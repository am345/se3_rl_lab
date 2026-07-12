# Copyright (c) 2026, SE3 RL Lab contributors.
# SPDX-License-Identifier: BSD-3-Clause

"""Complete root and joint reset contract for SerialLeg recovery discovery."""

from __future__ import annotations

import math
from pathlib import Path

import torch

from isaaclab.managers import SceneEntityCfg
from isaaclab.utils.math import quat_from_euler_xyz

from se3_rl_lab.assets.robots.serialleg import SERIALLEG_POLICY_LEG_JOINTS, SERIALLEG_WHEEL_JOINTS
from se3_rl_lab.assets.robots.serialleg_contract import SERIALLEG_CONTRACT

from .fourbar_reset import policy_to_passive_pos, policy_to_passive_vel

RECOVERY_CACHE_PATH = (
    Path(__file__).parents[4] / "assets/robots/serialleg/recovery_states/serialleg_closedchain_stair_v3_40k.npz"
)
RECOVERY_PASSIVE_JOINTS = ("lf1_Joint", "l_coupler_Joint", "rf1_Joint", "r_coupler_Joint")
_POSE_WEIGHTS = (0.08, 0.17, 0.17, 0.29, 0.29)
_POSE_RP = ((0.0, 0.0), (0.5 * math.pi, 0.0), (-0.5 * math.pi, 0.0), (0.0, math.pi), (0.0, -math.pi))
_FULL_ANGLE_RESET_BBOX_MIN = (-0.278, -0.242, -0.323)
_FULL_ANGLE_RESET_BBOX_MAX = (0.278, 0.242, 0.111)
_CACHE_RATIO_STAGES = (
    (0, 0.0),
    (300, 0.0),
    (800, 0.0),
    (1500, 0.10),
    (2000, 0.25),
    (2600, 0.45),
    (3400, 0.60),
    (4200, 0.70),
)
_STANDARD_STAGES = (
    (0, 5.0, 0.0, 0.0),
    (300, 10.0, 0.03, 0.10),
    (800, 15.0, 0.05, 0.20),
    (1500, 20.0, 0.08, 0.30),
    (2000, 25.0, 0.10, 0.40),
)
_JOINT_RANDOMIZATION_STAGES = ((0, 0.15), (300, 0.25), (650, 0.45), (1000, 0.70), (1400, 1.0))
_WHEEL_RADIUS = 0.06
_WHEEL_CLEARANCE = 0.001


def _iteration(env, steps_per_policy_iteration: int) -> int:
    return int(getattr(env, "common_step_counter", 0)) // max(int(steps_per_policy_iteration), 1)


def _stage(iteration: int, stages):
    return next(values for threshold, *values in reversed(stages) if iteration >= threshold)


def _quat_z_row(quat: torch.Tensor) -> torch.Tensor:
    w, x, y, z = quat.unbind(dim=-1)
    return torch.stack((2.0 * (x * z - w * y), 2.0 * (y * z + w * x), 1.0 - 2.0 * (x * x + y * y)), dim=-1)


def _safe_base_height(quat: torch.Tensor, clearance: torch.Tensor) -> torch.Tensor:
    z_row = _quat_z_row(quat)
    bbox_min = quat.new_tensor(_FULL_ANGLE_RESET_BBOX_MIN)
    bbox_max = quat.new_tensor(_FULL_ANGLE_RESET_BBOX_MAX)
    min_z = torch.minimum(z_row * bbox_min, z_row * bbox_max).sum(dim=-1)
    return -min_z + clearance


