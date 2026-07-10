#!/usr/bin/env python3
"""Prove that SerialLeg's external spherical joints actively maintain loop closure."""

from __future__ import annotations

import argparse
import importlib.util
import math
import os
import sys
import traceback
from pathlib import Path
from typing import Any

from isaaclab.app import AppLauncher

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = PROJECT_ROOT / "source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg"


def _load_serialleg_contract() -> Any:
    module_path = ASSET_DIR.parent / "serialleg_contract.py"
    module_name = "_se3_rl_lab_closed_chain_smoke_contract"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load SerialLeg contract module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module.load_serialleg_contract(ASSET_DIR / "robot_config.yaml")


CONTRACT = _load_serialleg_contract()
DEFAULT_USD = ASSET_DIR / CONTRACT.runtime_usd
LOOPS = tuple(CONTRACT.loop_joints.values())


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--usd", type=Path, default=DEFAULT_USD, help="Generated SerialLeg USD")
    parser.add_argument("--steps", type=int, default=240, help="Number of externally forced physics steps")
    parser.add_argument("--force", type=float, default=5.0, help="Peak force per loaded body in newtons")
    parser.add_argument(
        "--max-closed-residual",
        type=float,
        default=2.0e-5,
        help="Maximum attachment residual allowed with loop constraints enabled",
    )
    parser.add_argument(
        "--min-open-residual",
        type=float,
        default=1.0e-3,
        help="Minimum residual required from the disabled-loop A/B control",
    )
    parser.add_argument(
        "--min-separation-ratio",
        type=float,
        default=1000.0,
        help="Minimum open/closed peak residual ratio required for every loop",
    )
    parser.add_argument(
        "--min-joint-motion",
        type=float,
        default=1.0e-3,
        help="Minimum closed-instance joint displacement proving nontrivial motion in radians",
    )
    AppLauncher.add_app_launcher_args(parser)
    parser.set_defaults(headless=True, device="cpu")
    return parser.parse_args()


ARGS = _parse_args()
APP_LAUNCHER = AppLauncher(ARGS, fast_shutdown=True)
SIMULATION_APP = APP_LAUNCHER.app

import torch  # noqa: E402

import isaaclab.sim as sim_utils  # noqa: E402
from isaaclab.actuators import ImplicitActuatorCfg  # noqa: E402
from isaaclab.assets import Articulation, ArticulationCfg  # noqa: E402
from isaaclab.sim import SimulationContext  # noqa: E402
from isaaclab.utils.math import quat_apply  # noqa: E402


def _robot_cfg(usd_path: Path, prim_path: str, y_position: float) -> ArticulationCfg:
    return ArticulationCfg(
        prim_path=prim_path,
        spawn=sim_utils.UsdFileCfg(
            usd_path=str(usd_path),
            rigid_props=sim_utils.RigidBodyPropertiesCfg(
                rigid_body_enabled=True,
                disable_gravity=True,
                max_linear_velocity=100.0,
                max_angular_velocity=100.0,
                max_depenetration_velocity=10.0,
                enable_gyroscopic_forces=True,
            ),
            articulation_props=sim_utils.ArticulationRootPropertiesCfg(
                enabled_self_collisions=False,
                solver_position_iteration_count=16,
                solver_velocity_iteration_count=4,
                sleep_threshold=0.0,
                stabilization_threshold=0.001,
            ),
        ),
        init_state=ArticulationCfg.InitialStateCfg(
            pos=(0.0, y_position, 1.0),
            joint_pos=CONTRACT.default_joint_positions,
            joint_vel={".*": 0.0},
        ),
        actuators={
            "neutral": ImplicitActuatorCfg(
                joint_names_expr=[".*"],
                effort_limit_sim=0.0,
                stiffness=0.0,
                damping=0.0,
            )
        },
    )


