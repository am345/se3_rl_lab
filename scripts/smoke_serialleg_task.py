#!/usr/bin/env python3
"""Run a bounded single-environment SerialLeg task gate on CPU or CUDA."""

from __future__ import annotations

import argparse
import math
import os
import sys
import traceback
from collections.abc import Mapping, Sequence

from isaaclab.app import AppLauncher


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", default="SerialLeg-Flat-ClosedChain-v0", help="Registered Gym task id")
    parser.add_argument("--zero-steps", type=int, default=64, help="Environment steps with zero action")
    parser.add_argument("--controlled-steps", type=int, default=64, help="Environment steps with small actions")
    parser.add_argument("--action-amplitude", type=float, default=0.05, help="Peak normalized controlled action")
    parser.add_argument("--max-loop-residual", type=float, default=1.0e-3, help="Maximum loop attachment error")
    parser.add_argument("--min-contact-force", type=float, default=1.0, help="Minimum observed ground contact force")
    parser.add_argument("--max-contact-force", type=float, default=1.0e4, help="Maximum plausible contact force")
    parser.add_argument("--max-joint-speed", type=float, default=100.0, help="Maximum absolute joint speed")
    parser.add_argument("--max-root-linear-speed", type=float, default=20.0, help="Maximum root linear speed")
    parser.add_argument("--max-root-angular-speed", type=float, default=100.0, help="Maximum root angular speed")
    parser.add_argument("--max-passive-effort", type=float, default=1.0e-6, help="Maximum passive joint effort")
    parser.add_argument(
        "--compact-gpu-buffers",
        action="store_true",
        help="Use bounded PhysX GPU capacities suitable for this one-environment gate",
    )
    AppLauncher.add_app_launcher_args(parser)
    parser.set_defaults(headless=True, device="cpu")
    return parser.parse_args()


ARGS = _parse_args()
APP_LAUNCHER = AppLauncher(ARGS, fast_shutdown=True)
SIMULATION_APP = APP_LAUNCHER.app

import gymnasium as gym  # noqa: E402
import se3_rl_lab.tasks  # noqa: F401, E402
import torch  # noqa: E402
from se3_rl_lab.assets.robots.serialleg_contract import SERIALLEG_CONTRACT  # noqa: E402

from isaaclab.assets import Articulation  # noqa: E402
from isaaclab.sensors import ContactSensor  # noqa: E402
from isaaclab.utils.math import quat_apply  # noqa: E402

import isaaclab_tasks  # noqa: F401, E402
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402


def _validate_args() -> None:
    positive = {
        "--zero-steps": ARGS.zero_steps,
        "--controlled-steps": ARGS.controlled_steps,
        "--action-amplitude": ARGS.action_amplitude,
        "--max-loop-residual": ARGS.max_loop_residual,
        "--min-contact-force": ARGS.min_contact_force,
        "--max-contact-force": ARGS.max_contact_force,
        "--max-joint-speed": ARGS.max_joint_speed,
        "--max-root-linear-speed": ARGS.max_root_linear_speed,
        "--max-root-angular-speed": ARGS.max_root_angular_speed,
        "--max-passive-effort": ARGS.max_passive_effort,
    }
    invalid = {name: value for name, value in positive.items() if value <= 0.0}
    if invalid:
        raise ValueError(f"smoke arguments must be positive: {invalid}")
    if ARGS.max_contact_force <= ARGS.min_contact_force:
        raise ValueError("--max-contact-force must exceed --min-contact-force")


