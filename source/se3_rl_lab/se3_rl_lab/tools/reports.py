"""Evaluation scoring and Markdown reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def evaluation_score(metrics: dict[str, Any]) -> float:
    summary = metrics["summary"]
    return float(
        summary["survival_rate"] * 100.0
        - summary["velocity_rmse"] * 15.0
        - summary["yaw_rate_rmse"] * 3.0
        - summary["max_loop_residual_m"] * 10000.0
        - summary["max_virtual_root_drift_rad"] * 1000.0
    )


def write_evaluation_report(metrics: dict[str, Any], output_path: Path) -> None:
    summary = metrics["summary"]
    lines = [
        f"# Evaluation: {metrics['checkpoint_name']}",
        "",
        f"- Suite: `{metrics['suite']}`",
        f"- Score: `{evaluation_score(metrics):.3f}`",
        f"- Steps: `{summary['steps']}`",
        f"- Survival rate: `{summary['survival_rate']:.4f}`",
        f"- Velocity RMSE: `{summary['velocity_rmse']:.4f} m/s`",
        f"- Yaw-rate RMSE: `{summary['yaw_rate_rmse']:.4f} rad/s`",
        f"- Maximum loop residual: `{summary['max_loop_residual_m']:.6e} m`",
        f"- Maximum virtual-root drift: `{summary['max_virtual_root_drift_rad']:.6e} rad`",
        f"- Non-finite samples: `{summary['non_finite_samples']}`",
        "",
        "## Scenarios",
        "",
        "| Scenario | Steps | vx RMSE | yaw RMSE | Terminations |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for scenario in metrics["scenarios"]:
        lines.append(
            f"| {scenario['name']} | {scenario['steps']} | {scenario['velocity_rmse']:.4f} | "
            f"{scenario['yaw_rate_rmse']:.4f} | {scenario['terminations']} |"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def compare_metrics(paths: list[Path], output_path: Path) -> None:
    evaluations = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    evaluations.sort(key=evaluation_score, reverse=True)
    lines = [
        "# SerialLeg evaluation comparison",
        "",
        "| Rank | Checkpoint | Score | Survival | vx RMSE | yaw RMSE | Loop residual |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rank, metrics in enumerate(evaluations, start=1):
        summary = metrics["summary"]
        lines.append(
            f"| {rank} | {metrics['checkpoint_name']} | {evaluation_score(metrics):.3f} | "
            f"{summary['survival_rate']:.4f} | {summary['velocity_rmse']:.4f} | "
            f"{summary['yaw_rate_rmse']:.4f} | {summary['max_loop_residual_m']:.3e} |"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
