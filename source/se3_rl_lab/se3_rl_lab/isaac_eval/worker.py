"""Independent Isaac Sim evaluation and recording worker."""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
import math
from pathlib import Path

from isaaclab.app import AppLauncher

PARSER = argparse.ArgumentParser(description=__doc__)
PARSER.add_argument("--context", type=Path, required=True)
AppLauncher.add_app_launcher_args(PARSER)
ARGS = PARSER.parse_args()
ARGS.enable_cameras = True
APP_LAUNCHER = AppLauncher(ARGS)
SIMULATION_APP = APP_LAUNCHER.app

import gymnasium as gym
import torch
from rsl_rl.runners import OnPolicyRunner

from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper, handle_deprecated_rsl_rl_cfg

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils.hydra import load_cfg_from_registry

import se3_rl_lab.tasks  # noqa: F401
from se3_rl_lab.assets.robots.serialleg_contract import SERIALLEG_CONTRACT
from se3_rl_lab.isaac_eval.collision_preview import spawn_collision_preview
from se3_rl_lab.tools.reports import evaluation_score, write_evaluation_report
from se3_rl_lab.tools.rerun_export import export_rerun

SCENARIOS = (
    ("stand", 0.0, 0.0, 0.26),
    ("forward_slow", 0.5, 0.0, 0.26),
    ("reverse", -0.5, 0.0, 0.26),
    ("yaw_left", 0.0, 1.0, 0.26),
    ("yaw_right", 0.0, -1.0, 0.26),
    ("forward_turn", 0.5, 0.8, 0.26),
)


def _attachment(robot, body_name: str, local_position: tuple[float, float, float]):
    from isaaclab.utils.math import quat_apply

    body_index = robot.body_names.index(body_name)
    position = robot.data.body_pos_w[:, body_index]
    orientation = robot.data.body_quat_w[:, body_index]
    local = torch.tensor(local_position, dtype=position.dtype, device=position.device).expand_as(position)
    return position + quat_apply(orientation, local)


def _loop_residual(robot) -> float:
    values = []
    for loop in SERIALLEG_CONTRACT.loop_joints.values():
        point0 = _attachment(robot, loop.body0, loop.local_pos0)
        point1 = _attachment(robot, loop.body1, loop.local_pos1)
        values.append(torch.linalg.vector_norm(point0 - point1, dim=-1).max())
    return float(torch.stack(values).max().item())


def _virtual_root_drift(robot) -> float:
    ids = [robot.joint_names.index(name) for name in SERIALLEG_CONTRACT.tendon_root_joint_names]
    return float(torch.abs(robot.data.joint_pos[:, ids]).max().item())


def _set_command(env, vx: float, yaw_rate: float, height: float) -> None:
    term = env.command_manager.get_term("velocity_height")
    term._command[:, :] = 0.0
    term._command[:, 0] = vx
    term._command[:, 1] = yaw_rate
    term._command[:, 4] = height


def _update_follow_camera(sim, robot) -> None:
    """Keep a side-rear camera at a fixed offset in the robot yaw frame."""
    root_position = robot.data.root_pos_w[0]
    root_quaternion = robot.data.root_quat_w[0]
    w, x, y, z = (float(value.item()) for value in root_quaternion)
    yaw = math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))
    lateral_distance = -2.4
    eye = (
        float(root_position[0].item()) - math.sin(yaw) * lateral_distance,
        float(root_position[1].item()) + math.cos(yaw) * lateral_distance,
        float(root_position[2].item()) + 0.57,
    )
    target = (
        float(root_position[0].item()),
        float(root_position[1].item()),
        float(root_position[2].item()),
    )
    sim.set_camera_view(eye=eye, target=target)


def _scenario_summary(name: str, samples: list[dict]) -> dict:
    velocity_mse = sum((row["base_vx"] - row["command_vx"]) ** 2 for row in samples) / len(samples)
    yaw_mse = sum((row["base_yaw_rate"] - row["command_yaw_rate"]) ** 2 for row in samples) / len(samples)
    return {
        "name": name,
        "steps": len(samples),
        "velocity_rmse": math.sqrt(velocity_mse),
        "yaw_rate_rmse": math.sqrt(yaw_mse),
        "terminations": sum(int(row["terminated"]) for row in samples),
    }


