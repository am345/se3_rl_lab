"""Build and attach the SerialLeg WebSim deployment contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import onnx

METADATA_KEY = "se3_rl_lab.websim.deployment.v1"
SCHEMA_NAME = "se3_rl_lab.websim.deployment"
SCHEMA_VERSION = 1


def _asset_fingerprint(asset_dir: Path, relative_paths: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for relative_path in relative_paths:
        path = asset_dir / relative_path
        digest.update(relative_path.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _websim_asset_files(asset_dir: Path) -> tuple[str, ...]:
    manifest = json.loads((asset_dir / "websim_manifest.json").read_text(encoding="utf-8"))
    files = tuple(str(path) for path in manifest["files"])
    if not files or files[0] != "scene.xml" or len(files) != len(set(files)):
        raise ValueError("invalid WebSim asset manifest")
    return ("websim_manifest.json", *files)


def _term(
    name: str,
    dim: int,
    *,
    history_length: int = 1,
    scale: float | tuple[float, ...] = 1.0,
) -> dict[str, Any]:
    return {
        "name": name,
        "dim": dim,
        "history_length": history_length,
        "scale": list(scale) if isinstance(scale, tuple) else scale,
        "clip": 100.0,
    }


def build_serialleg_descriptor(
    *,
    task_name: str,
    sim_dt: float,
    policy_dt: float,
) -> dict[str, Any]:
    """Return the deployment descriptor derived from runtime project contracts."""
    from se3_rl_lab.assets.robots.serialleg_contract import SERIALLEG_CONTRACT
    from se3_rl_lab.assets.robots.serialleg_motors import DM8009P, M3508_C620_14
    from se3_rl_lab.serialleg_policy_contract import (
        COMMAND_SCALE,
        RECOVERY_OBSERVATION_HISTORY_LENGTH,
    )

    if sim_dt <= 0.0 or policy_dt <= 0.0:
        raise ValueError("sim_dt and policy_dt must be positive")
    decimation = round(policy_dt / sim_dt)
    if decimation <= 0 or abs(sim_dt * decimation - policy_dt) > 1e-9:
        raise ValueError(
            f"policy timing is not an integer decimation: sim_dt={sim_dt}, policy_dt={policy_dt}"
        )
    if "Recovery" not in task_name:
        raise ValueError(f"WebSim deployment currently supports Recovery policies only: {task_name}")

    contract = SERIALLEG_CONTRACT
    asset_dir = Path(__file__).parents[1] / "assets" / "robots" / "serialleg"
    asset_files = _websim_asset_files(asset_dir)
    asset_fingerprint = _asset_fingerprint(asset_dir, asset_files)
    leg_group = contract.actuator_groups["legs"]
    wheel_group = contract.actuator_groups["wheels"]
    default_joint_pos = contract.default_joint_positions
    history = RECOVERY_OBSERVATION_HISTORY_LENGTH
    active_lower = max(tendon.lower for tendon in contract.fixed_tendons.values())
    active_upper = min(tendon.upper for tendon in contract.fixed_tendons.values())

    return {
        "meta": {
            "schema_name": SCHEMA_NAME,
            "schema_version": SCHEMA_VERSION,
            "assets": {
                "asset_name": "serialleg",
                "fingerprint_sha256": asset_fingerprint,
                "scene_file": "scene.xml",
                "manifest_file": "websim_manifest.json",
            },
            "sim": {
                "sim_dt": float(sim_dt),
                "policy_dt": float(policy_dt),
                "decimation": decimation,
                "inference_hz": 1.0 / policy_dt,
            },
            "task": {"name": task_name, "family": "recovery"},
        },
        "robot": {
            "name": contract.robot_name,
            "root_link": contract.root_link,
            "policy_joint_names": list(contract.policy_joint_order),
            "passive_joint_names": list(contract.passive_joint_names),
            "tendon_root_joint_names": list(contract.tendon_root_joint_names),
            "standing_pose": {
                "root_position": list(contract.root_position),
                "root_quaternion_wxyz": list(contract.root_rotation_wxyz),
                "joint_position": {
                    name: default_joint_pos[name] for name in contract.tree_joints
                },
            },
        },
        "commands": {
            "velocity_height": {
                "fields": [
                    "linear_velocity_x",
                    "yaw_rate",
                    "pitch",
                    "roll",
                    "base_height",
                    "jump_flag",
                    "jump_height",
                    "jump_phase",
                ],
                "ranges": [
                    [-2.4, 2.4],
                    [-12.0, 12.0],
                    [0.0, 0.0],
                    [0.0, 0.0],
                    [0.20, 0.32],
                    [0.0, 0.0],
                    [0.0, 0.0],
                    [0.0, 0.0],
                ],
            }
        },
        "policy_io": {
            "inputs": [{"name": "obs", "groups": ["command", "proprio"], "dim": 138}],
            "outputs": [{"name": "actions", "dim": 6}],
            "groups": {
                "command": {
                    "dim": 8,
                    "terms": [
                        _term("commands", 5, scale=tuple(COMMAND_SCALE)),
                        _term("jump_commands", 3),
                    ],
                },
                "proprio": {
                    "dim": 130,
                    "history_order": "term_major_oldest_to_newest",
                    "terms": [
                        _term("base_ang_vel", 3, history_length=history, scale=0.25),
                        _term("projected_gravity", 3, history_length=history),
                        _term("leg_joint_pos", 6, history_length=history),
                        _term("leg_joint_vel", 4, history_length=history, scale=0.25),
                        _term("wheel_pos_zero", 2, history_length=history, scale=0.0),
                        _term("wheel_vel", 2, history_length=history, scale=0.05),
                        _term("last_actions", 6, history_length=history),
                    ],
                },
            },
            "actions": [
                {
                    "name": "legs",
                    "control_type": "joint_position",
                    "joint_names": list(leg_group.joint_names),
                    "action_indices": [0, 1, 2, 3],
                    "scale": leg_group.action_scale,
                    "clip": 100.0,
                    "target_model": "height_conditioned_active_rod",
                    "active_rod_range": [active_lower, active_upper],
                    "active_rod_lower_target_overdrive": 0.20,
                    "stiffness": leg_group.stiffness,
                    "damping": leg_group.damping,
                    "motor": {
                        "name": DM8009P.name,
                        "rated_torque": DM8009P.rated_torque,
                        "stall_torque": DM8009P.stall_torque,
                        "no_load_speed": DM8009P.no_load_speed,
                    },
                },
                {
                    "name": "wheels",
                    "control_type": "joint_velocity",
                    "joint_names": list(wheel_group.joint_names),
                    "action_indices": [4, 5],
                    "scale": wheel_group.action_scale,
                    "clip": 100.0,
                    "stiffness": wheel_group.stiffness,
                    "damping": wheel_group.damping,
                    "motor": {
                        "name": M3508_C620_14.name,
                        "rated_torque": M3508_C620_14.rated_torque,
                        "stall_torque": M3508_C620_14.stall_torque,
                        "no_load_speed": M3508_C620_14.no_load_speed,
                        "torque_speed_curve": [list(point) for point in M3508_C620_14.torque_speed_curve],
                    },
                },
            ],
            "action_delay": {
                "enabled": True,
                "nominal_s": 0.005,
                "randomized_range_s": [0.004, 0.006],
                "runtime_steps": 1,
            },
        },
    }


def attach_serialleg_websim_metadata(
    onnx_path: str | Path,
    *,
    task_name: str,
    sim_dt: float,
    policy_dt: float,
) -> dict[str, Any]:
    """Attach a canonical JSON descriptor to an exported ONNX model."""
    path = Path(onnx_path)
    descriptor = build_serialleg_descriptor(
        task_name=task_name,
        sim_dt=sim_dt,
        policy_dt=policy_dt,
    )
    model = onnx.load(path, load_external_data=False)
    preserved_metadata = [
        (entry.key, entry.value) for entry in model.metadata_props if entry.key != METADATA_KEY
    ]
    del model.metadata_props[:]
    for key, value in preserved_metadata:
        preserved = model.metadata_props.add()
        preserved.key = key
        preserved.value = value
    metadata = model.metadata_props.add()
    metadata.key = METADATA_KEY
    metadata.value = json.dumps(descriptor, sort_keys=True, separators=(",", ":"))
    onnx.save(model, path)
    return descriptor
