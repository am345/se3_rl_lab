# Copyright (c) 2026, SE3 RL Lab contributors.
# SPDX-License-Identifier: BSD-3-Clause

"""Recovery-specific hard-error terminations."""

from __future__ import annotations

import torch

from se3_rl_lab.assets.robots.serialleg import SERIALLEG_POLICY_LEG_JOINTS


def catastrophic_state(
    env,
    max_leg_vel: float = 120.0,
    max_root_lin_vel: float = 80.0,
    max_root_ang_vel: float = 500.0,
    min_base_height: float = -0.5,
    max_base_height: float = 3.0,
) -> torch.Tensor:
    """Terminate a diverging finite state before it can become a PhysX NaN."""
    robot = env.scene["robot"]
    joint_pos = robot.data.joint_pos
    joint_vel = robot.data.joint_vel
    root_pos = robot.data.root_link_pos_w
    root_lin_vel = robot.data.root_link_lin_vel_w
    root_ang_vel = robot.data.root_link_ang_vel_b
    projected_gravity = robot.data.projected_gravity_b
    leg_ids, leg_names = robot.find_joints(list(SERIALLEG_POLICY_LEG_JOINTS), preserve_order=True)
    if tuple(leg_names) != tuple(SERIALLEG_POLICY_LEG_JOINTS):
        raise RuntimeError(f"SerialLeg catastrophic-state joint order mismatch: {leg_names}")

    finite = (
        torch.isfinite(joint_pos).all(dim=1)
        & torch.isfinite(joint_vel).all(dim=1)
        & torch.isfinite(root_pos).all(dim=1)
        & torch.isfinite(root_lin_vel).all(dim=1)
        & torch.isfinite(root_ang_vel).all(dim=1)
        & torch.isfinite(projected_gravity).all(dim=1)
    )
    base_height = root_pos[:, 2] - env.scene.env_origins[:, 2]
    leg_vel_bad = torch.any(torch.abs(joint_vel[:, leg_ids]) > max_leg_vel, dim=1)
    root_lin_bad = torch.linalg.vector_norm(root_lin_vel, dim=1) > max_root_lin_vel
    root_ang_bad = torch.linalg.vector_norm(root_ang_vel, dim=1) > max_root_ang_vel
    height_bad = (base_height < min_base_height) | (base_height > max_base_height)
    return ~finite | leg_vel_bad | root_lin_bad | root_ang_bad | height_bad


__all__ = ["catastrophic_state"]
