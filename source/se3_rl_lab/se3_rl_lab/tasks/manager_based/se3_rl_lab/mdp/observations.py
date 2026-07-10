# Copyright (c) 2026, SE3 RL Lab contributors.
# SPDX-License-Identifier: BSD-3-Clause

"""SerialLeg actor and privileged-critic observation contract."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import torch

if TYPE_CHECKING:
    from isaaclab.envs import ManagerBasedRLEnv
    from isaaclab.managers import SceneEntityCfg


ACTOR_OBSERVATION_DIM = 34
CRITIC_OBSERVATION_DIM = 40
OBSERVATION_CLIP = 100.0
COMMAND_SCALE = (2.0, 0.25, 5.0, 5.0, 5.0)

# Public, immutable layout metadata.  Keeping the slices beside the producers makes
# checkpoint/deployment compatibility reviewable without launching Isaac Sim.
ACTOR_OBSERVATION_LAYOUT = {
    "base_ang_vel": slice(0, 3),
    "projected_gravity": slice(3, 6),
    "commands": slice(6, 11),
    "leg_joint_pos": slice(11, 17),
    "leg_joint_vel": slice(17, 21),
    "wheel_pos_zero": slice(21, 23),
    "wheel_vel": slice(23, 25),
    "last_actions": slice(25, 31),
    "jump_commands": slice(31, 34),
}
CRITIC_PRIVILEGED_LAYOUT = {
    "base_lin_vel": slice(34, 37),
    "wheel_contact_forces": slice(37, 39),
    "base_height": slice(39, 40),
}

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
    """Return the strict 8D command, or a transitional zero command if no term exists.

    Command migration belongs to the next migration phase.  The zero fallback is
    intentionally limited to an absent command manager or absent
    ``velocity_height`` term so the current skeleton remains runnable.  Once the
    named term exists, a wrong dimension is a hard contract error.
    """
    manager = getattr(env, "command_manager", None)
    active_terms = tuple(getattr(manager, "active_terms", ())) if manager is not None else ()
    if manager is None or "velocity_height" not in active_terms:
        return robot.data.joint_pos.new_zeros((robot.data.joint_pos.shape[0], 8))
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