def main() -> int:
    context = json.loads(ARGS.context.read_text(encoding="utf-8"))
    checkpoint = Path(context["checkpoint"]).resolve()
    run_dir = Path(context["run_dir"]).resolve()
    output_dir = run_dir / "isaac_eval"
    videos_dir = output_dir / "videos"
    metrics_dir = output_dir / "metrics"
    rerun_dir = run_dir / "rerun"
    reports_dir = run_dir / "reports"
    for path in (videos_dir, metrics_dir, rerun_dir, reports_dir):
        path.mkdir(parents=True, exist_ok=True)

    task = context["task"]
    env_cfg = load_cfg_from_registry(task, "env_cfg_entry_point")
    agent_cfg = load_cfg_from_registry(task, "rsl_rl_cfg_entry_point")
    agent_cfg = handle_deprecated_rsl_rl_cfg(agent_cfg, metadata.version("rsl-rl-lib"))
    env_cfg.scene.num_envs = 1
    env_cfg.sim.device = context["device"]
    env_cfg.sim.use_fabric = False
    env_cfg.seed = 47
    env_cfg.log_dir = str(run_dir)
    env_cfg.commands.velocity_height.debug_vis = True
    env_cfg.events.reset_base.params["pose_range"] = {
        "x": (0.0, 0.0),
        "y": (0.0, 0.0),
        "yaw": (0.0, 0.0),
    }
    env = gym.make(task, cfg=env_cfg, render_mode="rgb_array")
    unwrapped = env.unwrapped
    collision_preview = spawn_collision_preview("/World/envs/env_0/Robot")

    total_steps = sum(max(1, round(float(context["scenario_duration_s"]) / unwrapped.step_dt)) for _ in SCENARIOS)
    if context["video"]:
        env = gym.wrappers.RecordVideo(
            env,
            video_folder=str(videos_dir),
            name_prefix=checkpoint.stem,
            step_trigger=lambda step: step == 0,
            video_length=total_steps,
            disable_logger=True,
        )
    env = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)
    runner = OnPolicyRunner(env, agent_cfg.to_dict(), log_dir=None, device=agent_cfg.device)
    runner.load(str(checkpoint))
    policy = runner.get_inference_policy(device=unwrapped.device)
    obs = env.get_observations()
    robot = unwrapped.scene["robot"]
    collision_preview.update(robot)
    _update_follow_camera(unwrapped.sim, robot)
    samples: list[dict] = []
    scenarios: list[dict] = []
    global_step = 0

    with torch.inference_mode():
        for scenario_name, vx, yaw_rate, height in SCENARIOS:
            scenario_samples = []
            steps = max(1, round(float(context["scenario_duration_s"]) / unwrapped.step_dt))
            for _ in range(steps):
                _set_command(unwrapped, vx, yaw_rate, height)
                collision_preview.update(robot)
                _update_follow_camera(unwrapped.sim, robot)
                actions = policy(obs)
                obs, _, dones, _ = env.step(actions)
                command = unwrapped.command_manager.get_command("velocity_height")[0]
                finite = all(
                    bool(torch.isfinite(value).all())
                    for value in (robot.data.root_state_w, robot.data.joint_pos, robot.data.joint_vel)
                )
                row = {
                    "step": global_step,
                    "scenario": scenario_name,
                    "command_vx": float(command[0].item()),
                    "command_yaw_rate": float(command[1].item()),
                    "base_vx": float(robot.data.root_lin_vel_b[0, 0].item()),
                    "base_yaw_rate": float(robot.data.root_ang_vel_b[0, 2].item()),
                    "base_world_x": float(robot.data.root_pos_w[0, 0].item()),
                    "base_world_y": float(robot.data.root_pos_w[0, 1].item()),
                    "base_height": float(robot.data.root_pos_w[0, 2].item()),
                    "loop_residual_m": _loop_residual(robot),
                    "virtual_root_drift_rad": _virtual_root_drift(robot),
                    "terminated": bool(dones[0].item()),
                    "finite": finite,
                }
                samples.append(row)
                scenario_samples.append(row)
                global_step += 1
            scenarios.append(_scenario_summary(scenario_name, scenario_samples))

    velocity_mse = sum((row["base_vx"] - row["command_vx"]) ** 2 for row in samples) / len(samples)
    yaw_mse = sum((row["base_yaw_rate"] - row["command_yaw_rate"]) ** 2 for row in samples) / len(samples)
    metrics = {
        "schema_version": 1,
        "suite": context["suite"],
        "checkpoint_name": checkpoint.stem,
        "checkpoint_path": str(checkpoint),
        "preview_geometry": {
            "meshes": collision_preview.mesh_count,
            "cylinders": collision_preview.cylinder_count,
        },
        "summary": {
            "steps": len(samples),
            "survival_rate": 1.0 - sum(int(row["terminated"]) for row in samples) / len(samples),
            "velocity_rmse": math.sqrt(velocity_mse),
            "yaw_rate_rmse": math.sqrt(yaw_mse),
            "max_loop_residual_m": max(row["loop_residual_m"] for row in samples),
            "max_virtual_root_drift_rad": max(row["virtual_root_drift_rad"] for row in samples),
            "non_finite_samples": sum(not row["finite"] for row in samples),
        },
        "scenarios": scenarios,
    }
    metrics_path = metrics_dir / f"{checkpoint.stem}.metrics.json"
    telemetry_path = metrics_dir / f"{checkpoint.stem}.telemetry.json"
    report_path = reports_dir / f"{checkpoint.stem}.evaluation.md"
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    telemetry_path.write_text(json.dumps(samples, separators=(",", ":")) + "\n", encoding="utf-8")
    write_evaluation_report(metrics, report_path)
    rerun_path = rerun_dir / f"{checkpoint.stem}.rrd"
    if context["rerun"]:
        export_rerun(samples, rerun_path, application_id=f"serialleg-{checkpoint.stem}")
    result = {
        "checkpoint": str(checkpoint),
        "metrics_path": str(metrics_path),
        "telemetry_path": str(telemetry_path),
        "report_path": str(report_path),
        "rerun_path": str(rerun_path) if context["rerun"] else None,
        "score": evaluation_score(metrics),
    }
    (output_dir / "latest_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    env.close()
    SIMULATION_APP.close()
    print(json.dumps(result, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
