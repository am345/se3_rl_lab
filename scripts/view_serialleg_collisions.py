#!/usr/bin/env python3
"""Open SerialLeg as a lit solid collision-geometry preview or a PhysX debug view."""

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
    """Load the pure-Python contract without importing the extension package."""
    module_path = ASSET_DIR.parent / "serialleg_contract.py"
    module_name = "_se3_rl_lab_collision_view_contract"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load SerialLeg contract module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module.load_serialleg_contract(ASSET_DIR / "robot_config.yaml")


CONTRACT = _load_serialleg_contract()
DEFAULT_USD = ASSET_DIR / CONTRACT.runtime_usd
DEFAULT_JOINT_POSITIONS = CONTRACT.default_joint_positions
LEG_JOINTS = CONTRACT.actuator_groups["legs"].joint_names
WHEEL_JOINTS = CONTRACT.actuator_groups["wheels"].joint_names
PASSIVE_JOINTS = CONTRACT.passive_joint_names
FIXED_TENDONS = tuple(CONTRACT.fixed_tendons.values())
TENDON_BY_JOINT = {joint_name: tendon for tendon in FIXED_TENDONS for joint_name in tendon.joint_names}
LEG_CONTROL_HALF_RANGE = math.pi


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--usd", type=Path, default=DEFAULT_USD, help="SerialLeg collision-only USD")
    parser.add_argument(
        "--frames",
        type=int,
        default=0,
        help="Exit after this many rendered frames; 0 keeps the GUI open until the window closes",
    )
    parser.add_argument("--root-height", type=float, default=0.22, help="Standing base height in meters")
    parser.add_argument(
        "--view-mode",
        choices=("render", "collision", "both"),
        default="render",
        help="render=lit solid geometry, collision=PhysX overlays, both=solid geometry with overlays",
    )
    parser.add_argument("--show-joints", action="store_true", help="Also enable the physics joint overlay")
    parser.add_argument(
        "--floating-base",
        action="store_true",
        help="Leave the base floating; the default fixes it in the viewer for easier joint inspection",
    )
    parser.add_argument(
        "--demo-motion",
        action="store_true",
        help="Automatically sweep active joints; useful for bounded headless and hands-free visual checks",
    )
    parser.add_argument(
        "--max-loop-residual",
        type=float,
        default=2.0e-4,
        help="Residual threshold shown by the closed-chain status panel in meters",
    )
    parser.add_argument(
        "--min-demo-motion",
        type=float,
        default=1.0e-2,
        help="Minimum active and passive joint motion required by a bounded --demo-motion gate in radians",
    )
    AppLauncher.add_app_launcher_args(parser)
    parser.set_defaults(headless=False, device="cpu")
    return parser.parse_args()


ARGS = _parse_args()
APP_LAUNCHER = AppLauncher(ARGS)
SIMULATION_APP = APP_LAUNCHER.app

import torch  # noqa: E402

import carb  # noqa: E402
import omni.physx.bindings._physx as physx_bindings  # noqa: E402

if ARGS.headless:
    ui = None
else:
    import omni.ui as ui  # noqa: E402

import isaaclab.sim as sim_utils  # noqa: E402
from isaaclab.actuators import ImplicitActuatorCfg  # noqa: E402
from isaaclab.assets import Articulation, ArticulationCfg  # noqa: E402
from isaaclab.sim import SimulationContext  # noqa: E402
from isaaclab.utils.math import quat_apply  # noqa: E402


def _actuator_cfg(group_name: str, *, stiffness: float | None = None, damping: float | None = None):
    group = CONTRACT.actuator_groups[group_name]
    kwargs = {
        "joint_names_expr": list(group.joint_names),
        "effort_limit_sim": group.effort_limit_sim,
        "stiffness": group.stiffness if stiffness is None else stiffness,
        "damping": group.damping if damping is None else damping,
    }
    if group.velocity_limit_sim is not None:
        kwargs["velocity_limit_sim"] = group.velocity_limit_sim
    return ImplicitActuatorCfg(**kwargs)


