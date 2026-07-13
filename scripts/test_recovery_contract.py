"""Static contract tests for the recovery task without launching Isaac Sim."""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest
import torch

ROOT = Path(__file__).parents[1]
CFG_PATH = ROOT / "source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/recovery_env_cfg.py"
REGISTER_PATH = ROOT / "source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/__init__.py"
PPO_CFG_PATH = ROOT / "source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/agents/rsl_rl_ppo_cfg.py"
REWARDS_PATH = ROOT / "source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/mdp/rewards.py"
REWARD_MATH_PATH = ROOT / "source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/mdp/reward_math.py"
CACHE_PATH = (
    ROOT / "source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg/recovery_states/serialleg_closedchain_stair_v3_40k.npz"
)
FOURBAR_PATH = ROOT / "source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/mdp/fourbar_reset.py"
HEIGHT_DEFAULT_PATH = ROOT / "source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/mdp/height_defaults.py"
ACTIONS_PATH = ROOT / "source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/mdp/actions.py"
COMMANDS_PATH = ROOT / "source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/mdp/commands.py"
RECOVERY_EVENTS_PATH = ROOT / "source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/mdp/recovery_events.py"

EXPECTED_WEIGHTS = {
    "tracking_lin_vel": 3.0,
    "tracking_ang_vel": 1.5,
    "upward": 3.0,
    "tracking_height": -1500.0,
    "lin_vel_z": -2.0,
    "ang_vel_xy": -0.05,
    "upright_orientation_l2": -0.5,
    "upright_zero_velocity": -0.05,
    "stand_still": -2.0,
    "joint_pos_penalty": -1.0,
    "leg_action_rate": -0.001,
    "wheel_action_rate": -0.001,
    "action_smoothness": -0.03,
    "leg_torques": -2.0e-4,
    "leg_dof_acc": -2.5e-7,
    "leg_power": -1.0e-4,
    "wheel_torques": -1.0e-4,
    "joint_mirror": -0.05,
    "dof_pos_limits": -5.0,
    "collision": -1.0,
    "contact_forces": -1.5e-4,
    "wheel_air_velocity": -1.0e-3,
    "leg_contact": -1.0,
    "wheel_contact_without_cmd": 0.1,
    "diagnostics": 1.0,
}


def _classes() -> dict[str, ast.ClassDef]:
    module = ast.parse(CFG_PATH.read_text(encoding="utf-8"))
    return {node.name: node for node in module.body if isinstance(node, ast.ClassDef)}


def test_recovery_reward_names_and_weights_are_locked() -> None:
    rewards = _classes()["RecoveryRewardsCfg"]
    actual: dict[str, float] = {}
    for node in rewards.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        weight = next((keyword.value for keyword in node.value.keywords if keyword.arg == "weight"), None)
        if weight is not None:
            actual[node.targets[0].id] = float(ast.literal_eval(weight))
    assert actual == EXPECTED_WEIGHTS


