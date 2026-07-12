# Copyright (c) 2026, SE3 RL Lab contributors.
# SPDX-License-Identifier: BSD-3-Clause

"""SerialLeg robot configurations."""

from pathlib import Path

import isaaclab.sim as sim_utils
from isaaclab.actuators import DCMotorCfg, ImplicitActuatorCfg
from isaaclab.assets import ArticulationCfg

from .serialleg_actuators import TorqueSpeedCurveActuatorCfg
from .serialleg_contract import SERIALLEG_CONTRACT
from .serialleg_motors import DM8009P, M3508_C620_14

SERIALLEG_ASSET_DIR = Path(__file__).resolve().parent / "serialleg"
SERIALLEG_CLOSED_CHAIN_USD = SERIALLEG_ASSET_DIR / SERIALLEG_CONTRACT.runtime_usd

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


def _passive_actuator_cfg(group_name: str) -> ImplicitActuatorCfg:
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


def _leg_actuator_cfg() -> DCMotorCfg:
    group = SERIALLEG_CONTRACT.actuator_groups["legs"]
    return DCMotorCfg(
        joint_names_expr=list(group.joint_names),
        effort_limit=DM8009P.rated_torque,
        velocity_limit=DM8009P.no_load_speed,
        saturation_effort=DM8009P.stall_torque,
        effort_limit_sim=DM8009P.stall_torque,
        stiffness=group.stiffness,
        damping=group.damping,
    )


def _wheel_actuator_cfg() -> TorqueSpeedCurveActuatorCfg:
    group = SERIALLEG_CONTRACT.actuator_groups["wheels"]
    return TorqueSpeedCurveActuatorCfg(
        joint_names_expr=list(group.joint_names),
        effort_limit=M3508_C620_14.rated_torque,
        effort_limit_sim=M3508_C620_14.stall_torque,
        stiffness=group.stiffness,
        damping=group.damping,
        torque_speed_curve=M3508_C620_14.torque_speed_curve,
    )


SERIALLEG_CLOSED_CHAIN_CFG = ArticulationCfg(
    spawn=sim_utils.UsdFileCfg(
        usd_path=str(SERIALLEG_CLOSED_CHAIN_USD),
        activate_contact_sensors=True,
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
        pos=SERIALLEG_CONTRACT.root_position,
        rot=SERIALLEG_CONTRACT.root_rotation_wxyz,
        joint_pos=SERIALLEG_DEFAULT_JOINT_POS,
        joint_vel={".*": 0.0},
    ),
    actuators={
        "legs": _leg_actuator_cfg(),
        "wheels": _wheel_actuator_cfg(),
        "closed_chain_passive": _passive_actuator_cfg("closed_chain_passive"),
    },
)
"""SerialLeg closed-chain USD articulation configuration."""