def _attachment_position(robot: Articulation, body_name: str, local_position: tuple[float, float, float]):
    body_index = robot.body_names.index(body_name)
    position = robot.data.body_pos_w[:, body_index]
    orientation = robot.data.body_quat_w[:, body_index]
    local = torch.tensor(local_position, dtype=position.dtype, device=position.device).expand_as(position)
    return position + quat_apply(orientation, local)


def _loop_residuals(robot: Articulation) -> dict[str, float]:
    residuals = {}
    for loop in CONTRACT.loop_joints.values():
        point0 = _attachment_position(robot, loop.body0, loop.local_pos0)
        point1 = _attachment_position(robot, loop.body1, loop.local_pos1)
        residuals[loop.name] = float(torch.linalg.vector_norm(point0 - point1, dim=-1).max().item())
    return residuals


def _tendon_coordinate(tendon: Any, joint_positions: dict[str, float]) -> float:
    return sum(
        coefficient * joint_positions[joint_name]
        for joint_name, coefficient in zip(tendon.joint_names, tendon.coefficients, strict=True)
    )


def _project_changed_leg_target(joint_positions: dict[str, float], changed_joint: str) -> float:
    """Clamp one changed rod target so its side's coupled tendon coordinate stays legal."""
    tendon = TENDON_BY_JOINT[changed_joint]
    coordinate = _tendon_coordinate(tendon, joint_positions)
    bounded_coordinate = min(max(coordinate, tendon.lower), tendon.upper)
    coefficient = tendon.coefficients[tendon.joint_names.index(changed_joint)]
    joint_positions[changed_joint] += (bounded_coordinate - coordinate) / coefficient
    return joint_positions[changed_joint]


def _project_leg_targets(joint_positions: dict[str, float]) -> dict[str, float]:
    """Return coupled-limit-safe targets, adjusting the second axis of each tendon if needed."""
    projected = dict(joint_positions)
    for tendon in FIXED_TENDONS:
        _project_changed_leg_target(projected, tendon.joint_names[-1])
        coordinate = _tendon_coordinate(tendon, projected)
        if coordinate < tendon.lower - 1.0e-9 or coordinate > tendon.upper + 1.0e-9:
            raise RuntimeError(f"failed to project {tendon.name} target into its coupled range")
    return projected


