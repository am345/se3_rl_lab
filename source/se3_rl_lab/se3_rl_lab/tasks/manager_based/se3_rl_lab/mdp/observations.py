# Copyright (c) 2026, SE3 RL Lab contributors.
# SPDX-License-Identifier: BSD-3-Clause

"""SerialLeg actor and privileged-critic observation contract."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import torch

from se3_rl_lab import serialleg_policy_contract as _policy_contract

ACTOR_OBSERVATION_DIM = _policy_contract.ACTOR_OBSERVATION_DIM
ACTOR_OBSERVATION_LAYOUT = _policy_contract.ACTOR_OBSERVATION_LAYOUT
COMMAND_SCALE = _policy_contract.COMMAND_SCALE
CRITIC_OBSERVATION_DIM = _policy_contract.CRITIC_OBSERVATION_DIM
CRITIC_PRIVILEGED_LAYOUT = _policy_contract.CRITIC_PRIVILEGED_LAYOUT
OBSERVATION_CLIP = _policy_contract.OBSERVATION_CLIP
RECOVERY_ACTOR_OBSERVATION_DIM = _policy_contract.RECOVERY_ACTOR_OBSERVATION_DIM
RECOVERY_COMMAND_LAYOUT = _policy_contract.RECOVERY_COMMAND_LAYOUT
RECOVERY_COMMAND_OBSERVATION_DIM = _policy_contract.RECOVERY_COMMAND_OBSERVATION_DIM
RECOVERY_CRITIC_OBSERVATION_DIM = _policy_contract.RECOVERY_CRITIC_OBSERVATION_DIM
RECOVERY_OBSERVATION_GROUP_DIMS = _policy_contract.RECOVERY_OBSERVATION_GROUP_DIMS
RECOVERY_OBSERVATION_HISTORY_LENGTH = _policy_contract.RECOVERY_OBSERVATION_HISTORY_LENGTH
RECOVERY_PRIVILEGED_LAYOUT = _policy_contract.RECOVERY_PRIVILEGED_LAYOUT
RECOVERY_PRIVILEGED_PROPRIOCEPTION_DIM = _policy_contract.RECOVERY_PRIVILEGED_PROPRIOCEPTION_DIM
RECOVERY_PRIVILEGED_TERM_DIMS = _policy_contract.RECOVERY_PRIVILEGED_TERM_DIMS
RECOVERY_PROPRIOCEPTION_LAYOUT = _policy_contract.RECOVERY_PROPRIOCEPTION_LAYOUT
RECOVERY_PROPRIOCEPTION_OBSERVATION_DIM = _policy_contract.RECOVERY_PROPRIOCEPTION_OBSERVATION_DIM
RECOVERY_PROPRIOCEPTION_TERM_DIMS = _policy_contract.RECOVERY_PROPRIOCEPTION_TERM_DIMS

if TYPE_CHECKING:
    from isaaclab.envs import ManagerBasedRLEnv
    from isaaclab.managers import SceneEntityCfg


_LEG_ACTIVE_ROD_COEFFICIENTS = ((1.0, -1.0), (-1.0, 1.0))


def _finite_clamp(value: torch.Tensor, limit: float = OBSERVATION_CLIP) -> torch.Tensor:
    """Contain non-finite state from one environment before it reaches PPO."""
    return torch.nan_to_num(value, nan=0.0, posinf=limit, neginf=-limit).clamp(-limit, limit)


def _robot(env: ManagerBasedRLEnv, asset_cfg: SceneEntityCfg) -> Any:
    return env.scene[asset_cfg.name]


def base_ang_vel_obs(env: ManagerBasedRLEnv, asset_cfg: SceneEntityCfg) -> torch.Tensor:
    """Base-frame angular velocity, scaled by 0.25 (3D)."""
    return _finite_clamp(_robot(env, asset_cfg).data.root_ang_vel_b * 0.25)


def projected_gravity_obs(env: ManagerBasedRLEnv, asset_cfg: SceneEntityCfg) -> torch.Tensor:
    """Gravity projected into the base frame (3D)."""
    return _finite_clamp(_robot(env, asset_cfg).data.projected_gravity_b, limit=1.0)


def _velocity_height_command(env: ManagerBasedRLEnv, robot: Any) -> torch.Tensor:
    """Return the required strict 8D ``velocity_height`` command."""
    manager = getattr(env, "command_manager", None)
    active_terms = tuple(getattr(manager, "active_terms", ())) if manager is not None else ()
    if manager is None or "velocity_height" not in active_terms:
        raise RuntimeError("velocity_height command term is required by the SerialLeg observation contract")
    command = manager.get_command("velocity_height")
    if command.ndim != 2 or command.shape != (robot.data.joint_pos.shape[0], 8):
        raise ValueError(
            "velocity_height observation contract requires shape "
            f"({robot.data.joint_pos.shape[0]}, 8), got {tuple(command.shape)}"
        )
    return command


def commands_obs(env: ManagerBasedRLEnv, asset_cfg: SceneEntityCfg) -> torch.Tensor:
    """First five command fields: vx, yaw-rate, pitch, roll, height (5D)."""
    robot = _robot(env, asset_cfg)
    command = _velocity_height_command(env, robot)
    scale = command.new_tensor(COMMAND_SCALE)
    return _finite_clamp(command[:, :5] * scale)


def leg_joint_pos_obs(env: ManagerBasedRLEnv, asset_cfg: SceneEntityCfg) -> torch.Tensor:
    """Periodic front-link phase plus active-rod angle delta (6D).

    ``asset_cfg.joint_ids`` must resolve the four policy leg joints in
    ``[lf0, l_drive_bar, rf0, r_drive_bar]`` order.  Thus passive joints and the
    two virtual tendon roots can never leak into policy observations.
    """
    robot = _robot(env, asset_cfg)
    pos = robot.data.joint_pos[:, asset_cfg.joint_ids]
    default = robot.data.default_joint_pos[:, asset_cfg.joint_ids]
    front_delta = pos[:, (0, 2)] - default[:, (0, 2)]
    coeffs = pos.new_tensor(_LEG_ACTIVE_ROD_COEFFICIENTS)
    active_delta = torch.stack(
        (
            pos[:, 0] * coeffs[0, 0] + pos[:, 1] * coeffs[0, 1],
            pos[:, 2] * coeffs[1, 0] + pos[:, 3] * coeffs[1, 1],
        ),
        dim=1,
    ) - torch.stack(
        (
            default[:, 0] * coeffs[0, 0] + default[:, 1] * coeffs[0, 1],
            default[:, 2] * coeffs[1, 0] + default[:, 3] * coeffs[1, 1],
        ),
        dim=1,
    )
    return _finite_clamp(
        torch.stack(
            (
                torch.sin(front_delta[:, 0]),
                torch.cos(front_delta[:, 0]),
                active_delta[:, 0],
                torch.sin(front_delta[:, 1]),
                torch.cos(front_delta[:, 1]),
                active_delta[:, 1],
            ),
            dim=1,
        )
    )


def leg_joint_vel_obs(env: ManagerBasedRLEnv, asset_cfg: SceneEntityCfg) -> torch.Tensor:
    """Four ordered policy-leg velocities, scaled by 0.25 (4D)."""
    robot = _robot(env, asset_cfg)
    return _finite_clamp(robot.data.joint_vel[:, asset_cfg.joint_ids] * 0.25)


def wheel_pos_obs(env: ManagerBasedRLEnv, asset_cfg: SceneEntityCfg) -> torch.Tensor:
    """Compatibility slots fixed at zero; continuous wheel angles are unbounded (2D)."""
    robot = _robot(env, asset_cfg)
    return torch.zeros_like(robot.data.joint_pos[:, asset_cfg.joint_ids])


def wheel_vel_obs(env: ManagerBasedRLEnv, asset_cfg: SceneEntityCfg) -> torch.Tensor:
    """Two ordered policy-wheel velocities, scaled by 0.05 (2D)."""
    robot = _robot(env, asset_cfg)
    return _finite_clamp(robot.data.joint_vel[:, asset_cfg.joint_ids] * 0.05)


def last_actions_obs(env: ManagerBasedRLEnv) -> torch.Tensor:
    """Previous clipped 6D policy action, before delay/actuator transformation."""
    manager = env.action_manager
    for term_name in getattr(manager, "active_terms", ()):
        term = manager.get_term(term_name)
        for attribute in ("policy_action", "raw_actions", "raw_action"):
            value = getattr(term, attribute, None)
            if isinstance(value, torch.Tensor):
                return _finite_clamp(value)
    return _finite_clamp(manager.action)


def jump_commands_obs(env: ManagerBasedRLEnv, asset_cfg: SceneEntityCfg) -> torch.Tensor:
    """Jump flag, target height and normalized trajectory phase (3D)."""
    robot = _robot(env, asset_cfg)
    return _finite_clamp(_velocity_height_command(env, robot)[:, 5:8])


def base_lin_vel_obs(env: ManagerBasedRLEnv, asset_cfg: SceneEntityCfg) -> torch.Tensor:
    """Unscaled base-frame linear velocity, critic-only (3D)."""
    return _finite_clamp(_robot(env, asset_cfg).data.root_lin_vel_b)


def wheel_contact_force_obs(env: ManagerBasedRLEnv, sensor_cfg: SceneEntityCfg) -> torch.Tensor:
    """Norm of each wheel's net world-frame contact force, critic-only (2D)."""
    sensor = env.scene[sensor_cfg.name]
    force = sensor.data.net_forces_w[:, sensor_cfg.body_ids]
    return _finite_clamp(torch.linalg.vector_norm(force, dim=-1))


def flat_base_height_obs(env: ManagerBasedRLEnv, asset_cfg: SceneEntityCfg) -> torch.Tensor:
    """Base height above the flat environment origin, critic-only (1D).

    On this task's plane terrain this is identical to the legacy mean downward
    ray height, while avoiding a redundant ray-caster sensor.
    """
    robot = _robot(env, asset_cfg)
    origins = env.scene.env_origins
    return _finite_clamp((robot.data.root_pos_w[:, 2] - origins[:, 2]).unsqueeze(-1))