def _load_cache(env, robot, split: str) -> dict[str, torch.Tensor]:
    key = (str(RECOVERY_CACHE_PATH), split, tuple(robot.joint_names))
    store = getattr(env, "_recovery_state_cache_store", None)
    if not isinstance(store, dict):
        store = {}
        env._recovery_state_cache_store = store
    if key in store:
        return store[key]
    if not RECOVERY_CACHE_PATH.is_file():
        raise FileNotFoundError(f"recovery state cache missing: {RECOVERY_CACHE_PATH}")
    import numpy as np

    data = np.load(RECOVERY_CACHE_PATH)
    required = (
        "root_pos",
        "root_quat",
        "root_lin_vel",
        "root_ang_vel",
        "joint_pos",
        "joint_vel",
        "joint_names",
        "split",
    )
    missing = [name for name in required if name not in data]
    if missing:
        raise ValueError(f"recovery state cache missing fields: {missing}")
    rows = np.flatnonzero(np.asarray(data["split"]).astype(str) == split)
    if rows.size == 0:
        raise ValueError(f"recovery state cache split {split!r} has no samples")
    cache_names = tuple(str(value) for value in data["joint_names"].tolist())
    cache_index = {name: index for index, name in enumerate(cache_names)}
    joint_pos = np.broadcast_to(
        robot.data.default_joint_pos[0].cpu().numpy(), (rows.size, len(robot.joint_names))
    ).copy()
    joint_vel = np.zeros_like(joint_pos)
    for current_index, name in enumerate(robot.joint_names):
        if name in cache_index:
            joint_pos[:, current_index] = data["joint_pos"][rows, cache_index[name]]
            joint_vel[:, current_index] = data["joint_vel"][rows, cache_index[name]]
        elif name not in SERIALLEG_CONTRACT.tendon_root_joint_names:
            raise ValueError(f"recovery cache does not contain current joint {name!r}")
    cache = {
        "root_pos": torch.as_tensor(data["root_pos"][rows], device=env.device, dtype=torch.float32),
        "root_quat": torch.as_tensor(data["root_quat"][rows], device=env.device, dtype=torch.float32),
        "root_lin_vel": torch.as_tensor(data["root_lin_vel"][rows], device=env.device, dtype=torch.float32),
        "root_ang_vel": torch.as_tensor(data["root_ang_vel"][rows], device=env.device, dtype=torch.float32),
        "joint_pos": torch.as_tensor(joint_pos, device=env.device, dtype=torch.float32),
        "joint_vel": torch.as_tensor(joint_vel, device=env.device, dtype=torch.float32),
    }
    store[key] = cache
    return cache


def reset_root_state_recovery_mixed(
    env,
    env_ids: torch.Tensor,
    asset_cfg: SceneEntityCfg,
    steps_per_policy_iteration: int = 24,
    cache_split: str = "train",
) -> None:
    """Mix standard five-pose resets with settled states from the 40k cache."""
    robot = env.scene[asset_cfg.name]
    count = env_ids.numel()
    iteration = _iteration(env, steps_per_policy_iteration)
    (cache_ratio,) = _stage(iteration, _CACHE_RATIO_STAGES)
    jitter_deg, lin_vel_limit, ang_vel_limit = _stage(iteration, _STANDARD_STAGES)
    cache_mask = torch.rand(count, device=env.device) < cache_ratio
    pose = robot.data.default_root_state[env_ids, :7].clone()
    pose[:, :3] = env.scene.env_origins[env_ids]
    velocity = torch.zeros((count, 6), device=env.device)
    pose_ids = torch.multinomial(pose.new_tensor(_POSE_WEIGHTS), count, replacement=True)
    presets = pose.new_tensor(_POSE_RP)
    jitter = math.radians(jitter_deg)
    roll = presets[pose_ids, 0] + torch.empty(count, device=env.device).uniform_(-jitter, jitter)
    pitch = presets[pose_ids, 1] + torch.empty(count, device=env.device).uniform_(-jitter, jitter)
    yaw = torch.empty(count, device=env.device).uniform_(-math.pi, math.pi)
    pose[:, 0:2] += torch.empty((count, 2), device=env.device).uniform_(-0.15, 0.15)
    pose[:, 3:7] = quat_from_euler_xyz(roll, pitch, yaw)
    sampled_height = robot.data.default_root_state[env_ids, 2] + torch.empty(count, device=env.device).uniform_(
        0.0, 0.02
    )
    clearance = torch.empty(count, device=env.device).uniform_(0.001, 0.005)
    pose[:, 2] += torch.maximum(sampled_height, _safe_base_height(pose[:, 3:7], clearance))
    velocity[:, :3].uniform_(-lin_vel_limit, lin_vel_limit)
    velocity[:, 3:].uniform_(-ang_vel_limit, ang_vel_limit)

    cached_joint_pos = robot.data.default_joint_pos[env_ids].clone()
    cached_joint_vel = torch.zeros_like(cached_joint_pos)
    if torch.any(cache_mask):
        cache = _load_cache(env, robot, cache_split)
        cache_rows = torch.randint(cache["root_pos"].shape[0], (int(cache_mask.sum()),), device=env.device)
        pose[cache_mask, :3] = cache["root_pos"][cache_rows] + env.scene.env_origins[env_ids[cache_mask]]
        pose[cache_mask, 3:7] = cache["root_quat"][cache_rows]
        velocity[cache_mask, :3] = cache["root_lin_vel"][cache_rows]
        velocity[cache_mask, 3:] = cache["root_ang_vel"][cache_rows]
        cached_joint_pos[cache_mask] = cache["joint_pos"][cache_rows]
        cached_joint_vel[cache_mask] = cache["joint_vel"][cache_rows]
    if not hasattr(env, "_recovery_cached_joint_pos"):
        env._recovery_cached_joint_pos = torch.zeros_like(robot.data.default_joint_pos)
        env._recovery_cached_joint_vel = torch.zeros_like(robot.data.default_joint_pos)
        env._recovery_cache_reset_mask = torch.zeros(env.num_envs, device=env.device, dtype=torch.bool)
    env._recovery_cached_joint_pos[env_ids] = cached_joint_pos
    env._recovery_cached_joint_vel[env_ids] = cached_joint_vel
    env._recovery_cache_reset_mask[env_ids] = cache_mask
    robot.write_root_pose_to_sim(pose, env_ids=env_ids)
    robot.write_root_velocity_to_sim(velocity, env_ids=env_ids)