def _set_loop_constraints_enabled(root_path: str, enabled: bool) -> tuple[str, ...]:
    from pxr import Usd, UsdPhysics

    stage = sim_utils.get_current_stage()
    root_prim = stage.GetPrimAtPath(root_path)
    if not root_prim:
        raise RuntimeError(f"missing spawned robot root: {root_path}")
    expected_names = {loop.name for loop in LOOPS}
    found_names = set()
    for prim in Usd.PrimRange(root_prim, Usd.TraverseInstanceProxies()):
        if not prim.IsA(UsdPhysics.SphericalJoint) or prim.GetName() not in expected_names:
            continue
        if prim.IsInstanceProxy():
            raise RuntimeError(f"cannot author loop enabled state on instance proxy: {prim.GetPath()}")
        UsdPhysics.Joint(prim).CreateJointEnabledAttr(enabled)
        found_names.add(prim.GetName())
    if found_names != expected_names:
        raise RuntimeError(f"unexpected loop joint set below {root_path}: {sorted(found_names)}")
    return tuple(sorted(found_names))


def _attachment_position(robot: Articulation, body_name: str, local_position: tuple[float, float, float]):
    body_index = robot.body_names.index(body_name)
    position = robot.data.body_pos_w[:, body_index]
    orientation = robot.data.body_quat_w[:, body_index]
    local = torch.tensor(local_position, dtype=position.dtype, device=position.device).expand_as(position)
    return position + quat_apply(orientation, local)


def _loop_residuals(robot: Articulation) -> dict[str, float]:
    result = {}
    for loop in LOOPS:
        point0 = _attachment_position(robot, loop.body0, loop.local_pos0)
        point1 = _attachment_position(robot, loop.body1, loop.local_pos1)
        result[loop.name] = float(torch.linalg.vector_norm(point0 - point1, dim=-1).max().item())
    return result


def _loaded_body_ids(robot: Articulation) -> list[int]:
    body_names = []
    for loop in LOOPS:
        body_names.extend((loop.body0, loop.body1))
    if len(set(body_names)) != 4:
        raise RuntimeError(f"closed-chain smoke expects four unique loaded bodies, got {body_names}")
    return [robot.body_names.index(name) for name in body_names]


def _external_wrenches(step: int, body_count: int, device: str) -> tuple[torch.Tensor, torch.Tensor]:
    if body_count != 4:
        raise RuntimeError(f"expected four loaded bodies, got {body_count}")
    phase = math.sin(2.0 * math.pi * 3.0 * step / ARGS.steps)
    force = ARGS.force * phase
    forces = torch.zeros(1, body_count, 3, device=device)
    torques = torch.zeros_like(forces)
    forces[0, 0, 0] = force
    forces[0, 1, 0] = -force
    forces[0, 2, 2] = force
    forces[0, 3, 2] = -force
    torques[0, 0, 1] = 0.05 * force
    torques[0, 1, 1] = -0.05 * force
    torques[0, 2, 1] = -0.05 * force
    torques[0, 3, 1] = 0.05 * force
    return forces, torques


def _validate_args() -> None:
    positive_values = {
        "--steps": ARGS.steps,
        "--force": ARGS.force,
        "--max-closed-residual": ARGS.max_closed_residual,
        "--min-open-residual": ARGS.min_open_residual,
        "--min-separation-ratio": ARGS.min_separation_ratio,
        "--min-joint-motion": ARGS.min_joint_motion,
    }
    invalid = {name: value for name, value in positive_values.items() if value <= 0.0}
    if invalid:
        raise ValueError(f"closed-chain smoke arguments must be positive: {invalid}")


