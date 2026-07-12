# Copyright (c) 2026, SE3 RL Lab contributors.
# SPDX-License-Identifier: BSD-3-Clause

"""SerialLeg recovery finetune task.

The action, observation, command, scene, curriculum, and PPO contracts are inherited
unchanged from the flat baseline.  Only rewards, reset semantics, and terminations
are replaced by the recovery contract.
"""

import math

from isaaclab.managers import EventTermCfg as EventTerm
from isaaclab.managers import RewardTermCfg as RewTerm
from isaaclab.managers import SceneEntityCfg
from isaaclab.managers import TerminationTermCfg as DoneTerm
from isaaclab.utils import configclass

from se3_rl_lab.assets.robots.serialleg import SERIALLEG_POLICY_LEG_JOINTS, SERIALLEG_WHEEL_JOINTS

from . import mdp
from .se3_rl_lab_env_cfg import Se3RlLabEnvCfg

_ROBOT = SceneEntityCfg("robot")
_LEGS = SceneEntityCfg("robot", joint_names=list(SERIALLEG_POLICY_LEG_JOINTS), preserve_order=True)
_WHEELS = SceneEntityCfg("robot", joint_names=list(SERIALLEG_WHEEL_JOINTS), preserve_order=True)
_WHEEL_CONTACTS = SceneEntityCfg("contact_forces", body_names=["l_wheel_Link", "r_wheel_Link"], preserve_order=True)
_LEG_CONTACTS = SceneEntityCfg("contact_forces", body_names=r"^(?!base_link$|[lr]_wheel_Link$).+")
_BASE_CONTACT = SceneEntityCfg("contact_forces", body_names="base_link")
_UPRIGHT_15_COS = math.cos(math.radians(15.0))