def test_recovery_yaw_tracking_preserves_large_error_gradient() -> None:
    rewards = _classes()["RecoveryRewardsCfg"]
    tracking_ang_vel = next(
        node.value
        for node in rewards.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "tracking_ang_vel"
    )
    params = next(keyword.value for keyword in tracking_ang_vel.keywords if keyword.arg == "params")
    configured = {
        ast.literal_eval(key): ast.literal_eval(value)
        for key, value in zip(params.keys, params.values, strict=True)
        if ast.literal_eval(key) in {"sigma", "sigma_cmd_scale", "ratio_blend"}
    }
    assert configured == {"sigma": 0.25, "sigma_cmd_scale": 0.4, "ratio_blend": 0.2}

    spec = importlib.util.spec_from_file_location("reward_math_under_test", REWARD_MATH_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    error = torch.tensor([6.0], requires_grad=True)
    command = torch.tensor([12.0])
    gate = torch.ones(1)
    reward = module.angular_tracking_reward(
        error,
        command,
        gate,
        sigma=0.25,
        sigma_cmd_scale=0.4,
        ratio_blend=0.2,
    )
    reward.sum().backward()

    assert reward.item() == pytest.approx(0.1, abs=1.0e-6)
    assert error.grad is not None
    assert error.grad.item() < -0.01


def test_recovery_changes_rewards_terminations_reset_and_height_action_default() -> None:
    recovery = _classes()["RecoveryEnvCfg"]
    assigned = {
        node.target.id
        for node in recovery.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }
    assert assigned == {"rewards", "terminations"}
    source = ast.unparse(recovery)
    assert "self.events.reset_base" in source
    assert "reset_root_state_recovery_mixed" in source
    assert "reset_recovery_joints" in source
    assert "settle_physics_steps" not in source
    assert "self.actions.serialleg_delayed.height_conditioned_action_default = True" in source
    assert "self.actions.serialleg_delayed.action_default_command_name" in source
    assert "velocity_height" in source
    assert "self.observations" not in source
    assert "self.commands" not in source


def test_height_conditioned_default_is_wired_through_the_complete_contract() -> None:
    height_source = HEIGHT_DEFAULT_PATH.read_text(encoding="utf-8")
    assert "def policy_default_from_height" in height_source
    assert "def update_height_default_cache" in height_source
    assert "def get_height_default" in height_source
    assert "_LUT_SIZE = 1024" in height_source
    assert "_FOURBAR_LUT_SIZE = 8192" in height_source

    actions_source = ACTIONS_PATH.read_text(encoding="utf-8")
    assert "height_conditioned_action_default: bool = False" in actions_source
    assert "get_height_default(" in actions_source
    assert "active_default =" in actions_source

    commands_source = COMMANDS_PATH.read_text(encoding="utf-8")
    assert "update_height_default_cache" in commands_source

    reset_source = RECOVERY_EVENTS_PATH.read_text(encoding="utf-8")
    assert "update_height_default_cache" in reset_source
    assert "policy_pos.copy_(" in reset_source

    rewards_source = REWARDS_PATH.read_text(encoding="utf-8")
    assert "def _height_default" in rewards_source
    assert "default = _height_default(env, command_name, robot)" in rewards_source


def test_height_default_matches_reference_repository_across_command_range(monkeypatch) -> None:
    contract_module = ModuleType("se3_rl_lab.assets.robots.serialleg_contract")
    contract_module.SERIALLEG_CONTRACT = SimpleNamespace(
        fixed_tendons={
            "left": SimpleNamespace(lower=0.0, upper=np.deg2rad(86.49)),
            "right": SimpleNamespace(lower=0.0, upper=np.deg2rad(86.49)),
        }
    )
    monkeypatch.setitem(sys.modules, "se3_rl_lab.assets.robots.serialleg_contract", contract_module)
    spec = importlib.util.spec_from_file_location("height_defaults_under_test", HEIGHT_DEFAULT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    heights = torch.tensor([0.20, 0.22, 0.26, 0.30, 0.32])
    actual = module.policy_default_from_height(heights)
    expected = torch.tensor(
        [
            [-0.1456190795, -1.6063432693, 0.1456190795, 1.6063432693],
            [-0.2379817665, -1.5504239798, 0.2379817665, 1.5504239798],
            [-0.4081358612, -1.4373246431, 0.4081358612, 1.4373246431],
            [-0.5728592873, -1.3166157007, 0.5728592873, 1.3166157007],
            [-0.6571400762, -1.2521665096, 0.6571400762, 1.2521665096],
        ]
    )
    torch.testing.assert_close(actual, expected, atol=2.0e-6, rtol=0.0)


def test_recovery_loco_variant_and_dense_rewards_are_absent() -> None:
    classes = _classes()
    assert "RecoveryLocoRewardsCfg" not in classes
    assert "RecoveryLocoEnvCfg" not in classes
    cfg_source = CFG_PATH.read_text(encoding="utf-8")
    assert "_LOCO_" not in cfg_source
    rewards_source = REWARDS_PATH.read_text(encoding="utf-8")
    assert "recovery_tracking_lin_vel_dense" not in rewards_source
    assert "recovery_tracking_ang_vel_dense" not in rewards_source
    registration = REGISTER_PATH.read_text(encoding="utf-8")
    assert 'id="SerialLeg-Recovery-Loco-v0"' not in registration


def test_recovery_keeps_reference_hard_error_termination_and_is_registered() -> None:
    terminations = _classes()["RecoveryTerminationsCfg"]
    names = {
        node.targets[0].id
        for node in terminations.body
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
    }
    assert names == {"time_out", "catastrophic_state"}
    registration = REGISTER_PATH.read_text(encoding="utf-8")
    assert 'id="SerialLeg-Recovery-v0"' in registration
    assert "recovery_env_cfg:RecoveryEnvCfg" in registration


def test_recovery_uses_reference_exploration_settings_without_changing_flat() -> None:
    registration = REGISTER_PATH.read_text(encoding="utf-8")
    assert registration.count("rsl_rl_ppo_cfg:RecoveryPPORunnerCfg") == 1
    assert registration.count("rsl_rl_ppo_cfg:PPORunnerCfg") == 1

    module = ast.parse(PPO_CFG_PATH.read_text(encoding="utf-8"))
    recovery = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "RecoveryPPORunnerCfg"
    )
    assignments = {
        node.targets[0].id: node.value
        for node in recovery.body
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
    }
    actor = assignments["actor"]
    algorithm = assignments["algorithm"]
    distribution = next(keyword.value for keyword in actor.keywords if keyword.arg == "distribution_cfg")
    init_std = next(keyword.value for keyword in distribution.keywords if keyword.arg == "init_std")
    assert ast.literal_eval(init_std) == 0.5
    expected_algorithm = {
        "entropy_coef": 0.00516,
        "learning_rate": 3.0e-4,
        "desired_kl": 0.008,
    }
    actual_algorithm = {
        keyword.arg: float(ast.literal_eval(keyword.value))
        for keyword in algorithm.keywords
        if keyword.arg in expected_algorithm
    }
    assert actual_algorithm == expected_algorithm


def test_recovery_cache_contains_full_closedchain_state() -> None:
    data = np.load(CACHE_PATH)
    assert data["root_pos"].shape == (40000, 3)
    assert data["joint_pos"].shape == (40000, 10)
    assert data["joint_vel"].shape == (40000, 10)
    assert set(data["split"].astype(str)) == {"train", "eval"}
    assert tuple(data["joint_names"].tolist()) == (
        "lf0_Joint",
        "lf1_Joint",
        "l_wheel_Joint",
        "l_drive_bar_Joint",
        "l_coupler_Joint",
        "rf0_Joint",
        "rf1_Joint",
        "r_wheel_Joint",
        "r_drive_bar_Joint",
        "r_coupler_Joint",
    )


def test_policy_default_maps_to_canonical_passive_pose() -> None:
    spec = importlib.util.spec_from_file_location("fourbar_reset_under_test", FOURBAR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    policy = torch.tensor([[-0.275422946189, -1.592100148957, 0.275422946189, 1.592100148957]])
    passive = module.policy_to_passive_pos(policy)
    expected = torch.tensor([[-1.242259649307, 1.40126634, 1.242259649307, -1.40126941]])
    torch.testing.assert_close(passive, expected, atol=2.0e-5, rtol=0.0)
    velocity = module.policy_to_passive_vel(policy, torch.zeros_like(policy))
    torch.testing.assert_close(velocity, torch.zeros_like(velocity))
