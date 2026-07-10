"""CPU-only contract tests for SerialLeg's 34D/40D observations."""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

_MODULE_PATH = (
    Path(__file__).parents[1] / "source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/mdp/observations.py"
)
_SPEC = importlib.util.spec_from_file_location("serialleg_observations_under_test", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
obs = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(obs)


class _CommandManager:
    def __init__(self, command: torch.Tensor | None):
        self.active_terms = () if command is None else ("velocity_height",)
        self._command = command

    def get_command(self, name: str) -> torch.Tensor:
        assert name == "velocity_height"
        assert self._command is not None
        return self._command


class _ActionManager:
    active_terms = ("serialleg_delayed",)

    def __init__(self, policy_action: torch.Tensor):
        self.action = torch.full_like(policy_action, -99.0)
        self._term = SimpleNamespace(policy_action=policy_action)

    def get_term(self, name: str) -> SimpleNamespace:
        assert name == "serialleg_delayed"
        return self._term


def _fixture(command: torch.Tensor | None = None):
    joint_pos = torch.zeros(2, 12)
    default_pos = torch.zeros_like(joint_pos)
    joint_vel = torch.zeros_like(joint_pos)
    leg_ids = [1, 4, 7, 9]
    wheel_ids = [3, 8]
    joint_pos[:, leg_ids] = torch.tensor([[0.2, -0.3, -0.4, 0.1], [0.0, 0.0, 0.0, 0.0]])
    joint_vel[:, leg_ids] = torch.tensor([[4.0, 8.0, 12.0, 16.0], [0.0, 0.0, 0.0, 0.0]])
    joint_vel[:, wheel_ids] = torch.tensor([[20.0, -40.0], [0.0, 0.0]])
    # Huge virtual/passive state proves selection is only through resolved policy ids.
    joint_pos[:, [0, 2, 5, 6, 10, 11]] = 999.0
    joint_vel[:, [0, 2, 5, 6, 10, 11]] = 999.0
    robot = SimpleNamespace(
        data=SimpleNamespace(
            joint_pos=joint_pos,
            default_joint_pos=default_pos,
            joint_vel=joint_vel,
            root_ang_vel_b=torch.tensor([[4.0, -8.0, 12.0], [0.0, 0.0, 0.0]]),
            root_lin_vel_b=torch.tensor([[1.0, 2.0, 3.0], [0.0, 0.0, 0.0]]),
            projected_gravity_b=torch.tensor([[0.0, 0.0, -1.0], [0.0, 0.0, -1.0]]),
            root_pos_w=torch.tensor([[0.0, 0.0, 0.30], [2.0, 0.0, 1.25]]),
        )
    )
    force = torch.zeros(2, 5, 3)
    force[0, 1] = torch.tensor([3.0, 4.0, 0.0])
    force[0, 4] = torch.tensor([0.0, 0.0, 12.0])
    sensor = SimpleNamespace(data=SimpleNamespace(net_forces_w=force))
    scene = _Scene({"robot": robot, "contact_forces": sensor})
    scene.env_origins = torch.tensor([[0.0, 0.0, 0.0], [2.0, 0.0, 1.0]])
    policy_action = torch.tensor([[0.1, 0.2, 0.3, 0.4, 0.5, 0.6], [0.0] * 6])
    env = SimpleNamespace(
        scene=scene,
        command_manager=_CommandManager(command),
        action_manager=_ActionManager(policy_action),
    )
    robot_cfg = SimpleNamespace(name="robot")
    leg_cfg = SimpleNamespace(name="robot", joint_ids=leg_ids)
    wheel_cfg = SimpleNamespace(name="robot", joint_ids=wheel_ids)
    sensor_cfg = SimpleNamespace(name="contact_forces", body_ids=[1, 4])
    return env, robot_cfg, leg_cfg, wheel_cfg, sensor_cfg


class _Scene(dict):
    pass


def test_actor_and_critic_layout_values_and_policy_joint_isolation() -> None:
    command = torch.tensor([[0.5, 4.0, 0.1, -0.2, 0.25, 1.0, 0.4, 0.75], [0.0] * 8], dtype=torch.float32)
    env, robot_cfg, leg_cfg, wheel_cfg, sensor_cfg = _fixture(command)
    actor = torch.cat(
        (
            obs.base_ang_vel_obs(env, robot_cfg),
            obs.projected_gravity_obs(env, robot_cfg),
            obs.commands_obs(env, robot_cfg),
            obs.leg_joint_pos_obs(env, leg_cfg),
            obs.leg_joint_vel_obs(env, leg_cfg),
            obs.wheel_pos_obs(env, wheel_cfg),
            obs.wheel_vel_obs(env, wheel_cfg),
            obs.last_actions_obs(env),
            obs.jump_commands_obs(env, robot_cfg),
        ),
        dim=1,
    )
    critic = torch.cat(
        (
            actor,
            obs.base_lin_vel_obs(env, robot_cfg),
            obs.wheel_contact_force_obs(env, sensor_cfg),
            obs.flat_base_height_obs(env, robot_cfg),
        ),
        dim=1,
    )

    assert actor.shape == (2, obs.ACTOR_OBSERVATION_DIM)
    assert critic.shape == (2, obs.CRITIC_OBSERVATION_DIM)
    assert torch.allclose(actor[0, 0:3], torch.tensor([1.0, -2.0, 3.0]))
    assert torch.allclose(actor[0, 6:11], torch.tensor([1.0, 1.0, 0.5, -1.0, 1.25]))
    assert torch.allclose(
        actor[0, 11:17],
        torch.tensor([math.sin(0.2), math.cos(0.2), 0.5, math.sin(-0.4), math.cos(-0.4), 0.5]),
    )
    assert torch.allclose(actor[0, 17:21], torch.tensor([1.0, 2.0, 3.0, 4.0]))
    assert torch.equal(actor[:, 21:23], torch.zeros(2, 2))
    assert torch.allclose(actor[0, 23:25], torch.tensor([1.0, -2.0]))
    assert torch.allclose(actor[0, 25:31], env.action_manager._term.policy_action[0])
    assert torch.allclose(actor[0, 31:34], torch.tensor([1.0, 0.4, 0.75]))
    assert torch.allclose(critic[0, 34:40], torch.tensor([1.0, 2.0, 3.0, 5.0, 12.0, 0.3]))
    assert torch.allclose(critic[1, 39:40], torch.tensor([0.25]))
    assert max(abs(float(value)) for value in actor[0]) < 100.0


def test_layout_metadata_is_contiguous_and_exact() -> None:
    slices = list(obs.ACTOR_OBSERVATION_LAYOUT.values()) + list(obs.CRITIC_PRIVILEGED_LAYOUT.values())
    assert [(item.start, item.stop) for item in slices] == [
        (0, 3),
        (3, 6),
        (6, 11),
        (11, 17),
        (17, 21),
        (21, 23),
        (23, 25),
        (25, 31),
        (31, 34),
        (34, 37),
        (37, 39),
        (39, 40),
    ]


def test_absent_command_term_uses_only_transitional_zero_fallback() -> None:
    env, robot_cfg, *_ = _fixture(None)
    assert torch.equal(obs.commands_obs(env, robot_cfg), torch.zeros(2, 5))
    assert torch.equal(obs.jump_commands_obs(env, robot_cfg), torch.zeros(2, 3))


def test_existing_command_term_with_wrong_dimension_fails_hard() -> None:
    env, robot_cfg, *_ = _fixture(torch.zeros(2, 7))
    with pytest.raises(ValueError, match="requires shape .*8"):
        obs.commands_obs(env, robot_cfg)
