# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

from typing import TYPE_CHECKING

import torch

from isaaclab.assets import Articulation
from isaaclab.managers import SceneEntityCfg
from isaaclab.utils.math import wrap_to_pi

from se3_rl_lab.assets.robots.serialleg_contract import SERIALLEG_CONTRACT

if TYPE_CHECKING:
    from isaaclab.envs import ManagerBasedRLEnv


def joint_pos_target_l2(env: ManagerBasedRLEnv, target: float, asset_cfg: SceneEntityCfg) -> torch.Tensor:
    """Penalize joint position deviation from a target value."""
    # extract the used quantities (to enable type-hinting)
    asset: Articulation = env.scene[asset_cfg.name]
    # wrap the joint positions to (-pi, pi)
    joint_pos = wrap_to_pi(asset.data.joint_pos[:, asset_cfg.joint_ids])
    # compute the reward
    return torch.sum(torch.square(joint_pos - target), dim=1)


def _robot(env: ManagerBasedRLEnv, asset_cfg: SceneEntityCfg) -> Articulation:
    return env.scene[asset_cfg.name]


def _command(env: ManagerBasedRLEnv, name: str) -> torch.Tensor:
    return env.command_manager.get_command(name)


def _upright_factor(projected_gravity_z: torch.Tensor) -> torch.Tensor:
    return torch.clamp(-projected_gravity_z, 0.0, 0.7) / 0.7


def _near_upright_gate(projected_gravity_z: torch.Tensor, start_deg: float, full_deg: float) -> torch.Tensor:
    tilt = torch.rad2deg(torch.acos(torch.clamp(-projected_gravity_z, -1.0, 1.0)))
    return torch.clamp((float(start_deg) - tilt) / max(float(start_deg) - float(full_deg), 1.0e-6), 0.0, 1.0)


def recovery_tracking_lin_vel(
    env: ManagerBasedRLEnv,
    command_name: str,
    sigma_move: float,
    sigma_stand: float,
    asset_cfg: SceneEntityCfg,
    upright_full_cos: float,
) -> torch.Tensor:
    robot = _robot(env, asset_cfg)
    cmd = _command(env, command_name)
    error = robot.data.root_lin_vel_b[:, 0] - cmd[:, 0]
    sigma = torch.where(torch.abs(cmd[:, 0]) > 0.1, sigma_move, sigma_stand)
    gate = torch.clamp(-robot.data.projected_gravity_b[:, 2], 0.0, upright_full_cos) / upright_full_cos
    return torch.exp(-(error**2) / sigma) * gate


def recovery_tracking_ang_vel(
    env: ManagerBasedRLEnv,
    command_name: str,
    sigma: float,
    asset_cfg: SceneEntityCfg,
    upright_full_cos: float,
) -> torch.Tensor:
    robot = _robot(env, asset_cfg)
    error = robot.data.root_ang_vel_b[:, 2] - _command(env, command_name)[:, 1]
    gate = torch.clamp(-robot.data.projected_gravity_b[:, 2], 0.0, upright_full_cos) / upright_full_cos
    return torch.exp(-(error**2) / sigma) * gate


def recovery_upward(env: ManagerBasedRLEnv, asset_cfg: SceneEntityCfg) -> torch.Tensor:
    pg_z = _robot(env, asset_cfg).data.projected_gravity_b[:, 2]
    return torch.square(1.0 - pg_z)


def recovery_height_l2(env: ManagerBasedRLEnv, command_name: str, asset_cfg: SceneEntityCfg) -> torch.Tensor:
    robot = _robot(env, asset_cfg)
    height = robot.data.root_pos_w[:, 2] - env.scene.env_origins[:, 2]
    error = height - _command(env, command_name)[:, 4]
    pg_z = robot.data.projected_gravity_b[:, 2]
    pose_gate = torch.maximum(torch.clamp(-pg_z, 0.0, 1.0), torch.clamp(pg_z, 0.0, 1.0))
    return error**2 * pose_gate


def recovery_lin_vel_z_l2(env: ManagerBasedRLEnv, asset_cfg: SceneEntityCfg) -> torch.Tensor:
    robot = _robot(env, asset_cfg)
    return robot.data.root_lin_vel_b[:, 2] ** 2 * _upright_factor(robot.data.projected_gravity_b[:, 2])


def recovery_ang_vel_xy_l2(env: ManagerBasedRLEnv, asset_cfg: SceneEntityCfg) -> torch.Tensor:
    robot = _robot(env, asset_cfg)
    return torch.sum(robot.data.root_ang_vel_b[:, :2] ** 2, dim=1) * _upright_factor(
        robot.data.projected_gravity_b[:, 2]
    )