def main() -> int:
    _validate_args()
    usd_path = ARGS.usd.resolve()
    if not usd_path.is_file():
        raise FileNotFoundError(f"generated SerialLeg USD not found: {usd_path}")

    simulation = SimulationContext(sim_utils.SimulationCfg(dt=0.005, device=ARGS.device))
    closed = Articulation(_robot_cfg(usd_path, "/World/Closed", -0.75))
    open_control = Articulation(_robot_cfg(usd_path, "/World/OpenControl", 0.75))
    closed_loops = _set_loop_constraints_enabled("/World/Closed", True)
    open_loops = _set_loop_constraints_enabled("/World/OpenControl", False)
    if open_loops != closed_loops:
        raise RuntimeError(f"closed/open A/B loop sets differ: closed={closed_loops}, open={open_loops}")
    simulation.reset()

    for robot in (closed, open_control):
        if robot.num_instances != 1 or robot.num_bodies != 11 or robot.num_joints != 10:
            raise RuntimeError(
                f"unexpected articulation dimensions: instances={robot.num_instances}, "
                f"bodies={robot.num_bodies}, joints={robot.num_joints}"
            )

    closed_body_ids = _loaded_body_ids(closed)
    open_body_ids = _loaded_body_ids(open_control)
    initial_closed_joint_pos = closed.data.joint_pos.clone()
    peak_closed = _loop_residuals(closed)
    peak_open = _loop_residuals(open_control)
    max_joint_motion = 0.0
    physics_dt = simulation.get_physics_dt()

    for step in range(ARGS.steps):
        forces, torques = _external_wrenches(step, len(closed_body_ids), closed.device)
        closed.permanent_wrench_composer.set_forces_and_torques(
            forces=forces, torques=torques, body_ids=closed_body_ids, is_global=True
        )
        open_control.permanent_wrench_composer.set_forces_and_torques(
            forces=forces, torques=torques, body_ids=open_body_ids, is_global=True
        )
        closed.write_data_to_sim()
        open_control.write_data_to_sim()
        simulation.step(render=False)
        closed.update(physics_dt)
        open_control.update(physics_dt)

        for robot in (closed, open_control):
            state_tensors = (
                robot.data.root_state_w,
                robot.data.body_state_w,
                robot.data.joint_pos,
                robot.data.joint_vel,
            )
            if not all(torch.isfinite(tensor).all() for tensor in state_tensors):
                raise RuntimeError("non-finite articulation state during closed-chain A/B smoke")
        for name, residual in _loop_residuals(closed).items():
            peak_closed[name] = max(peak_closed[name], residual)
        for name, residual in _loop_residuals(open_control).items():
            peak_open[name] = max(peak_open[name], residual)
        max_joint_motion = max(
            max_joint_motion,
            float(torch.max(torch.abs(closed.data.joint_pos - initial_closed_joint_pos)).item()),
        )

    failures = []
    ratios = {}
    for loop in LOOPS:
        closed_residual = peak_closed[loop.name]
        open_residual = peak_open[loop.name]
        ratio = open_residual / max(closed_residual, torch.finfo(torch.float32).eps)
        ratios[loop.name] = ratio
        if closed_residual > ARGS.max_closed_residual:
            failures.append(f"{loop.name} closed residual {closed_residual:.3e}m > {ARGS.max_closed_residual:.3e}m")
        if open_residual < ARGS.min_open_residual:
            failures.append(f"{loop.name} open residual {open_residual:.3e}m < {ARGS.min_open_residual:.3e}m")
        if ratio < ARGS.min_separation_ratio:
            failures.append(f"{loop.name} open/closed ratio {ratio:.1f} < {ARGS.min_separation_ratio:.1f}")
    if max_joint_motion < ARGS.min_joint_motion:
        failures.append(f"closed joint motion {max_joint_motion:.3e}rad < {ARGS.min_joint_motion:.3e}rad")
    if failures:
        raise RuntimeError("closed-chain effect gate failed: " + "; ".join(failures))

    print(f"[serialleg-closed-chain-smoke] usd={usd_path}", flush=True)
    print(
        f"[serialleg-closed-chain-smoke] device={ARGS.device} steps={ARGS.steps} force={ARGS.force:.3f}N "
        f"loop_names={closed_loops} closed_enabled=true open_control_enabled=false "
        f"max_joint_motion={max_joint_motion:.3e}rad",
        flush=True,
    )
    for loop in LOOPS:
        print(
            f"[serialleg-closed-chain-smoke] loop={loop.name} closed_peak={peak_closed[loop.name]:.3e}m "
            f"open_peak={peak_open[loop.name]:.3e}m ratio={ratios[loop.name]:.1f}x",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except BaseException:
        traceback.print_exc()
        exit_code = 1
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exit_code)