class JointControlPanel:
    """Own the viewer-only active-joint commands and optional omni.ui controls."""

    def __init__(self, robot: Articulation):
        self._robot = robot
        self._leg_targets = {name: DEFAULT_JOINT_POSITIONS[name] for name in LEG_JOINTS}
        self._wheel_velocities = {name: 0.0 for name in WHEEL_JOINTS}
        self._models: dict[str, Any] = {}
        self._value_labels: dict[str, Any] = {}
        self._residual_labels: dict[str, Any] = {}
        self._tendon_labels: dict[str, Any] = {}
        self._passive_label = None
        self._status_label = None
        self._reset_requested = False
        self._updating_model = False
        self._window = None
        if not ARGS.headless:
            self._build_window()

    def _build_window(self) -> None:
        if ui is None:
            raise RuntimeError("omni.ui is unavailable in headless mode")
        self._window = ui.Window("SerialLeg Collision + Closed Chain", width=560, height=570)
        with self._window.frame:
            with ui.VStack(spacing=6):
                ui.Label("Active rod targets (rad; each slider spans one full turn)", height=22)
                for joint_name in LEG_JOINTS:
                    standing = DEFAULT_JOINT_POSITIONS[joint_name]
                    self._add_control_row(
                        joint_name,
                        initial=standing,
                        minimum=standing - LEG_CONTROL_HALF_RANGE,
                        maximum=standing + LEG_CONTROL_HALF_RANGE,
                        step=0.01,
                        unit="rad",
                    )
                ui.Label("Coupled rod-angle limits", height=22)
                for tendon in FIXED_TENDONS:
                    self._tendon_labels[tendon.name] = ui.Label(f"{tendon.name}: waiting", height=20)
                ui.Spacer(height=6)
                ui.Label("Wheel velocity targets (rad/s)", height=22)
                for joint_name in WHEEL_JOINTS:
                    self._add_control_row(joint_name, minimum=-10.0, maximum=10.0, step=0.1, unit="rad/s")
                ui.Spacer(height=6)
                with ui.HStack(height=30):
                    ui.Button("Reset standing pose", clicked_fn=self._request_reset)
                    ui.Button("Standing + zero wheels", clicked_fn=self._zero_models)
                ui.Spacer(height=6)
                ui.Label("Closed-chain attachment residuals", height=22)
                for loop in CONTRACT.loop_joints.values():
                    self._residual_labels[loop.name] = ui.Label(f"{loop.name}: waiting", height=20)
                self._status_label = ui.Label("status: waiting", height=22)
                self._passive_label = ui.Label("passive joints: waiting", word_wrap=True, height=44)

    def _add_control_row(
        self,
        joint_name: str,
        *,
        initial: float = 0.0,
        minimum: float,
        maximum: float,
        step: float,
        unit: str,
    ) -> None:
        model = ui.SimpleFloatModel(initial)
        self._models[joint_name] = model
        with ui.HStack(height=26):
            ui.Label(joint_name, width=170)
            ui.FloatSlider(model=model, min=minimum, max=maximum, step=step)
            value_label = ui.Label(f"{initial:+.3f} {unit}", width=105)
        self._value_labels[joint_name] = value_label

        def _on_changed(changed_model, name=joint_name, value_widget=value_label, suffix=unit):
            if self._updating_model:
                return
            value = changed_model.get_value_as_float()
            if name in self._leg_targets:
                self._leg_targets[name] = value
                projected = _project_changed_leg_target(self._leg_targets, name)
                if not math.isclose(projected, value, abs_tol=1.0e-7):
                    self._updating_model = True
                    changed_model.set_value(projected)
                    self._updating_model = False
                    value = projected
            else:
                self._wheel_velocities[name] = value
            value_widget.text = f"{value:+.3f} {suffix}"

        model.add_value_changed_fn(_on_changed)

    def _request_reset(self) -> None:
        self._reset_requested = True
        self._zero_models()

    def _zero_models(self) -> None:
        self._updating_model = True
        try:
            for joint_name, model in self._models.items():
                value = DEFAULT_JOINT_POSITIONS[joint_name] if joint_name in self._leg_targets else 0.0
                model.set_value(value)
                unit = "rad" if joint_name in self._leg_targets else "rad/s"
                self._value_labels[joint_name].text = f"{value:+.3f} {unit}"
                if joint_name in self._leg_targets:
                    self._leg_targets[joint_name] = value
                else:
                    self._wheel_velocities[joint_name] = value
        finally:
            self._updating_model = False

    def consume_reset_request(self) -> bool:
        requested = self._reset_requested
        self._reset_requested = False
        return requested

    def apply_commands(self, elapsed_time: float) -> None:
        if ARGS.demo_motion:
            phase = 2.0 * torch.pi * 0.35 * elapsed_time
            sine = float(torch.sin(torch.tensor(phase)).item())
            cosine = float(torch.cos(torch.tensor(phase)).item())
            demo_targets = {
                LEG_JOINTS[0]: DEFAULT_JOINT_POSITIONS[LEG_JOINTS[0]] + 0.22 * sine,
                LEG_JOINTS[1]: DEFAULT_JOINT_POSITIONS[LEG_JOINTS[1]] - 0.18 * sine,
                LEG_JOINTS[2]: DEFAULT_JOINT_POSITIONS[LEG_JOINTS[2]] - 0.22 * cosine,
                LEG_JOINTS[3]: DEFAULT_JOINT_POSITIONS[LEG_JOINTS[3]] + 0.18 * cosine,
            }
            demo_wheel_velocities = {WHEEL_JOINTS[0]: 3.0 * sine, WHEEL_JOINTS[1]: -3.0 * sine}
            leg_targets_by_name = _project_leg_targets(demo_targets)
            wheel_values = demo_wheel_velocities
        else:
            leg_targets_by_name = _project_leg_targets(self._leg_targets)
            wheel_values = self._wheel_velocities

        leg_ids = [self._robot.joint_names.index(name) for name in LEG_JOINTS]
        wheel_ids = [self._robot.joint_names.index(name) for name in WHEEL_JOINTS]
        leg_targets = torch.tensor(
            [[leg_targets_by_name[name] for name in LEG_JOINTS]],
            dtype=self._robot.data.joint_pos.dtype,
            device=self._robot.device,
        )
        wheel_targets = torch.tensor(
            [[wheel_values[name] for name in WHEEL_JOINTS]],
            dtype=self._robot.data.joint_vel.dtype,
            device=self._robot.device,
        )
        self._robot.set_joint_position_target(leg_targets, joint_ids=leg_ids)
        self._robot.set_joint_velocity_target(wheel_targets, joint_ids=wheel_ids)

    def update_status(self, residuals: dict[str, float]) -> None:
        if self._status_label is None:
            return
        max_residual = max(residuals.values())
        state = "OK" if max_residual <= ARGS.max_loop_residual else "HIGH"
        self._status_label.text = (
            f"status: {state} | max={max_residual:.3e} m | threshold={ARGS.max_loop_residual:.3e} m"
        )
        for name, residual in residuals.items():
            self._residual_labels[name].text = f"{name}: {residual:.3e} m"
        actual_leg_positions = {
            name: float(self._robot.data.joint_pos[0, self._robot.joint_names.index(name)].item())
            for name in LEG_JOINTS
        }
        for tendon in FIXED_TENDONS:
            target_coordinate = _tendon_coordinate(tendon, self._leg_targets)
            actual_coordinate = _tendon_coordinate(tendon, actual_leg_positions)
            self._tendon_labels[tendon.name].text = (
                f"{tendon.name}: target={target_coordinate:.3f}, actual={actual_coordinate:.3f} rad "
                f"in [{tendon.lower:.3f}, {tendon.upper:.3f}]"
            )
        passive_values = []
        for name in PASSIVE_JOINTS:
            joint_index = self._robot.joint_names.index(name)
            passive_values.append(f"{name}={float(self._robot.data.joint_pos[0, joint_index].item()):+.3f}")
        self._passive_label.text = "passive joints: " + "  ".join(passive_values)


