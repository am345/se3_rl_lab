"""Export evaluation telemetry to a Rerun recording."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def export_rerun(samples: list[dict[str, Any]], output_path: Path, *, application_id: str) -> None:
    try:
        import rerun as rr
    except ImportError as exc:
        raise RuntimeError("Rerun export requires the 'rerun-sdk' dependency") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    rr.init(application_id, spawn=False)
    rr.save(str(output_path))
    for sample in samples:
        rr.set_time_sequence("step", int(sample["step"]))
        rr.log("command/vx", rr.Scalar(float(sample["command_vx"])))
        rr.log("command/yaw_rate", rr.Scalar(float(sample["command_yaw_rate"])))
        rr.log("state/vx", rr.Scalar(float(sample["base_vx"])))
        rr.log("state/yaw_rate", rr.Scalar(float(sample["base_yaw_rate"])))
        rr.log("state/base_height", rr.Scalar(float(sample["base_height"])))
        rr.log("diagnostics/loop_residual", rr.Scalar(float(sample["loop_residual_m"])))
        rr.log("diagnostics/virtual_root_drift", rr.Scalar(float(sample["virtual_root_drift_rad"])))
        rr.log("diagnostics/terminated", rr.Scalar(float(sample["terminated"])))