def recovery_upright_orientation_l2(
    env: ManagerBasedRLEnv,
    command_name: str,
    asset_cfg: SceneEntityCfg,
    gate_start_deg: float = 60.0,
    gate_full_deg: float = 20.0,
    roll_scale_rad: float = 0.14,
    pitch_scale_rad: float = 0.20,
    roll_weight: float = 1.5,
    pitch_weight: float = 1.0,
    max_penalty: float = 6.0,
) -> torch.Tensor:
    robot = _robot(env, asset_cfg)
    pg = robot.data.projected_gravity_b
    pitch = torch.atan2(pg[:, 0], torch.sqrt(pg[:, 1] ** 2 + pg[:, 2] ** 2))
    roll = torch.atan2(-pg[:, 1], -pg[:, 2])
    cmd = _command(env, command_name)
    penalty = roll_weight * ((roll - cmd[:, 3]) / roll_scale_rad) ** 2
    penalty += pitch_weight * ((pitch - cmd[:, 2]) / pitch_scale_rad) ** 2
    return torch.clamp(penalty, max=max_penalty) * _near_upright_gate(pg[:, 2], gate_start_deg, gate_full_deg)


def recovery_upright_zero_velocity(
    env: ManagerBasedRLEnv,
    command_name: str,
    asset_cfg: SceneEntityCfg,
    wheel_cfg: SceneEntityCfg,
    command_threshold: float = 0.1,
    gate_start_deg: float = 45.0,
    gate_full_deg: float = 15.0,
    base_speed_scale: float = 0.15,
    wheel_speed_scale: float = 0.12,
    base_ang_vel_scale: float = 0.6,
    wheel_radius: float = 0.06,
    max_penalty: float = 8.0,
) -> torch.Tensor:
    robot = _robot(env, asset_cfg)
    standing = torch.linalg.vector_norm(_command(env, command_name)[:, :2], dim=1) <= command_threshold
    gate = _near_upright_gate(robot.data.projected_gravity_b[:, 2], gate_start_deg, gate_full_deg)
    base = torch.sum(robot.data.root_lin_vel_b[:, :2] ** 2, dim=1) / base_speed_scale**2
    angular = torch.sum(robot.data.root_ang_vel_b**2, dim=1) / base_ang_vel_scale**2
    wheel = torch.mean((robot.data.joint_vel[:, wheel_cfg.joint_ids] * wheel_radius) ** 2, dim=1) / wheel_speed_scale**2
    return torch.clamp(base + angular + wheel, max=max_penalty) * gate * standing.float()


def recovery_stand_still(
    env: ManagerBasedRLEnv, command_name: str, asset_cfg: SceneEntityCfg, command_threshold: float = 0.1
) -> torch.Tensor:
    robot = _robot(env, asset_cfg)
    stationary = torch.linalg.vector_norm(_command(env, command_name)[:, :2], dim=1) < command_threshold
    error = torch.sum(
        (robot.data.joint_pos[:, asset_cfg.joint_ids] - robot.data.default_joint_pos[:, asset_cfg.joint_ids]) ** 2,
        dim=1,
    )
    return error * _upright_factor(robot.data.projected_gravity_b[:, 2]) * stationary.float()


def recovery_joint_pos_penalty(
    env: ManagerBasedRLEnv,
    command_name: str,
    asset_cfg: SceneEntityCfg,
    stand_still_scale: float = 5.0,
    command_threshold: float = 0.1,
) -> torch.Tensor:
    robot = _robot(env, asset_cfg)
    error = torch.linalg.vector_norm(
        robot.data.joint_pos[:, asset_cfg.joint_ids] - robot.data.default_joint_pos[:, asset_cfg.joint_ids], dim=1
    )
    stationary = torch.linalg.vector_norm(_command(env, command_name)[:, :2], dim=1) < command_threshold
    scale = torch.where(stationary, stand_still_scale, 1.0)
    return error * scale * _upright_factor(robot.data.projected_gravity_b[:, 2])


def recovery_leg_action_rate(env: ManagerBasedRLEnv) -> torch.Tensor:
    return torch.sum((env.action_manager.action[:, :4] - env.action_manager.prev_action[:, :4]) ** 2, dim=1)


def recovery_wheel_action_rate(env: ManagerBasedRLEnv) -> torch.Tensor:
    return torch.sum((env.action_manager.action[:, 4:6] - env.action_manager.prev_action[:, 4:6]) ** 2, dim=1)


def recovery_action_smoothness(
    env: ManagerBasedRLEnv,
    asset_cfg: SceneEntityCfg,
    gate_start_deg: float = 90.0,
    gate_full_deg: float = 30.0,
    leg_scale: float = 1.0,
    wheel_scale: float = 2.0,
    max_penalty: float = 80.0,
) -> torch.Tensor:
    action = env.action_manager.action
    prev = env.action_manager.prev_action
    prev_prev = getattr(env, "_recovery_prev_prev_action", None)
    if not isinstance(prev_prev, torch.Tensor) or prev_prev.shape != action.shape:
        prev_prev = prev.detach().clone()
        env._recovery_prev_prev_action = prev_prev
    second = action - 2.0 * prev + prev_prev
    prev_prev.copy_(prev.detach())
    penalty = leg_scale * torch.sum(second[:, :4] ** 2, dim=1) + wheel_scale * torch.sum(second[:, 4:6] ** 2, dim=1)
    robot = _robot(env, asset_cfg)
    return torch.clamp(penalty, max=max_penalty) * _near_upright_gate(
        robot.data.projected_gravity_b[:, 2], gate_start_deg, gate_full_deg
    )


