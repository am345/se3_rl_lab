# Copyright (c) 2026, SE3 RL Lab contributors.
# SPDX-License-Identifier: BSD-3-Clause

"""SerialLeg flat-task curricula."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from isaaclab.envs import ManagerBasedRLEnv


def _active_stage(stages: Sequence[dict[str, Any]], iteration: int) -> tuple[int, dict[str, Any]]:
    if not stages:
        raise ValueError("curriculum stages must not be empty")
    active_index = 0
    for index, stage in enumerate(stages):
        if iteration < int(stage["iteration"]):
            break
        active_index = index
    return active_index, stages[active_index]


def flat_velocity_and_push(
    env: ManagerBasedRLEnv,
    env_ids: Sequence[int],
    command_name: str,
    push_event_name: str,
    steps_per_policy_iteration: int,
    velocity_stages: Sequence[dict[str, Any]],
    push_stages: Sequence[dict[str, Any]],
) -> dict[str, float]:
    """Advance non-jumping command ranges and push strength by policy iteration."""
    del env_ids
    if steps_per_policy_iteration <= 0:
        raise ValueError("steps_per_policy_iteration must be positive")
    iteration = int(env.common_step_counter) // steps_per_policy_iteration

    velocity_index, velocity_stage = _active_stage(velocity_stages, iteration)
    command_cfg = env.command_manager.get_term(command_name).cfg
    command_cfg.lin_vel_x_range = tuple(velocity_stage["lin_vel_x_range"])
    command_cfg.ang_vel_yaw_range = tuple(velocity_stage["ang_vel_yaw_range"])

    push_index, push_stage = _active_stage(push_stages, iteration)
    push_cfg = env.event_manager.get_term_cfg(push_event_name)
    push_cfg.params["velocity_range"] = {
        "x": tuple(push_stage["lin_vel_range"]),
        "y": tuple(push_stage["lin_vel_range"]),
    }
    return {
        "policy_iteration": float(iteration),
        "velocity_stage": float(velocity_index),
        "push_stage": float(push_index),
    }