@configclass
class RecoveryRewardsCfg:
    """Exact term names and weights from the spring_add Recovery-Discovery contract."""

    tracking_lin_vel = RewTerm(
        func=mdp.recovery_tracking_lin_vel,
        weight=3.0,
        params={
            "command_name": "velocity_height",
            "sigma_move": 0.25,
            "sigma_stand": 0.05,
            "asset_cfg": _ROBOT,
            "upright_full_cos": _UPRIGHT_15_COS,
        },
    )
    tracking_ang_vel = RewTerm(
        func=mdp.recovery_tracking_ang_vel,
        weight=1.5,
        params={
            "command_name": "velocity_height",
            "sigma": 0.25,
            "asset_cfg": _ROBOT,
            "upright_full_cos": _UPRIGHT_15_COS,
        },
    )
    upward = RewTerm(func=mdp.recovery_upward, weight=3.0, params={"asset_cfg": _ROBOT})
    tracking_height = RewTerm(
        func=mdp.recovery_height_l2,
        weight=-1500.0,
        params={"command_name": "velocity_height", "asset_cfg": _ROBOT},
    )
    lin_vel_z = RewTerm(func=mdp.recovery_lin_vel_z_l2, weight=-2.0, params={"asset_cfg": _ROBOT})
    ang_vel_xy = RewTerm(func=mdp.recovery_ang_vel_xy_l2, weight=-0.05, params={"asset_cfg": _ROBOT})
    upright_orientation_l2 = RewTerm(
        func=mdp.recovery_upright_orientation_l2,
        weight=-0.5,
        params={"command_name": "velocity_height", "asset_cfg": _ROBOT},
    )
    upright_zero_velocity = RewTerm(
        func=mdp.recovery_upright_zero_velocity,
        weight=-0.05,
        params={"command_name": "velocity_height", "asset_cfg": _ROBOT, "wheel_cfg": _WHEELS},
    )
    stand_still = RewTerm(
        func=mdp.recovery_stand_still,
        weight=-2.0,
        params={"command_name": "velocity_height", "asset_cfg": _LEGS},
    )
    joint_pos_penalty = RewTerm(
        func=mdp.recovery_joint_pos_penalty,
        weight=-1.0,
        params={"command_name": "velocity_height", "asset_cfg": _LEGS},
    )
    leg_action_rate = RewTerm(func=mdp.recovery_leg_action_rate, weight=-0.001)
    wheel_action_rate = RewTerm(func=mdp.recovery_wheel_action_rate, weight=-0.001)
    action_smoothness = RewTerm(
        func=mdp.recovery_action_smoothness,
        weight=-0.03,
        params={"asset_cfg": _ROBOT, "leg_scale": 1.0, "wheel_scale": 2.0},
    )
    leg_torques = RewTerm(func=mdp.joint_torques_l2, weight=-2.0e-4, params={"asset_cfg": _LEGS})
    leg_dof_acc = RewTerm(func=mdp.joint_acc_l2, weight=-2.5e-7, params={"asset_cfg": _LEGS})
    leg_power = RewTerm(func=mdp.recovery_leg_power, weight=-1.0e-4, params={"asset_cfg": _LEGS})
    wheel_torques = RewTerm(
        func=mdp.recovery_wheel_torque_excess,
        weight=-1.0e-4,
        params={"asset_cfg": _WHEELS, "max_torque": 3.0},
    )
    joint_mirror = RewTerm(func=mdp.recovery_joint_mirror, weight=-0.05, params={"asset_cfg": _LEGS})
    dof_pos_limits = RewTerm(func=mdp.recovery_dof_pos_limits, weight=-5.0, params={"asset_cfg": _LEGS})
    collision = RewTerm(
        func=mdp.recovery_contact_count,
        weight=-1.0,
        params={"sensor_cfg": _BASE_CONTACT, "threshold": 0.1},
    )
    contact_forces = RewTerm(
        func=mdp.recovery_contact_force_excess,
        weight=-1.5e-4,
        params={"sensor_cfg": _WHEEL_CONTACTS, "threshold": 20.0},
    )
    wheel_air_velocity = RewTerm(
        func=mdp.recovery_wheel_air_velocity,
        weight=-1.0e-3,
        params={"asset_cfg": _WHEELS, "sensor_cfg": _WHEEL_CONTACTS},
    )
    leg_contact = RewTerm(
        func=mdp.recovery_contact_count,
        weight=-1.0,
        params={"sensor_cfg": _LEG_CONTACTS, "threshold": 1.0},
    )
    wheel_contact_without_cmd = RewTerm(
        func=mdp.recovery_wheel_contact_without_cmd,
        weight=0.1,
        params={
            "command_name": "velocity_height",
            "asset_cfg": _ROBOT,
            "sensor_cfg": _WHEEL_CONTACTS,
        },
    )
    diagnostics = RewTerm(func=mdp.recovery_diagnostics, weight=1.0)


@configclass
class RecoveryTerminationsCfg:
    """Falling is recoverable; timeout and physically divergent states end an episode."""

    time_out = DoneTerm(func=mdp.time_out, time_out=True)
    catastrophic_state = DoneTerm(
        func=mdp.catastrophic_state,
        params={
            "max_leg_vel": 120.0,
            "max_root_lin_vel": 80.0,
            "max_root_ang_vel": 500.0,
            "min_base_height": -0.5,
            "max_base_height": 3.0,
        },
    )


@configclass
class RecoveryEnvCfg(Se3RlLabEnvCfg):
    """Recovery task with the flat policy interface kept byte-for-byte compatible."""

    rewards: RecoveryRewardsCfg = RecoveryRewardsCfg()
    terminations: RecoveryTerminationsCfg = RecoveryTerminationsCfg()

    def __post_init__(self) -> None:
        super().__post_init__()
        self.events.reset_base = EventTerm(
            func=mdp.reset_root_state_recovery_mixed,
            mode="reset",
            params={
                "asset_cfg": SceneEntityCfg("robot"),
                "steps_per_policy_iteration": 24,
                "cache_split": "train",
            },
        )
        self.events.reset_robot_joints = EventTerm(
            func=mdp.reset_recovery_joints,
            mode="reset",
            params={"asset_cfg": SceneEntityCfg("robot"), "steps_per_policy_iteration": 24},
        )


__all__ = [
    "RecoveryEnvCfg",
    "RecoveryRewardsCfg",
    "RecoveryTerminationsCfg",
]