def reset_recovery_joints(
    env,
    env_ids: torch.Tensor,
    asset_cfg: SceneEntityCfg,
    steps_per_policy_iteration: int = 24,
) -> None:
    """Write a closure-consistent full 12-joint state, including passive and tendon-root joints."""
    robot = env.scene[asset_cfg.name]
    joint_pos = robot.data.default_joint_pos[env_ids].clone()
    joint_vel = torch.zeros_like(joint_pos)
    policy_ids, policy_names = robot.find_joints(list(SERIALLEG_POLICY_LEG_JOINTS), preserve_order=True)
    passive_ids, passive_names = robot.find_joints(list(RECOVERY_PASSIVE_JOINTS), preserve_order=True)
    wheel_ids, wheel_names = robot.find_joints(list(SERIALLEG_WHEEL_JOINTS), preserve_order=True)
    tendon_ids, tendon_names = robot.find_joints(list(SERIALLEG_CONTRACT.tendon_root_joint_names), preserve_order=True)
    if tuple(policy_names) != tuple(SERIALLEG_POLICY_LEG_JOINTS) or tuple(passive_names) != RECOVERY_PASSIVE_JOINTS:
        raise RuntimeError("SerialLeg recovery joint order does not match the reset contract")
    if (
        tuple(wheel_names) != tuple(SERIALLEG_WHEEL_JOINTS)
        or tuple(tendon_names) != SERIALLEG_CONTRACT.tendon_root_joint_names
    ):
        raise RuntimeError("SerialLeg recovery wheel/tendon-root order does not match the reset contract")
    iteration = _iteration(env, steps_per_policy_iteration)
    (randomize_prob,) = _stage(iteration, _JOINT_RANDOMIZATION_STAGES)
    randomize = torch.rand(env_ids.numel(), device=env.device) < randomize_prob
    policy_pos = joint_pos[:, policy_ids].clone()
    policy_vel = torch.zeros_like(policy_pos)
    if torch.any(randomize):
        rows = torch.nonzero(randomize, as_tuple=False).flatten()
        policy_pos[rows, 0] += torch.empty(rows.numel(), device=env.device).uniform_(-math.pi, math.pi)
        policy_pos[rows, 2] += torch.empty(rows.numel(), device=env.device).uniform_(-math.pi, math.pi)
        active_lower = max(tendon.lower for tendon in SERIALLEG_CONTRACT.fixed_tendons.values())
        active_upper = min(tendon.upper for tendon in SERIALLEG_CONTRACT.fixed_tendons.values())
        active = torch.empty((rows.numel(), 2), device=env.device).uniform_(active_lower, active_upper)
        policy_pos[rows, 1] = policy_pos[rows, 0] - active[:, 0]
        policy_pos[rows, 3] = policy_pos[rows, 2] + active[:, 1]
        policy_vel[rows].uniform_(-0.8, 0.8)
        joint_vel[rows[:, None], wheel_ids] = torch.empty((rows.numel(), 2), device=env.device).uniform_(-10.0, 10.0)
    joint_pos[:, policy_ids] = policy_pos
    joint_vel[:, policy_ids] = policy_vel
    joint_pos[:, passive_ids] = policy_to_passive_pos(policy_pos)
    joint_vel[:, passive_ids] = policy_to_passive_vel(policy_pos, policy_vel)
    joint_pos[:, wheel_ids] = 0.0
    joint_pos[:, tendon_ids] = robot.data.default_joint_pos[env_ids][:, tendon_ids]
    joint_vel[:, tendon_ids] = 0.0
    cache_mask = env._recovery_cache_reset_mask[env_ids]
    if torch.any(cache_mask):
        joint_pos[cache_mask] = env._recovery_cached_joint_pos[env_ids[cache_mask]]
        joint_vel[cache_mask] = env._recovery_cached_joint_vel[env_ids[cache_mask]]
        cache_rows = torch.nonzero(cache_mask, as_tuple=False).flatten()
        joint_pos[cache_rows[:, None], tendon_ids] = robot.data.default_joint_pos[env_ids[cache_mask]][:, tendon_ids]
        joint_vel[cache_rows[:, None], tendon_ids] = 0.0
    robot.write_joint_state_to_sim(joint_pos, joint_vel, env_ids=env_ids)
    _lift_root_to_wheel_clearance(env, env_ids, robot, asset_cfg)


