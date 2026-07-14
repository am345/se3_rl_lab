"""Pure-Python tests for run metadata and evaluation reports."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from se3_rl_lab.isaac_eval.camera import translated_follow_view, widened_focal_length
from se3_rl_lab.isaac_eval.schedule import (
    configure_fixed_command_eval,
    disable_policy_observation_corruption,
    set_command_and_refresh_observations,
)
from se3_rl_lab.tools.reports import compare_metrics, evaluation_score, write_evaluation_report
from se3_rl_lab.tools.rerun_export import export_rerun
from se3_rl_lab.tools.runs import RunDirectory, checkpoint_iteration

ROOT = Path(__file__).parents[1]


def _metrics(name: str, survival: float, velocity_rmse: float) -> dict:
    return {
        "checkpoint_name": name,
        "suite": "flat-basic",
        "summary": {
            "steps": 100,
            "survival_rate": survival,
            "velocity_rmse": velocity_rmse,
            "yaw_rate_rmse": 0.2,
            "max_loop_residual_m": 1e-4,
            "max_virtual_root_drift_rad": 1e-5,
            "non_finite_samples": 0,
        },
        "scenarios": [
            {
                "name": "forward_slow",
                "steps": 100,
                "velocity_rmse": velocity_rmse,
                "yaw_rate_rmse": 0.2,
                "terminations": 0,
            }
        ],
    }


def test_checkpoint_resolution_and_status(tmp_path: Path) -> None:
    run = RunDirectory(tmp_path)
    for iteration in (0, 10, 499):
        (tmp_path / f"model_{iteration}.pt").write_bytes(b"checkpoint")
    assert checkpoint_iteration(tmp_path / "model_10.pt") == 10
    assert run.checkpoint("latest").name == "model_499.pt"
    run.update_status(best_checkpoint=str(tmp_path / "model_10.pt"), best_score=12.0)
    assert run.checkpoint("best").name == "model_10.pt"


def test_reports_rank_by_score(tmp_path: Path) -> None:
    weak = _metrics("model_0", survival=0.5, velocity_rmse=1.0)
    strong = _metrics("model_499", survival=0.99, velocity_rmse=0.2)
    assert evaluation_score(strong) > evaluation_score(weak)
    weak_path = tmp_path / "weak.json"
    strong_path = tmp_path / "strong.json"
    weak_path.write_text(json.dumps(weak), encoding="utf-8")
    strong_path.write_text(json.dumps(strong), encoding="utf-8")
    write_evaluation_report(strong, tmp_path / "strong.md")
    compare_metrics([weak_path, strong_path], tmp_path / "comparison.md")
    comparison = (tmp_path / "comparison.md").read_text(encoding="utf-8")
    assert comparison.index("model_499") < comparison.index("model_0")


def test_rerun_export(tmp_path: Path) -> None:
    output = tmp_path / "telemetry.rrd"
    export_rerun(
        [
            {
                "step": 0,
                "command_vx": 0.1,
                "command_yaw_rate": 0.2,
                "base_vx": 0.0,
                "base_yaw_rate": 0.0,
                "base_height": 0.2,
                "loop_residual_m": 1e-5,
                "virtual_root_drift_rad": 1e-6,
                "terminated": False,
            }
        ],
        output,
        application_id="se3rl-test",
    )
    assert output.stat().st_size > 0


def test_eval_camera_follows_translation_without_rotating() -> None:
    eye_a, target_a = translated_follow_view((1.0, 2.0, 0.3))
    eye_b, target_b = translated_follow_view((4.0, -1.0, 0.8))
    translation = tuple(after - before for before, after in zip(target_a, target_b, strict=True))
    assert tuple(after - before for before, after in zip(eye_a, eye_b, strict=True)) == pytest.approx(translation)
    assert tuple(target - eye for eye, target in zip(eye_a, target_a, strict=True)) == pytest.approx(
        tuple(target - eye for eye, target in zip(eye_b, target_b, strict=True))
    )


def test_eval_camera_horizontal_fov_is_30_percent_wider() -> None:
    widened_focal, old_fov, new_fov = widened_focal_length(horizontal_aperture=20.955, focal_length=18.14756)
    assert new_fov == pytest.approx(old_fov * 1.3)
    assert widened_focal < 18.14756


def test_eval_worker_disables_training_observation_corruption() -> None:
    class GroupCfg:
        enable_corruption = True

    class FlatObservationsCfg:
        actor = GroupCfg()
        critic = GroupCfg()

    class FlatEnvCfg:
        observations = FlatObservationsCfg()

    flat_agent_cfg = type(
        "FlatAgentCfg",
        (),
        {"obs_groups": {"actor": ["actor"], "critic": ["critic"]}},
    )()
    assert disable_policy_observation_corruption(FlatEnvCfg(), flat_agent_cfg) == ("actor",)
    assert not FlatEnvCfg.observations.actor.enable_corruption
    assert FlatEnvCfg.observations.critic.enable_corruption

    class ObservationsCfg:
        command = GroupCfg()
        proprio = GroupCfg()
        privileged = GroupCfg()

    class EnvCfg:
        observations = ObservationsCfg()

    agent_cfg = type(
        "AgentCfg",
        (),
        {"obs_groups": {"actor": ["command", "proprio"], "critic": ["command", "privileged"]}},
    )()
    disabled = disable_policy_observation_corruption(EnvCfg(), agent_cfg)

    assert disabled == ("command", "proprio")
    assert not EnvCfg.observations.command.enable_corruption
    assert not EnvCfg.observations.proprio.enable_corruption
    assert EnvCfg.observations.privileged.enable_corruption


def test_run_manifest_uses_task_specific_observation_dimensions(tmp_path: Path) -> None:
    flat = RunDirectory(tmp_path / "flat").ensure_manifest(
        repo_root=ROOT,
        task="SerialLeg-Flat-v0",
        command=["train"],
    )
    recovery = RunDirectory(tmp_path / "recovery").ensure_manifest(
        repo_root=ROOT,
        task="SerialLeg-Recovery-v0",
        command=["train"],
    )

    assert (flat["actor_observation_dim"], flat["critic_observation_dim"]) == (34, 40)
    assert (recovery["actor_observation_dim"], recovery["critic_observation_dim"]) == (138, 168)


def test_fixed_command_eval_outlives_the_full_scenario_suite() -> None:
    class VelocityCommandCfg:
        resampling_time_range = (5.0, 5.0)

    class CommandsCfg:
        velocity_height = VelocityCommandCfg()

    class EnvCfg:
        episode_length_s = 20.0
        commands = CommandsCfg()

    env_cfg = EnvCfg()
    timing = configure_fixed_command_eval(
        env_cfg,
        scenario_count=6,
        scenario_duration_s=4.0,
    )

    assert timing.total_duration_s == pytest.approx(24.0)
    assert timing.protected_duration_s == pytest.approx(25.0)
    assert env_cfg.episode_length_s == pytest.approx(25.0)
    assert env_cfg.commands.velocity_height.resampling_time_range == pytest.approx((25.0, 25.0))


def test_fixed_command_is_visible_in_observations_before_policy_inference() -> None:
    torch = pytest.importorskip("torch")

    class CommandTerm:
        _command = torch.zeros((1, 8))

    command_term = CommandTerm()

    class CommandManager:
        @staticmethod
        def get_term(name: str):
            assert name == "velocity_height"
            return command_term

    class UnwrappedEnv:
        command_manager = CommandManager()

    class WrappedEnv:
        @staticmethod
        def get_observations():
            return {"actor": command_term._command.clone()}

    observations = set_command_and_refresh_observations(
        WrappedEnv(),
        UnwrappedEnv(),
        vx=0.5,
        yaw_rate=0.8,
        height=0.26,
    )

    assert observations["actor"][0, (0, 1, 4)].tolist() == pytest.approx([0.5, 0.8, 0.26])