def recovery_leg_power(env: ManagerBasedRLEnv, asset_cfg: SceneEntityCfg) -> torch.Tensor:
    robot = _robot(env, asset_cfg)
    return torch.sum(
        torch.abs(robot.data.applied_torque[:, asset_cfg.joint_ids] * robot.data.joint_vel[:, asset_cfg.joint_ids]),
        dim=1,
    )


def recovery_wheel_torque_excess(env: ManagerBasedRLEnv, asset_cfg: SceneEntityCfg, max_torque: float) -> torch.Tensor:
    torque = torch.abs(_robot(env, asset_cfg).data.applied_torque[:, asset_cfg.joint_ids])
    return torch.sum(torch.clamp(torque - max_torque, min=0.0) ** 2, dim=1)


def recovery_joint_mirror(env: ManagerBasedRLEnv, asset_cfg: SceneEntityCfg) -> torch.Tensor:
    robot = _robot(env, asset_cfg)
    pos = robot.data.joint_pos[:, asset_cfg.joint_ids]
    default = robot.data.default_joint_pos[:, asset_cfg.joint_ids]
    diff = (pos[:, :2] - default[:, :2]) + (pos[:, 2:4] - default[:, 2:4])
    return torch.mean(diff**2, dim=1) * _upright_factor(robot.data.projected_gravity_b[:, 2])


def recovery_dof_pos_limits(env: ManagerBasedRLEnv, asset_cfg: SceneEntityCfg) -> torch.Tensor:
    robot = _robot(env, asset_cfg)
    pos = robot.data.joint_pos[:, asset_cfg.joint_ids]
    penalties = []
    for tendon in SERIALLEG_CONTRACT.fixed_tendons.values():
        indices = [SERIALLEG_CONTRACT.policy_joint_order.index(name) for name in tendon.joint_names]
        angle = sum(coef * pos[:, index] for coef, index in zip(tendon.coefficients, indices, strict=True))
        penalties.extend((torch.clamp(tendon.lower - angle, min=0.0), torch.clamp(angle - tendon.upper, min=0.0)))
    return torch.stack(penalties, dim=1).sum(dim=1)


def recovery_contact_count(env: ManagerBasedRLEnv, sensor_cfg: SceneEntityCfg, threshold: float = 0.1) -> torch.Tensor:
    force = env.scene[sensor_cfg.name].data.net_forces_w[:, sensor_cfg.body_ids]
    return (torch.linalg.vector_norm(force, dim=-1) > threshold).float().sum(dim=1)


def recovery_contact_force_excess(env: ManagerBasedRLEnv, sensor_cfg: SceneEntityCfg, threshold: float) -> torch.Tensor:
    force = torch.linalg.vector_norm(env.scene[sensor_cfg.name].data.net_forces_w[:, sensor_cfg.body_ids], dim=-1)
    return torch.sum(torch.clamp(force - threshold, min=0.0) / 100.0, dim=1)


def recovery_wheel_air_velocity(
    env: ManagerBasedRLEnv,
    asset_cfg: SceneEntityCfg,
    sensor_cfg: SceneEntityCfg,
    force_threshold: float = 1.0,
    max_penalty: float = 10000.0,
) -> torch.Tensor:
    robot = _robot(env, asset_cfg)
    force = torch.linalg.vector_norm(env.scene[sensor_cfg.name].data.net_forces_w[:, sensor_cfg.body_ids], dim=-1)
    air = (force < force_threshold).float()
    return torch.clamp(torch.sum(air * robot.data.joint_vel[:, asset_cfg.joint_ids] ** 2, dim=1), max=max_penalty)


def recovery_wheel_contact_without_cmd(
    env: ManagerBasedRLEnv,
    command_name: str,
    asset_cfg: SceneEntityCfg,
    sensor_cfg: SceneEntityCfg,
    force_threshold: float = 1.0,
    command_threshold: float = 0.1,
) -> torch.Tensor:
    robot = _robot(env, asset_cfg)
    force = torch.linalg.vector_norm(env.scene[sensor_cfg.name].data.net_forces_w[:, sensor_cfg.body_ids], dim=-1)
    stationary = torch.linalg.vector_norm(_command(env, command_name)[:, :2], dim=1) < command_threshold
    return (
        (force > force_threshold).float().sum(dim=1)
        * _upright_factor(robot.data.projected_gravity_b[:, 2])
        * stationary.float()
    )


def recovery_diagnostics(env: ManagerBasedRLEnv) -> torch.Tensor:
    """Logging-only reward term; deliberately contributes exactly zero."""
    return torch.zeros(env.num_envs, device=env.device)