def _lift_root_to_wheel_clearance(env, env_ids: torch.Tensor, robot, asset_cfg: SceneEntityCfg) -> None:
    """Lift resets whose randomized linkage puts either wheel below the ground plane."""
    env.sim.forward()
    body_ids, body_names = robot.find_bodies(("l_wheel_Link", "r_wheel_Link"), preserve_order=True)
    if tuple(body_names) != ("l_wheel_Link", "r_wheel_Link"):
        raise RuntimeError(f"{asset_cfg.name} recovery wheel bodies do not match the reset contract: {body_names}")
    wheel_pos_w = robot.data.body_link_pos_w[env_ids][:, body_ids, :]
    ground_z = env.scene.env_origins[env_ids, 2].unsqueeze(1)
    wheel_bottom = wheel_pos_w[:, :, 2] - ground_z - _WHEEL_RADIUS
    adjustment = torch.clamp(_WHEEL_CLEARANCE - wheel_bottom.min(dim=1).values, min=0.0, max=0.3)
    if torch.any(adjustment > 0.0):
        root_pose = robot.data.root_link_state_w[env_ids, :7].clone()
        root_pose[:, 2] += adjustment
        robot.write_root_pose_to_sim(root_pose, env_ids=env_ids)
        env.sim.forward()
    if hasattr(env, "extras"):
        log = env.extras.setdefault("log", {})
        log["Reset/wheel_clearance_before_min_m"] = float(wheel_bottom.min().item())
        log["Reset/wheel_clearance_adjustment_max_m"] = float(adjustment.max().item())
        log["Reset/wheel_clearance_adjustment_ratio"] = float((adjustment > 1.0e-6).float().mean().item())


__all__ = [
    "RECOVERY_CACHE_PATH",
    "RECOVERY_PASSIVE_JOINTS",
    "reset_recovery_joints",
    "reset_root_state_recovery_mixed",
]