def _configure_physics_overlays() -> None:
    settings = carb.settings.get_settings()
    # Physics viewport menu values are: 0=None, 1=Selected, 2=All.
    settings.set(physx_bindings.SETTING_DISPLAY_COLLIDERS, 2 if ARGS.view_mode in {"collision", "both"} else 0)
    settings.set(physx_bindings.SETTING_DISPLAY_JOINTS, bool(ARGS.show_joints))


def _add_preview_lighting() -> None:
    """Light the collision geometry without changing the runtime robot USD."""
    dome_light_cfg = sim_utils.DomeLightCfg(intensity=1500.0, color=(0.78, 0.82, 0.9))
    dome_light_cfg.func("/World/PreviewDomeLight", dome_light_cfg)
    key_light_cfg = sim_utils.DistantLightCfg(intensity=2500.0, color=(1.0, 0.96, 0.9), angle=0.35)
    key_light_cfg.func("/World/PreviewKeyLight", key_light_cfg)


def _spawn_collision_geometry_preview() -> tuple[int, int]:
    """Create render-only copies parented below their moving rigid bodies."""
    from pxr import Usd, UsdGeom, UsdShade

    stage = sim_utils.get_current_stage()
    robot_path = "/World/Robot"
    material_path = "/World/Looks/SerialLegCollisionPreview"
    source_meshes = [
        prim
        for prim in Usd.PrimRange(stage.GetPseudoRoot(), Usd.TraverseInstanceProxies())
        if prim.IsA(UsdGeom.Mesh) and prim.GetPath().HasPrefix(robot_path)
    ]
    source_cylinders = [
        prim
        for prim in Usd.PrimRange(stage.GetPseudoRoot(), Usd.TraverseInstanceProxies())
        if prim.IsA(UsdGeom.Cylinder) and prim.GetPath().HasPrefix(robot_path)
    ]
    if len(source_meshes) != 54:
        paths = [str(prim.GetPath()) for prim in source_meshes]
        raise RuntimeError(f"expected 54 robot collision meshes for preview, got {len(paths)}: {paths}")
    if len(source_cylinders) != 2:
        paths = [str(prim.GetPath()) for prim in source_cylinders]
        raise RuntimeError(f"expected 2 robot collision cylinders for preview, got {len(paths)}: {paths}")

    material_cfg = sim_utils.PreviewSurfaceCfg(
        diffuse_color=(0.32, 0.48, 0.66), emissive_color=(0.04, 0.07, 0.1), metallic=0.15, roughness=0.38
    )
    material_cfg.func(material_path, material_cfg)
    material = UsdShade.Material.Get(stage, material_path)
    if not material:
        raise RuntimeError("failed to create the SerialLeg collision preview material")

    def body_ancestor(source_prim):
        ancestor = source_prim
        while ancestor and ancestor.GetParent() and str(ancestor.GetParent().GetPath()) != robot_path:
            ancestor = ancestor.GetParent()
        if not ancestor or str(ancestor.GetParent().GetPath()) != robot_path:
            raise RuntimeError(f"collision geometry is not below a direct robot body: {source_prim.GetPath()}")
        return ancestor

    preview_roots = {}

    def preview_root_for(source_prim):
        body_prim = body_ancestor(source_prim)
        body_path = str(body_prim.GetPath())
        if body_path not in preview_roots:
            root = UsdGeom.Xform.Define(stage, f"{body_path}/collision_preview_render").GetPrim()
            UsdShade.MaterialBindingAPI.Apply(root).Bind(
                material, bindingStrength=UsdShade.Tokens.strongerThanDescendants
            )
            preview_roots[body_path] = root
        return body_prim, preview_roots[body_path]

    xform_cache = UsdGeom.XformCache()
    for index, source_prim in enumerate(source_meshes):
        body_prim, preview_root = preview_root_for(source_prim)
        source_mesh = UsdGeom.Mesh(source_prim)
        points = source_mesh.GetPointsAttr().Get()
        face_counts = source_mesh.GetFaceVertexCountsAttr().Get()
        face_indices = source_mesh.GetFaceVertexIndicesAttr().Get()
        if not points or not face_counts or not face_indices:
            raise RuntimeError(f"collision mesh {source_prim.GetPath()} has incomplete topology")
        preview_mesh = UsdGeom.Mesh.Define(stage, f"{preview_root.GetPath()}/mesh_{index:02d}")
        preview_mesh.CreatePointsAttr(points)
        preview_mesh.CreateFaceVertexCountsAttr(face_counts)
        preview_mesh.CreateFaceVertexIndicesAttr(face_indices)
        preview_mesh.CreateOrientationAttr(source_mesh.GetOrientationAttr().Get() or UsdGeom.Tokens.rightHanded)
        preview_mesh.CreateDoubleSidedAttr(True)
        normals = source_mesh.GetNormalsAttr().Get()
        if normals:
            preview_mesh.CreateNormalsAttr(normals)
            preview_mesh.SetNormalsInterpolation(source_mesh.GetNormalsInterpolation())
        body_world = xform_cache.GetLocalToWorldTransform(body_prim)
        source_world = xform_cache.GetLocalToWorldTransform(source_prim)
        UsdGeom.Xformable(preview_mesh).AddTransformOp().Set(source_world * body_world.GetInverse())

    for index, source_prim in enumerate(source_cylinders):
        body_prim, preview_root = preview_root_for(source_prim)
        source_cylinder = UsdGeom.Cylinder(source_prim)
        radius = source_cylinder.GetRadiusAttr().Get()
        height = source_cylinder.GetHeightAttr().Get()
        axis = source_cylinder.GetAxisAttr().Get() or UsdGeom.Tokens.z
        if radius is None or radius <= 0.0 or height is None or height <= 0.0:
            raise RuntimeError(
                f"collision cylinder {source_prim.GetPath()} has invalid dimensions: radius={radius}, height={height}"
            )
        preview_cylinder = UsdGeom.Cylinder.Define(stage, f"{preview_root.GetPath()}/cylinder_{index:02d}")
        preview_cylinder.CreateRadiusAttr(radius)
        preview_cylinder.CreateHeightAttr(height)
        preview_cylinder.CreateAxisAttr(axis)
        preview_cylinder.CreateDoubleSidedAttr(True)
        extent = source_cylinder.GetExtentAttr().Get()
        if extent:
            preview_cylinder.CreateExtentAttr(extent)
        body_world = xform_cache.GetLocalToWorldTransform(body_prim)
        source_world = xform_cache.GetLocalToWorldTransform(source_prim)
        UsdGeom.Xformable(preview_cylinder).AddTransformOp().Set(source_world * body_world.GetInverse())

    return len(source_meshes), len(source_cylinders)