def _assert_finite(value, context: str) -> None:
    if isinstance(value, torch.Tensor):
        if not torch.isfinite(value).all():
            raise RuntimeError(f"non-finite tensor in {context}")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            _assert_finite(item, f"{context}.{key}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, item in enumerate(value):
            _assert_finite(item, f"{context}[{index}]")


def _attachment_position(robot: Articulation, body_name: str, local_position: tuple[float, float, float]):
    body_index = robot.body_names.index(body_name)
    position = robot.data.body_pos_w[:, body_index]
    orientation = robot.data.body_quat_w[:, body_index]
    local = torch.tensor(local_position, dtype=position.dtype, device=position.device).expand_as(position)
    return position + quat_apply(orientation, local)


def _loop_residuals(robot: Articulation) -> dict[str, float]:
    residuals = {}
    for loop in SERIALLEG_CONTRACT.loop_joints.values():
        point0 = _attachment_position(robot, loop.body0, loop.local_pos0)
        point1 = _attachment_position(robot, loop.body1, loop.local_pos1)
        residuals[loop.name] = float(torch.linalg.vector_norm(point0 - point1, dim=-1).max().item())
    return residuals


def _joint_ids(robot: Articulation, names: Sequence[str]) -> list[int]:
    ids, resolved_names = robot.find_joints(list(names), preserve_order=True)
    if tuple(resolved_names) != tuple(names):
        raise RuntimeError(f"joint resolution order mismatch: expected={tuple(names)} actual={tuple(resolved_names)}")
    return list(ids)


def _tensor_joint_ids(indices: slice | torch.Tensor, joint_count: int) -> list[int]:
    if isinstance(indices, slice):
        return list(range(joint_count))[indices]
    return [int(index) for index in indices.detach().cpu().tolist()]


def _validate_topology_and_control(env, robot: Articulation) -> tuple[list[int], list[int]]:
    expected_policy = SERIALLEG_CONTRACT.policy_joint_order
    expected_passive = SERIALLEG_CONTRACT.passive_joint_names
    if robot.num_bodies != 11 or robot.num_joints != 10:
        raise RuntimeError(f"unexpected articulation size: bodies={robot.num_bodies} joints={robot.num_joints}")
    if set(robot.joint_names) != set(SERIALLEG_CONTRACT.tree_joints):
        raise RuntimeError(f"unexpected articulation joints: {robot.joint_names}")

    if env.action_manager.active_terms != ["joint_effort"] or env.action_manager.total_action_dim != 6:
        terms = env.action_manager.active_terms
        action_dim = env.action_manager.total_action_dim
        raise RuntimeError(f"unexpected action terms/dimension: {terms}/{action_dim}")
    action_term = env.action_manager.get_term("joint_effort")
    action_names = tuple(action_term._joint_names)
    if action_names != expected_policy:
        raise RuntimeError(f"policy action order mismatch: expected={expected_policy} actual={action_names}")

    policy_ids = _joint_ids(robot, expected_policy)
    passive_ids = _joint_ids(robot, expected_passive)
    configured_policy_ids: list[int] = []
    configured_passive_ids: list[int] = []
    for group_name, actuator in robot.actuators.items():
        ids = _tensor_joint_ids(actuator.joint_indices, robot.num_joints)
        expected_names = SERIALLEG_CONTRACT.actuator_groups[group_name].joint_names
        actual_names = tuple(robot.joint_names[index] for index in ids)
        if len(actual_names) != len(expected_names) or set(actual_names) != set(expected_names):
            raise RuntimeError(f"actuator {group_name} mismatch: expected={expected_names} actual={actual_names}")
        if SERIALLEG_CONTRACT.actuator_groups[group_name].policy:
            configured_policy_ids.extend(ids)
        else:
            configured_passive_ids.extend(ids)
            for field_name in ("effort_limit_sim", "stiffness", "damping"):
                value = getattr(actuator, field_name)
                if not torch.allclose(value, torch.zeros_like(value), atol=0.0, rtol=0.0):
                    raise RuntimeError(f"passive actuator {group_name}.{field_name} is nonzero: {value}")
    if set(configured_policy_ids) != set(policy_ids) or len(configured_policy_ids) != 6:
        raise RuntimeError(f"policy actuator coverage mismatch: {configured_policy_ids} vs {policy_ids}")
    if set(configured_passive_ids) != set(passive_ids) or len(configured_passive_ids) != 4:
        raise RuntimeError(f"passive actuator coverage mismatch: {configured_passive_ids} vs {passive_ids}")
    if set(configured_policy_ids).intersection(configured_passive_ids):
        raise RuntimeError("policy and passive actuator groups overlap")
    return policy_ids, passive_ids


def _validate_reset(robot: Articulation, observation) -> None:
    _assert_finite(observation, "reset observation")
    tensors = {
        "joint_pos": robot.data.joint_pos,
        "joint_vel": robot.data.joint_vel,
        "body_pos_w": robot.data.body_pos_w,
        "body_quat_w": robot.data.body_quat_w,
        "root_state_w": robot.data.root_state_w,
    }
    for name, tensor in tensors.items():
        _assert_finite(tensor, f"reset {name}")
    expected = torch.tensor(
        [SERIALLEG_CONTRACT.default_joint_positions[name] for name in robot.joint_names],
        dtype=robot.data.joint_pos.dtype,
        device=robot.device,
    )
    max_error = float(torch.max(torch.abs(robot.data.joint_pos[0] - expected)).item())
    if max_error > 1.0e-5:
        raise RuntimeError(f"standing reset joint error {max_error:.3e} exceeds 1e-5 rad")


def _sample_metrics(robot: Articulation, sensor: ContactSensor, passive_ids: list[int]) -> dict[str, float]:
    tensors = {
        "joint_pos": robot.data.joint_pos,
        "joint_vel": robot.data.joint_vel,
        "joint_acc": robot.data.joint_acc,
        "applied_torque": robot.data.applied_torque,
        "body_pos_w": robot.data.body_pos_w,
        "body_quat_w": robot.data.body_quat_w,
        "root_lin_vel_w": robot.data.root_lin_vel_w,
        "root_ang_vel_w": robot.data.root_ang_vel_w,
        "contact_forces": sensor.data.net_forces_w,
    }
    for name, tensor in tensors.items():
        _assert_finite(tensor, name)
    residuals = _loop_residuals(robot)
    return {
        "loop": max(residuals.values()),
        "joint_speed": float(torch.max(torch.abs(robot.data.joint_vel)).item()),
        "root_linear_speed": float(torch.linalg.vector_norm(robot.data.root_lin_vel_w, dim=-1).max().item()),
        "root_angular_speed": float(torch.linalg.vector_norm(robot.data.root_ang_vel_w, dim=-1).max().item()),
        "contact_force": float(torch.linalg.vector_norm(sensor.data.net_forces_w, dim=-1).max().item()),
        "applied_effort": float(torch.max(torch.abs(robot.data.applied_torque)).item()),
        "passive_effort": float(torch.max(torch.abs(robot.data.applied_torque[:, passive_ids])).item()),
    }


def _merge_peaks(peaks: dict[str, float], sample: Mapping[str, float]) -> None:
    for name, value in sample.items():
        peaks[name] = max(peaks.get(name, 0.0), value)


def _validate_peaks(label: str, peaks: Mapping[str, float]) -> None:
    limits = {
        "loop": ARGS.max_loop_residual,
        "joint_speed": ARGS.max_joint_speed,
        "root_linear_speed": ARGS.max_root_linear_speed,
        "root_angular_speed": ARGS.max_root_angular_speed,
        "contact_force": ARGS.max_contact_force,
        "passive_effort": ARGS.max_passive_effort,
    }
    exceeded = {name: (peaks[name], limit) for name, limit in limits.items() if peaks[name] > limit}
    if exceeded:
        raise RuntimeError(f"{label} rollout exceeded stability gates: {exceeded}")


def _controlled_action(step: int, device: str) -> torch.Tensor:
    phase = math.sin(2.0 * math.pi * (step + 1) / ARGS.controlled_steps)
    pattern = torch.tensor([1.0, -1.0, -1.0, 1.0, 1.0, -1.0], device=device)
    return (ARGS.action_amplitude * phase * pattern).unsqueeze(0)


def main() -> int:
    _validate_args()
    env_cfg = parse_env_cfg(ARGS.task, device=ARGS.device, num_envs=1, use_fabric=True)
    env_cfg.scene.num_envs = 1
    if ARGS.compact_gpu_buffers:
        env_cfg.sim.physx.gpu_max_rigid_contact_count = 2**18
        env_cfg.sim.physx.gpu_max_rigid_patch_count = 2**14
        env_cfg.sim.physx.gpu_found_lost_pairs_capacity = 2**18
        env_cfg.sim.physx.gpu_found_lost_aggregate_pairs_capacity = 2**18
        env_cfg.sim.physx.gpu_total_aggregate_pairs_capacity = 2**18
        env_cfg.sim.physx.gpu_collision_stack_size = 2**24
        env_cfg.sim.physx.gpu_heap_capacity = 2**24
        env_cfg.sim.physx.gpu_temp_buffer_capacity = 2**22
    env = None
    try:
        env = gym.make(ARGS.task, cfg=env_cfg)
        unwrapped = env.unwrapped
        observation, _info = env.reset()
        robot: Articulation = unwrapped.scene["robot"]
        sensor: ContactSensor = unwrapped.scene["contact_forces"]
        policy_ids, passive_ids = _validate_topology_and_control(unwrapped, robot)
        _validate_reset(robot, observation)

        zero_peaks: dict[str, float] = {}
        zero_action = torch.zeros((1, 6), device=unwrapped.device)
        for _ in range(ARGS.zero_steps):
            observation, reward, terminated, truncated, _extras = env.step(zero_action)
            for name, value in {
                "observation": observation,
                "reward": reward,
                "terminated": terminated,
                "truncated": truncated,
            }.items():
                _assert_finite(value, f"zero rollout {name}")
            if bool(torch.any(terminated | truncated)):
                raise RuntimeError("zero-action rollout terminated or truncated unexpectedly")
            if torch.count_nonzero(robot.data.joint_effort_target[:, passive_ids]).item() != 0:
                raise RuntimeError("zero-action rollout wrote a nonzero passive joint effort target")
            _merge_peaks(zero_peaks, _sample_metrics(robot, sensor, passive_ids))
        _validate_peaks("zero-action", zero_peaks)

        controlled_peaks: dict[str, float] = {}
        for step in range(ARGS.controlled_steps):
            action = _controlled_action(step, unwrapped.device)
            observation, reward, terminated, truncated, _extras = env.step(action)
            for name, value in {
                "observation": observation,
                "reward": reward,
                "terminated": terminated,
                "truncated": truncated,
            }.items():
                _assert_finite(value, f"controlled rollout {name}")
            if bool(torch.any(terminated | truncated)):
                raise RuntimeError("controlled rollout terminated or truncated unexpectedly")
            if torch.count_nonzero(robot.data.joint_effort_target[:, passive_ids]).item() != 0:
                raise RuntimeError("controlled rollout wrote a nonzero passive joint effort target")
            _merge_peaks(controlled_peaks, _sample_metrics(robot, sensor, passive_ids))
        _validate_peaks("controlled", controlled_peaks)

        expected_scale = torch.tensor(
            [
                next(
                    group.action_scale
                    for group in SERIALLEG_CONTRACT.actuator_groups.values()
                    if joint_name in group.joint_names
                )
                for joint_name in SERIALLEG_CONTRACT.policy_joint_order
            ],
            device=unwrapped.device,
        )
        action_term = unwrapped.action_manager.get_term("joint_effort")
        if not torch.allclose(action_term.processed_actions, action_term.raw_actions * expected_scale, atol=1e-6):
            raise RuntimeError("processed policy effort does not match the contract action scale")
        peak_contact = max(zero_peaks["contact_force"], controlled_peaks["contact_force"])
        if peak_contact < ARGS.min_contact_force:
            raise RuntimeError(f"ground contact was not observed: peak={peak_contact:.3f} N")

        print(
            f"[serialleg-task-smoke] task={ARGS.task} device={unwrapped.device} "
            f"gpu_buffers={'compact' if ARGS.compact_gpu_buffers else 'default'} "
            f"gym_make=true reset=true rollout=true bodies={robot.num_bodies} dofs={robot.num_joints}",
            flush=True,
        )
        print(
            f"[serialleg-task-smoke] policy_joints={tuple(robot.joint_names[index] for index in policy_ids)} "
            f"passive_joints={tuple(robot.joint_names[index] for index in passive_ids)} action_dim=6",
            flush=True,
        )
        for label, peaks in (("zero", zero_peaks), ("controlled", controlled_peaks)):
            print(
                f"[serialleg-task-smoke] phase={label} loop={peaks['loop']:.3e}m "
                f"joint_speed={peaks['joint_speed']:.3f}rad/s root_linear={peaks['root_linear_speed']:.3f}m/s "
                f"root_angular={peaks['root_angular_speed']:.3f}rad/s contact={peaks['contact_force']:.3f}N "
                f"effort={peaks['applied_effort']:.3f}Nm passive_effort={peaks['passive_effort']:.3e}Nm",
                flush=True,
            )
        return 0
    finally:
        if env is not None:
            env.close()


if __name__ == "__main__":
    exit_code = 1
    try:
        exit_code = main()
    except Exception as error:
        print(f"[serialleg-task-smoke][error] {type(error).__name__}: {error}", file=sys.stderr, flush=True)
        traceback.print_exc()
    sys.stdout.flush()
    sys.stderr.flush()
    if exit_code != 0:
        os._exit(exit_code)
    SIMULATION_APP.close()
    os._exit(exit_code)
