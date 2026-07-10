# Copyright (c) 2026, SE3 RL Lab contributors.
# SPDX-License-Identifier: BSD-3-Clause

"""SerialLeg robot configurations."""

from pathlib import Path

from isaacsim.core.utils.extensions import enable_extension
from pxr import Gf, Sdf, Usd, UsdPhysics

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets import ArticulationCfg
from isaaclab.sim.spawners.from_files.from_files import spawn_from_mjcf
from isaaclab.sim.utils import clone

from .serialleg_contract import SERIALLEG_CONTRACT

enable_extension("isaacsim.asset.importer.mjcf")

SERIALLEG_ASSET_DIR = Path(__file__).resolve().parent / "serialleg"
SERIALLEG_ORIGINAL_CLOSED_CHAIN_MJCF = SERIALLEG_ASSET_DIR / "mjcf" / "serialleg_closed_chain_complex_collision.xml"
SERIALLEG_CLOSED_CHAIN_MJCF = (
    SERIALLEG_ASSET_DIR / "mjcf" / "serialleg_closed_chain_complex_collision_isaaclab_import.xml"
)

SERIALLEG_POLICY_LEG_JOINTS = SERIALLEG_CONTRACT.actuator_groups["legs"].joint_names
SERIALLEG_WHEEL_JOINTS = SERIALLEG_CONTRACT.actuator_groups["wheels"].joint_names
SERIALLEG_PASSIVE_CLOSED_CHAIN_JOINTS = SERIALLEG_CONTRACT.passive_joint_names
SERIALLEG_POLICY_JOINTS = SERIALLEG_CONTRACT.policy_joint_order
SERIALLEG_POLICY_ACTION_SCALE = {
    joint_name: group.action_scale
    for group in SERIALLEG_CONTRACT.actuator_groups.values()
    if group.policy and group.action_scale is not None
    for joint_name in group.joint_names
}
SERIALLEG_DEFAULT_JOINT_POS = SERIALLEG_CONTRACT.default_joint_positions


def _actuator_cfg(group_name: str) -> ImplicitActuatorCfg:
    group = SERIALLEG_CONTRACT.actuator_groups[group_name]
    kwargs = {
        "joint_names_expr": list(group.joint_names),
        "effort_limit_sim": group.effort_limit_sim,
        "stiffness": group.stiffness,
        "damping": group.damping,
    }
    if group.velocity_limit_sim is not None:
        kwargs["velocity_limit_sim"] = group.velocity_limit_sim
    return ImplicitActuatorCfg(**kwargs)


def _add_serialleg_loop_joints(stage: Usd.Stage, prim_path: str) -> None:
    """Restore the two MJCF equality/connect closures as USD Physics spherical joints."""
    for loop in SERIALLEG_CONTRACT.loop_joints.values():
        joint = UsdPhysics.SphericalJoint.Define(stage, f"{prim_path}/loop_joints/{loop.name}")
        joint.CreateBody0Rel().SetTargets([Sdf.Path(f"{prim_path}/base_link/{loop.body0}")])
        joint.CreateBody1Rel().SetTargets([Sdf.Path(f"{prim_path}/base_link/{loop.body1}")])
        joint.CreateLocalPos0Attr(Gf.Vec3f(*loop.local_pos0))
        joint.CreateLocalPos1Attr(Gf.Vec3f(*loop.local_pos1))
        joint.CreateJointEnabledAttr(True)


@clone
def spawn_serialleg_closed_chain_from_mjcf(
    prim_path: str,
    cfg: sim_utils.MjcfFileCfg,
    translation: tuple[float, float, float] | None = None,
    orientation: tuple[float, float, float, float] | None = None,
) -> Usd.Prim:
    """Spawn SerialLeg from MJCF and add importer-compatible closed-chain constraints."""
    prim = spawn_from_mjcf(prim_path, cfg, translation=translation, orientation=orientation)
    _add_serialleg_loop_joints(prim.GetStage(), str(prim.GetPath()))
    return prim


SERIALLEG_CLOSED_CHAIN_CFG = ArticulationCfg(
    articulation_root_prim_path="/base_link/base_link",
    spawn=sim_utils.MjcfFileCfg(
        func=spawn_serialleg_closed_chain_from_mjcf,
        asset_path=str(SERIALLEG_CLOSED_CHAIN_MJCF),
        fix_base=False,
        import_sites=False,
        self_collision=False,
        rigid_props=sim_utils.RigidBodyPropertiesCfg(
            rigid_body_enabled=True,
            max_linear_velocity=100.0,
            max_angular_velocity=100.0,
            max_depenetration_velocity=10.0,
            enable_gyroscopic_forces=True,
        ),
        articulation_props=sim_utils.ArticulationRootPropertiesCfg(
            enabled_self_collisions=False,
            solver_position_iteration_count=8,
            solver_velocity_iteration_count=2,
            sleep_threshold=0.005,
            stabilization_threshold=0.001,
        ),
    ),
    init_state=ArticulationCfg.InitialStateCfg(
        pos=(0.0, 0.0, SERIALLEG_CONTRACT.root_height),
        joint_pos=SERIALLEG_DEFAULT_JOINT_POS,
        joint_vel={".*": 0.0},
    ),
    actuators={group_name: _actuator_cfg(group_name) for group_name in SERIALLEG_CONTRACT.actuator_groups},
)
"""SerialLeg closed-chain MJCF articulation configuration."""
