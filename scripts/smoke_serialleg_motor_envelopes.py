#!/usr/bin/env python3
"""Verify runtime SerialLeg actuators against the shared motor T-N envelopes."""

from __future__ import annotations

import argparse

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--samples", type=int, default=801, help="Velocity samples per motor envelope")
AppLauncher.add_app_launcher_args(parser)
parser.set_defaults(headless=True, device="cuda:0")
ARGS = parser.parse_args()
APP = AppLauncher(ARGS, fast_shutdown=True).app

import gymnasium as gym  # noqa: E402
import numpy as np  # noqa: E402
import se3_rl_lab.tasks  # noqa: F401, E402
import torch  # noqa: E402
from se3_rl_lab.assets.robots.serialleg_actuators import TorqueSpeedCurveActuator  # noqa: E402
from se3_rl_lab.assets.robots.serialleg_motors import DM8009P, M3508_C620_14  # noqa: E402

from isaaclab.actuators import DCMotor  # noqa: E402

from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402


def _assert_close(actual: np.ndarray, expected: np.ndarray, label: str, *, atol: float = 2.0e-5) -> float:
    error = float(np.max(np.abs(actual - expected)))
    if not np.all(np.isfinite(actual)) or error > atol:
        raise RuntimeError(f"{label} envelope mismatch: max_error={error:.6e} atol={atol:.6e}")
    return error


def _check_wheel(actuator: TorqueSpeedCurveActuator) -> float:
    velocities = np.linspace(-1.1 * M3508_C620_14.no_load_speed, 1.1 * M3508_C620_14.no_load_speed, ARGS.samples)
    actual_samples: list[np.ndarray] = []
    expected_samples: list[np.ndarray] = []
    request_np = np.array([1.0e6, -1.0e6], dtype=np.float64)
    request = torch.tensor(request_np, device=actuator._joint_vel.device, dtype=actuator._joint_vel.dtype).unsqueeze(0)
    with torch.inference_mode():
        for velocity in velocities:
            actuator._joint_vel.fill_(float(velocity))
            actual_samples.append(actuator._clip_effort(request).squeeze(0).cpu().numpy().astype(np.float64))
            expected_samples.append(M3508_C620_14.clip_effort_np(request_np, velocity))
    return _assert_close(np.stack(actual_samples), np.stack(expected_samples), "wheel")


def _check_leg(actuator: DCMotor) -> float:
    corner_speed = DM8009P.no_load_speed * (1.0 + DM8009P.rated_torque / DM8009P.stall_torque)
    velocities = np.linspace(-1.1 * corner_speed, 1.1 * corner_speed, ARGS.samples)
    request_np = np.array([1.0e6, -1.0e6, 1.0e6, -1.0e6], dtype=np.float64)
    request = torch.tensor(request_np, device=actuator._joint_vel.device, dtype=actuator._joint_vel.dtype).unsqueeze(0)
    actual_samples: list[np.ndarray] = []
    expected_samples: list[np.ndarray] = []
    with torch.inference_mode():
        for velocity in velocities:
            actuator._joint_vel.fill_(float(velocity))
            actual_samples.append(actuator._clip_effort(request).squeeze(0).cpu().numpy().astype(np.float64))
            expected_samples.append(DM8009P.clip_effort_np(request_np, velocity))
    return _assert_close(np.stack(actual_samples), np.stack(expected_samples), "leg")


def main() -> None:
    if ARGS.samples < 3:
        raise ValueError(f"--samples must be at least 3, got {ARGS.samples}")
    cfg = parse_env_cfg("SerialLeg-Recovery-v0", device=ARGS.device, num_envs=1, use_fabric=True)
    leg_cfg = cfg.scene.robot.actuators["legs"]
    wheel_cfg = cfg.scene.robot.actuators["wheels"]
    if leg_cfg.velocity_limit_sim is not None or wheel_cfg.velocity_limit_sim is not None:
        raise RuntimeError(
            "active motor models must not use PhysX velocity_limit_sim: "
            f"leg={leg_cfg.velocity_limit_sim} wheel={wheel_cfg.velocity_limit_sim}"
        )
    env = gym.make("SerialLeg-Recovery-v0", cfg=cfg)
    try:
        env.reset()
        robot = env.unwrapped.scene["robot"]
        leg = robot.actuators["legs"]
        wheel = robot.actuators["wheels"]
        if not isinstance(leg, DCMotor) or not isinstance(wheel, TorqueSpeedCurveActuator):
            raise RuntimeError(f"unexpected runtime actuators: leg={type(leg).__name__} wheel={type(wheel).__name__}")
        wheel_error = _check_wheel(wheel)
        leg_error = _check_leg(leg)
        print(
            "[serialleg-motor-envelope-smoke] "
            f"samples={ARGS.samples} leg_max_error={leg_error:.3e} wheel_max_error={wheel_error:.3e} "
            "velocity_limit_sim=none passed=true",
            flush=True,
        )
    finally:
        env.close()


if __name__ == "__main__":
    try:
        main()
    finally:
        APP.close()
