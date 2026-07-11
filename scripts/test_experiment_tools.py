"""Pure-Python tests for run metadata and evaluation reports."""

from __future__ import annotations

import json
from pathlib import Path

from se3_rl_lab.tools.reports import compare_metrics, evaluation_score, write_evaluation_report
from se3_rl_lab.tools.rerun_export import export_rerun
from se3_rl_lab.tools.runs import RunDirectory, checkpoint_iteration


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
