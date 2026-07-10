#!/usr/bin/env python3
"""Run bounded free-space or ground-contact smoke tests for the SerialLeg USD."""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path

from isaaclab.app import AppLauncher

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_USD = (
    PROJECT_ROOT
    / "source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg/usd"
    / "serialleg_closed_chain_complex_collision.usd"
)

EXPECTED_JOINTS = {
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
}
DEFAULT_JOINT_POSITIONS = {
    "lf0_Joint": -0.275422946189,
    "lf1_Joint": -1.242259649307,
    "l_wheel_Joint": 0.0,
    "l_drive_bar_Joint": -1.592100148957,
    "l_coupler_Joint": 1.40126634,
    "rf0_Joint": 0.275422946189,
    "rf1_Joint": 1.242259649307,
    "r_wheel_Joint": 0.0,
    "r_drive_bar_Joint": 1.592100148957,
    "r_coupler_Joint": -1.40126941,
}
LOOPS = (
    (
        "l_coupler_to_lf_calf",
        "l_coupler_Link",
        (-0.16999653, 0.0146, 0.00108627),
        "lf1_Link",
        (0.05003347, 0.0, 0.04149627),
    ),
    (
        "r_coupler_to_rf_calf",
        "r_coupler_Link",
        (-0.16999653, -0.0131, 0.00108627),
        "rf1_Link",
        (0.05003347, 0.0, 0.04149627),
    ),
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--usd", type=Path, default=DEFAULT_USD, help="Generated SerialLeg USD")
    parser.add_argument(
        "--steps",
        type=int,
        default=None,
        help="Number of physics steps (default: free-space=64, ground-contact=400)",
    )
    parser.add_argument(
        "--ground-contact",
        action="store_true",
        help="Spawn a ground plane and require reported contact forces on both wheel cylinders and a mesh-backed link",
    )
    parser.add_argument(
        "--root-height",
        type=float,
        default=0.24,
        help="Initial base height for --ground-contact in meters",
    )
    parser.add_argument(
        "--min-contact-force",
        type=float,
        default=1.0,
        help="Minimum peak force required for each wheel and one mesh-backed link in newtons",
    )
    parser.add_argument(
        "--max-loop-residual",
        type=float,
        default=None,
        help="Maximum attachment-point separation in meters (default: free-space=1e-5, ground-contact=2e-4)",
    )
    AppLauncher.add_app_launcher_args(parser)
    parser.set_defaults(headless=True, device="cpu")
    return parser.parse_args()


ARGS = _parse_args()
APP_LAUNCHER = AppLauncher(ARGS, fast_shutdown=True)
SIMULATION_APP = APP_LAUNCHER.app

import torch  # noqa: E402

import carb  # noqa: E402
import omni.physx.bindings._physx as physx_bindings  # noqa: E402

import isaaclab.sim as sim_utils  # noqa: E402
from isaaclab.actuators import ImplicitActuatorCfg  # noqa: E402
from isaaclab.assets import Articulation, ArticulationCfg  # noqa: E402
from isaaclab.sensors import ContactSensor, ContactSensorCfg  # noqa: E402
from isaaclab.sim import SimulationContext  # noqa: E402
from isaaclab.utils.math import quat_apply  # noqa: E402


def _attachment_position(robot: Articulation, body_name: str, local_position: tuple[float, float, float]):
    body_index = robot.body_names.index(body_name)
    position = robot.data.body_pos_w[:, body_index]
    orientation = robot.data.body_quat_w[:, body_index]
    local = torch.tensor(local_position, dtype=position.dtype, device=position.device).expand_as(position)
    return position + quat_apply(orientation, local)


def _max_loop_residual(robot: Articulation) -> float:
    residual = 0.0
    for _name, body0, local0, body1, local1 in LOOPS:
        point0 = _attachment_position(robot, body0, local0)
        point1 = _attachment_position(robot, body1, local1)
        residual = max(residual, float(torch.linalg.vector_norm(point0 - point1, dim=-1).max().item()))
    return residual


def _collision_shape_types(body_names: list[str]) -> dict[str, tuple[str, ...]]:
    """Return direct collider geometry types below every articulation body."""
    from pxr import Usd, UsdGeom, UsdPhysics

    stage = sim_utils.get_current_stage()
    result = {}
    for body_name in body_names:
        body_prim = stage.GetPrimAtPath(f"/World/Robot/{body_name}")
        if not body_prim:
            raise RuntimeError(f"missing spawned body prim: /World/Robot/{body_name}")
        shape_types = []
        for prim in Usd.PrimRange(body_prim, Usd.TraverseInstanceProxies()):
            if not prim.HasAPI(UsdPhysics.CollisionAPI):
                continue
            if prim.IsA(UsdGeom.Mesh):
                shape_types.append("Mesh")
            elif prim.IsA(UsdGeom.Cylinder):
                shape_types.append("Cylinder")
            elif prim.IsA(UsdGeom.Gprim):
                shape_types.append(prim.GetTypeName())
        if not shape_types:
            raise RuntimeError(f"body {body_name} has no direct collider geometry")
        result[body_name] = tuple(shape_types)
    return result


def _resolve_runtime_limits() -> tuple[int, float]:
    """Resolve mode-specific defaults and reject invalid CLI thresholds."""
    steps = ARGS.steps
    if steps is None:
        steps = 400 if ARGS.ground_contact else 64
    max_loop_residual = ARGS.max_loop_residual
    if max_loop_residual is None:
        max_loop_residual = 2.0e-4 if ARGS.ground_contact else 1.0e-5
    if steps <= 0:
        raise ValueError("--steps must be positive")
    if max_loop_residual <= 0.0:
        raise ValueError("--max-loop-residual must be positive")
    if ARGS.root_height <= 0.0:
        raise ValueError("--root-height must be positive")
    if ARGS.min_contact_force <= 0.0:
        raise ValueError("--min-contact-force must be positive")
    return steps, max_loop_residual


def main() -> int:
    usd_path = ARGS.usd.resolve()
    if not usd_path.is_file():
        raise FileNotFoundError(f"generated SerialLeg USD not found: {usd_path}")
    steps, max_loop_residual_limit = _resolve_runtime_limits()

    simulation = SimulationContext(sim_utils.SimulationCfg(dt=0.005, device=ARGS.device))
    approximate_cylinders = bool(
        carb.settings.get_settings().get(physx_bindings.SETTING_COLLISION_APPROXIMATE_CYLINDERS)
    )
    if ARGS.ground_contact:
        if approximate_cylinders:
            raise RuntimeError(
                "ground-contact smoke requires /physics/collisionApproximateCylinders=False "
                "to exercise custom Cylinder contact geometry"
            )
        ground_cfg = sim_utils.GroundPlaneCfg()
        ground_cfg.func("/World/GroundPlane", ground_cfg)
    robot_cfg = ArticulationCfg(
        prim_path="/World/Robot",
        spawn=sim_utils.UsdFileCfg(
            usd_path=str(usd_path),
            activate_contact_sensors=ARGS.ground_contact,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(
                rigid_body_enabled=True,
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
            pos=(0.0, 0.0, ARGS.root_height if ARGS.ground_contact else 1.0),
            joint_pos=DEFAULT_JOINT_POSITIONS,
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
    robot = Articulation(robot_cfg)
    contact_sensor = None
    if ARGS.ground_contact:
        contact_sensor = ContactSensor(
            ContactSensorCfg(
                prim_path="/World/Robot/.*",
                update_period=0.0,
                history_length=0,
                debug_vis=False,
            )
        )
    simulation.reset()

    if robot.num_instances != 1:
        raise RuntimeError(f"expected one articulation instance, got {robot.num_instances}")
    if robot.num_bodies != 11:
        raise RuntimeError(f"expected 11 rigid bodies, got {robot.num_bodies}")
    if robot.num_joints != 10 or set(robot.joint_names) != EXPECTED_JOINTS:
        raise RuntimeError(f"unexpected articulation joints ({robot.num_joints}): {robot.joint_names}")

    shape_types = _collision_shape_types(robot.body_names)
    wheel_names = ("l_wheel_Link", "r_wheel_Link")
    mesh_body_names = tuple(name for name, types in shape_types.items() if "Mesh" in types)
    if ARGS.ground_contact:
        for wheel_name in wheel_names:
            if shape_types.get(wheel_name) != ("Cylinder",):
                raise RuntimeError(
                    f"wheel {wheel_name} must have exactly one direct Cylinder collider, "
                    f"got {shape_types.get(wheel_name)}"
                )
        if not mesh_body_names:
            raise RuntimeError("ground-contact smoke found no mesh-backed articulation bodies")
        if contact_sensor is None:
            raise RuntimeError("ground-contact smoke failed to create its contact sensor")
        if set(contact_sensor.body_names) != set(robot.body_names):
            raise RuntimeError(
                f"contact sensor body set differs from articulation: sensor={contact_sensor.body_names}, "
                f"articulation={robot.body_names}"
            )

    max_residual = _max_loop_residual(robot)
    peak_contact_forces = {name: 0.0 for name in robot.body_names}
    physics_dt = simulation.get_physics_dt()
    for _ in range(steps):
        robot.write_data_to_sim()
        simulation.step(render=False)
        robot.update(physics_dt)
        if contact_sensor is not None:
            contact_sensor.update(physics_dt, force_recompute=True)
            forces = contact_sensor.data.net_forces_w
            if forces is None or forces.shape != (1, robot.num_bodies, 3):
                shape = None if forces is None else tuple(forces.shape)
                raise RuntimeError(f"unexpected contact force tensor shape: {shape}")
            if not torch.isfinite(forces).all():
                raise RuntimeError("non-finite contact force during ground-contact smoke")
            force_norms = torch.linalg.vector_norm(forces[0], dim=-1)
            for body_index, body_name in enumerate(contact_sensor.body_names):
                peak_contact_forces[body_name] = max(
                    peak_contact_forces[body_name], float(force_norms[body_index].item())
                )
        state_tensors = (
            robot.data.root_state_w,
            robot.data.body_state_w,
            robot.data.joint_pos,
            robot.data.joint_vel,
        )
        if not all(torch.isfinite(tensor).all() for tensor in state_tensors):
            raise RuntimeError("non-finite articulation state during smoke test")
        max_residual = max(max_residual, _max_loop_residual(robot))

    if max_residual > max_loop_residual_limit:
        raise RuntimeError(f"loop residual {max_residual:.3e}m exceeds threshold {max_loop_residual_limit:.3e}m")

    if ARGS.ground_contact:
        weak_wheels = {
            name: peak_contact_forces[name]
            for name in wheel_names
            if peak_contact_forces[name] < ARGS.min_contact_force
        }
        if weak_wheels:
            raise RuntimeError(f"wheel ground-contact peaks are below {ARGS.min_contact_force:.3f}N: {weak_wheels}")
        strongest_mesh_body = max(mesh_body_names, key=peak_contact_forces.__getitem__)
        strongest_mesh_force = peak_contact_forces[strongest_mesh_body]
        if strongest_mesh_force < ARGS.min_contact_force:
            raise RuntimeError(
                f"no mesh-backed body reached {ARGS.min_contact_force:.3f}N; "
                f"strongest={strongest_mesh_body}:{strongest_mesh_force:.3f}N"
            )

    print(f"[serialleg-usd-smoke] usd={usd_path}", flush=True)
    print(
        f"[serialleg-usd-smoke] bodies={robot.num_bodies} dofs={robot.num_joints} "
        f"device={ARGS.device} steps={steps} max_loop_residual={max_residual:.3e}m "
        f"threshold={max_loop_residual_limit:.3e}m",
        flush=True,
    )
    if ARGS.ground_contact:
        active_contacts = {
            name: f"{force:.3f}" for name, force in peak_contact_forces.items() if force >= ARGS.min_contact_force
        }
        print(
            f"[serialleg-usd-smoke] ground_contact=true root_height={ARGS.root_height:.3f}m "
            f"contact_tensor_device={contact_sensor.data.net_forces_w.device} "
            f"cylinder_mode=custom min_force={ARGS.min_contact_force:.3f}N wheel_peaks="
            f"{{'{wheel_names[0]}': {peak_contact_forces[wheel_names[0]]:.3f}, "
            f"'{wheel_names[1]}': {peak_contact_forces[wheel_names[1]]:.3f}}}N",
            flush=True,
        )
        print(f"[serialleg-usd-smoke] active_contact_peaks={active_contacts}N", flush=True)
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except BaseException:  # keep the smoke command bounded even when Kit teardown is unhealthy
        traceback.print_exc()
        exit_code = 1
    # This is a bounded process-level smoke test.  Direct exit avoids Kit's
    # extension teardown stalling when the host has exhausted inotify watches.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exit_code)