def _create_robot(usd_path: Path) -> Articulation:
    robot_cfg = ArticulationCfg(
        prim_path="/World/Robot",
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
                fix_root_link=not ARGS.floating_base,
            ),
        ),
        init_state=ArticulationCfg.InitialStateCfg(
            pos=(0.0, 0.0, ARGS.root_height),
            joint_pos=DEFAULT_JOINT_POSITIONS,
            joint_vel={".*": 0.0},
        ),
        actuators={
            "legs": _actuator_cfg("legs"),
            "wheels": _actuator_cfg("wheels"),
            "closed_chain_passive": _actuator_cfg("closed_chain_passive"),
        },
    )
    return Articulation(robot_cfg)


def main() -> int:
    usd_path = ARGS.usd.resolve()
    if not usd_path.is_file():
        raise FileNotFoundError(f"SerialLeg USD not found: {usd_path}")
    if ARGS.frames < 0:
        raise ValueError("--frames must be non-negative")
    if ARGS.root_height <= 0.0:
        raise ValueError("--root-height must be positive")
    if ARGS.max_loop_residual <= 0.0:
        raise ValueError("--max-loop-residual must be positive")
    if ARGS.min_demo_motion <= 0.0:
        raise ValueError("--min-demo-motion must be positive")

    simulation = SimulationContext(sim_utils.SimulationCfg(dt=0.005, device=ARGS.device))
    _add_preview_lighting()
    robot = _create_robot(usd_path)
    preview_meshes, preview_cylinders = (
        _spawn_collision_geometry_preview() if ARGS.view_mode in {"render", "both"} else (0, 0)
    )
    simulation.set_camera_view(eye=(1.35, -1.55, 0.85), target=(0.0, 0.0, 0.23))
    simulation.reset()
    robot.write_joint_state_to_sim(robot.data.default_joint_pos, robot.data.default_joint_vel)
    controls = JointControlPanel(robot)
    _configure_physics_overlays()
    residuals = _loop_residuals(robot)
    controls.update_status(residuals)
    max_observed_residual = max(residuals.values())
    initial_joint_pos = robot.data.joint_pos.clone()
    leg_joint_ids = [robot.joint_names.index(name) for name in LEG_JOINTS]
    wheel_joint_ids = [robot.joint_names.index(name) for name in WHEEL_JOINTS]
    passive_joint_ids = [robot.joint_names.index(name) for name in PASSIVE_JOINTS]
    max_leg_motion = 0.0
    max_wheel_motion = 0.0
    max_passive_motion = 0.0

    print(f"[serialleg-collision-view] usd={usd_path}", flush=True)
    print(
        "[serialleg-collision-view] "
        f"view_mode={ARGS.view_mode} gravity=disabled root_height={ARGS.root_height:.3f}m "
        f"base={'floating' if ARGS.floating_base else 'fixed'} demo_motion={ARGS.demo_motion} "
        f"bodies={robot.num_bodies} dofs={robot.num_joints} "
        f"preview_meshes={preview_meshes} preview_cylinders={preview_cylinders}",
        flush=True,
    )
    print(
        f"[serialleg-collision-view] active_leg_position_controls={LEG_JOINTS} "
        f"wheel_velocity_controls={WHEEL_JOINTS} passive_joints={PASSIVE_JOINTS}",
        flush=True,
    )
    print(
        f"[serialleg-collision-view] rod_target_span={2.0 * LEG_CONTROL_HALF_RANGE:.6f}rad "
        f"coupled_limits={{{', '.join(f'{t.name!r}: ({t.lower:.6f}, {t.upper:.6f})' for t in FIXED_TENDONS)}}}",
        flush=True,
    )
    if ARGS.view_mode in {"collision", "both"}:
        print(
            "[serialleg-collision-view] green=dynamic collider, magenta=static collider, dark-red=PhysX fallback",
            flush=True,
        )
    else:
        print(
            "[serialleg-collision-view] lit blue-gray solid geometry preview; use --view-mode both for PhysX overlays",
            flush=True,
        )

    frame = 0
    physics_dt = simulation.get_physics_dt()
    while SIMULATION_APP.is_running() and (ARGS.frames == 0 or frame < ARGS.frames):
        if controls.consume_reset_request():
            robot.write_joint_state_to_sim(robot.data.default_joint_pos, robot.data.default_joint_vel)
            robot.reset()
        controls.apply_commands(frame * physics_dt)
        robot.write_data_to_sim()
        simulation.step(render=True)
        robot.update(physics_dt)
        residuals = _loop_residuals(robot)
        max_observed_residual = max(max_observed_residual, max(residuals.values()))
        joint_motion = torch.abs(robot.data.joint_pos - initial_joint_pos)
        max_leg_motion = max(max_leg_motion, float(joint_motion[:, leg_joint_ids].max().item()))
        max_wheel_motion = max(max_wheel_motion, float(joint_motion[:, wheel_joint_ids].max().item()))
        max_passive_motion = max(max_passive_motion, float(joint_motion[:, passive_joint_ids].max().item()))
        controls.update_status(residuals)
        frame += 1
    if ARGS.frames > 0 and max_observed_residual > ARGS.max_loop_residual:
        raise RuntimeError(
            f"interactive viewer loop residual {max_observed_residual:.3e}m exceeds "
            f"threshold {ARGS.max_loop_residual:.3e}m"
        )
    if ARGS.frames > 0 and ARGS.demo_motion:
        if max_leg_motion < ARGS.min_demo_motion or max_passive_motion < ARGS.min_demo_motion:
            raise RuntimeError(
                f"demo motion is too small: active_legs={max_leg_motion:.3e}rad "
                f"passive={max_passive_motion:.3e}rad threshold={ARGS.min_demo_motion:.3e}rad"
            )
    print(
        f"[serialleg-collision-view] max_loop_residual={max_observed_residual:.3e}m "
        f"threshold={ARGS.max_loop_residual:.3e}m max_leg_motion={max_leg_motion:.3e}rad "
        f"max_wheel_motion={max_wheel_motion:.3e}rad "
        f"max_passive_motion={max_passive_motion:.3e}rad",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except BaseException:
        traceback.print_exc()
        exit_code = 1
    # This process owns the interactive viewer.  Exit directly after the
    # window closes (or a bounded --frames run finishes) because Kit teardown
    # can stall on hosts that have exhausted inotify watches.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exit_code)
