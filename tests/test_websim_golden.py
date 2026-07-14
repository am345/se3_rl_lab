import importlib.util
import json
from pathlib import Path

import numpy as np
import torch
from se3_rl_lab.assets.robots.serialleg_motors import DM8009P, M3508_C620_14

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "websim_se3/frontend/tests/fixtures/serialleg-golden.json"
HEIGHT_DEFAULTS = (
    ROOT / "source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/mdp/height_defaults.py"
)


def _height_module():
    spec = importlib.util.spec_from_file_location("websim_height_defaults", HEIGHT_DEFAULTS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_browser_golden_fixture_matches_native_contract() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    heights = torch.tensor(fixture["heights"], dtype=torch.float32)
    defaults = _height_module().policy_default_from_height(heights)

    np.testing.assert_allclose(defaults.numpy(), fixture["defaults"], atol=2.0e-5)
    for case in fixture["legMotorCases"]:
        assert np.isclose(DM8009P.clip_effort_np(case["request"], case["velocity"]), case["expected"])
    for case in fixture["wheelMotorCases"]:
        assert np.isclose(M3508_C620_14.clip_effort_np(case["request"], case["velocity"]), case["expected"])
    for case in fixture["periodicLegErrorCases"]:
        target = np.array([[case["target"], 0.0, case["target"], 0.0]])
        position = np.array([[case["position"], 0.0, case["position"], 0.0]])
        error = np.arctan2(np.sin(target - position), np.cos(target - position))
        assert np.isclose(error[0, 0], case["expected"])
        assert np.isclose(error[0, 2], case["expected"])
    for case in fixture["baseMotionCases"]:
        quaternion = np.asarray(case["quaternion"], dtype=np.float64)
        velocity = np.asarray(case["freeJointVelocity"], dtype=np.float64)
        w, x, y, z = quaternion
        rotation = np.array(
            [
                [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
            ]
        )
        np.testing.assert_allclose(velocity[3:6] * 0.25, case["expectedAngularVelocity"])
        np.testing.assert_allclose(
            rotation.T @ np.array([0.0, 0.0, -1.0]),
            case["expectedProjectedGravity"],
            atol=1e-12,
        )
