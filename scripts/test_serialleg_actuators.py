"""CPU-only contract tests for SerialLeg motor envelopes and actuator wiring."""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).parents[1]
MOTOR_PATH = ROOT / "source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg_motors.py"
ASSET_CFG_PATH = ROOT / "source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg.py"


def _load_motors():
    spec = importlib.util.spec_from_file_location("serialleg_motors_under_test", MOTOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_m3508_measured_curve_is_exact_and_interpolated_symmetrically() -> None:
    motors = _load_motors()
    curve = motors.M3508_C620_14_TORQUE_SPEED_CURVE
    assert curve == (
        (0.00, 3.71),
        (32.93, 3.71),
        (49.07, 3.61),
        (57.82, 3.54),
        (63.65, 3.46),
        (65.29, 3.39),
        (65.70, 3.32),
        (67.43, 2.95),
        (69.28, 2.21),
        (70.90, 1.47),
        (71.37, 0.74),
        (71.81, 0.00),
    )
    speeds = np.array([0.0, 32.93, 60.735, 67.43, 70.90, 71.81, 80.0])
    expected = np.array([3.71, 3.71, 3.50, 2.95, 1.47, 0.0, 0.0])
    np.testing.assert_allclose(motors.M3508_C620_14.torque_limit_np(speeds), expected, atol=1.0e-12)
    np.testing.assert_allclose(
        motors.M3508_C620_14.torque_limit_np(-speeds),
        expected,
        atol=1.0e-12,
    )


def test_m3508_effort_clipping_uses_current_speed_envelope() -> None:
    motors = _load_motors()
    effort = np.array([10.0, -10.0, 10.0, -10.0])
    velocity = np.array([0.0, 67.43, 70.90, 71.81])
    expected = np.array([3.71, -2.95, 1.47, 0.0])
    np.testing.assert_allclose(
        motors.M3508_C620_14.clip_effort_np(effort, velocity),
        expected,
        atol=1.0e-12,
    )


def test_m3508_dense_envelope_is_finite_symmetric_and_nonincreasing() -> None:
    motors = _load_motors()
    speed = np.linspace(0.0, 1.1 * motors.M3508_C620_14.no_load_speed, 2001)
    limit = motors.M3508_C620_14.torque_limit_np(speed)
    assert np.all(np.isfinite(limit))
    assert np.all(limit >= 0.0)
    assert np.all(np.diff(limit) <= 1.0e-12)
    np.testing.assert_allclose(limit, motors.M3508_C620_14.torque_limit_np(-speed), atol=1.0e-12)


def test_dm8009p_uses_four_quadrant_continuous_and_stall_limits() -> None:
    motors = _load_motors()
    motor = motors.DM8009P
    assert motor.stall_torque == 40.0
    assert motor.rated_torque == 20.0
    np.testing.assert_allclose(
        motor.clip_effort_np(
            np.array([100.0, -100.0, 100.0, -100.0, 100.0, -100.0]),
            np.array([0.0, 0.0, motor.no_load_speed, motor.no_load_speed, -motor.no_load_speed, -motor.no_load_speed]),
        ),
        np.array([20.0, -20.0, 0.0, -20.0, 20.0, 0.0]),
        atol=1.0e-12,
    )


def test_asset_wires_explicit_motor_models_without_physics_velocity_clamps() -> None:
    module = ast.parse(ASSET_CFG_PATH.read_text(encoding="utf-8"))
    calls = {
        node.func.id: node
        for node in ast.walk(module)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    leg = calls["DCMotorCfg"]
    wheel = calls["TorqueSpeedCurveActuatorCfg"]
    leg_keywords = {keyword.arg for keyword in leg.keywords}
    wheel_keywords = {keyword.arg for keyword in wheel.keywords}
    assert {"effort_limit", "velocity_limit", "saturation_effort", "effort_limit_sim"} <= leg_keywords
    assert "velocity_limit_sim" not in leg_keywords
    assert {"effort_limit", "effort_limit_sim", "torque_speed_curve"} <= wheel_keywords
    assert "velocity_limit_sim" not in wheel_keywords


def test_policy_action_contract_remains_unchanged() -> None:
    action_path = ROOT / "source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/mdp/actions.py"
    source = action_path.read_text(encoding="utf-8")
    robot_config_path = ROOT / "source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg/robot_config.yaml"
    robot_config = yaml.safe_load(robot_config_path.read_text(encoding="utf-8"))
    groups = robot_config["joints"]["groups"]
    assert groups["legs"]["action_scale"] == 0.25
    assert groups["wheels"]["action_scale"] == 45.0
    assert '_LEG_ACTION_SCALE = _required_action_scale("legs")' in source
    assert '_WHEEL_ACTION_SCALE = _required_action_scale("wheels")' in source
    assert "leg_scale: float = _LEG_ACTION_SCALE" in source
    assert "wheel_scale: float = _WHEEL_ACTION_SCALE" in source
    assert "set_joint_position_target" in source
    assert "set_joint_velocity_target" in source
