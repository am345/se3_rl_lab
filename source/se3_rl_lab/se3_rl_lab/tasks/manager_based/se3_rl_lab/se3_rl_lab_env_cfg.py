# Copyright (c) 2022-2025, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

import math

import isaaclab.sim as sim_utils
from isaaclab.assets import ArticulationCfg, AssetBaseCfg
from isaaclab.envs import ManagerBasedRLEnvCfg
from isaaclab.managers import CurriculumTermCfg as CurrTerm
from isaaclab.managers import EventTermCfg as EventTerm
from isaaclab.managers import ObservationGroupCfg as ObsGroup
from isaaclab.managers import ObservationTermCfg as ObsTerm
from isaaclab.managers import RewardTermCfg as RewTerm
from isaaclab.managers import SceneEntityCfg
from isaaclab.managers import TerminationTermCfg as DoneTerm
from isaaclab.scene import InteractiveSceneCfg
from isaaclab.sensors import ContactSensorCfg
from isaaclab.utils import configclass
from isaaclab.utils.noise import AdditiveUniformNoiseCfg as Unoise

from se3_rl_lab.assets.robots.serialleg import (
    SERIALLEG_CLOSED_CHAIN_CFG,
    SERIALLEG_POLICY_LEG_JOINTS,
    SERIALLEG_WHEEL_JOINTS,
)

from . import mdp

_POLICY_JOINTS = (*SERIALLEG_POLICY_LEG_JOINTS, *SERIALLEG_WHEEL_JOINTS)
_VELOCITY_STAGES = (
    {"iteration": 0, "lin_vel_x_range": (-0.4, 0.4), "ang_vel_yaw_range": (-1.0, 1.0)},
    {"iteration": 400, "lin_vel_x_range": (-0.8, 0.8), "ang_vel_yaw_range": (-2.0, 2.0)},
    {"iteration": 800, "lin_vel_x_range": (-1.2, 1.2), "ang_vel_yaw_range": (-4.0, 4.0)},
    {"iteration": 1200, "lin_vel_x_range": (-1.6, 1.6), "ang_vel_yaw_range": (-6.0, 6.0)},
    {"iteration": 1600, "lin_vel_x_range": (-2.0, 2.0), "ang_vel_yaw_range": (-9.0, 9.0)},
    {"iteration": 2000, "lin_vel_x_range": (-2.4, 2.4), "ang_vel_yaw_range": (-12.0, 12.0)},
)
_PUSH_STAGES = (
    {"iteration": 0, "lin_vel_range": (0.0, 0.0)},
    {"iteration": 2000, "lin_vel_range": (-0.3, 0.3)},
    {"iteration": 5000, "lin_vel_range": (-0.5, 0.5)},
    {"iteration": 10000, "lin_vel_range": (-1.0, 1.0)},
    {"iteration": 20000, "lin_vel_range": (-1.5, 1.5)},
    {"iteration": 40000, "lin_vel_range": (-2.0, 2.0)},
)

##
# Scene definition
##


@configclass
class Se3RlLabSceneCfg(InteractiveSceneCfg):
    """Configuration for the SerialLeg flat scene."""

    # ground plane
    ground = AssetBaseCfg(
        prim_path="/World/ground",
        spawn=sim_utils.GroundPlaneCfg(size=(100.0, 100.0)),
    )

    # robot
    robot: ArticulationCfg = SERIALLEG_CLOSED_CHAIN_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")

    # whole-body contact reports for task gates and future contact rewards
    contact_forces = ContactSensorCfg(
        prim_path="{ENV_REGEX_NS}/Robot/.*",
        history_length=3,
        track_air_time=False,
    )

    # lights
    dome_light = AssetBaseCfg(
        prim_path="/World/DomeLight",
        spawn=sim_utils.DomeLightCfg(color=(0.9, 0.9, 0.9), intensity=500.0),
    )


##
# MDP settings
##


@configclass
class ActionsCfg:
    """Action specifications for the MDP."""

    serialleg_delayed = mdp.SerialLegDelayedActionCfg(
        asset_name="robot",
    )


@configclass
class CommandsCfg:
    """Strict 8D flat command plus an official-reward-compatible planar view."""

    velocity_height = mdp.VelocityHeightCommandCfg(
        asset_name="robot",
        resampling_time_range=(5.0, 5.0),
        lin_vel_x_range=(-0.4, 0.4),
        ang_vel_yaw_range=(-1.0, 1.0),
        pitch_range=(0.0, 0.0),
        roll_range=(0.0, 0.0),
        height_range=(0.20, 0.32),
        standing_height_range=(0.20, 0.32),
        standing_ratio=0.1,
        constrain_diff_drive_commands=True,
        diff_drive_wheel_radius=0.06,
        diff_drive_half_track=0.20,
        diff_drive_max_wheel_speed=45.0,
        diff_drive_wheel_speed_fraction=0.9,
    )
    base_velocity = mdp.PlanarVelocityCommandCfg(source_command_name="velocity_height")


@configclass
class ObservationsCfg:
    """Legacy-compatible 34D actor and 40D privileged-critic observations."""

    @configclass
    class ActorCfg(ObsGroup):
        """34D actor observations in checkpoint/deployment order."""

        base_ang_vel = ObsTerm(
            func=mdp.base_ang_vel_obs,
            params={"asset_cfg": SceneEntityCfg("robot")},
            noise=Unoise(n_min=-0.2, n_max=0.2),
        )
        projected_gravity = ObsTerm(
            func=mdp.projected_gravity_obs,
            params={"asset_cfg": SceneEntityCfg("robot")},
            noise=Unoise(n_min=-0.05, n_max=0.05),
        )
        commands = ObsTerm(func=mdp.commands_obs, params={"asset_cfg": SceneEntityCfg("robot")})
        leg_joint_pos = ObsTerm(
            func=mdp.leg_joint_pos_obs,
            params={
                "asset_cfg": SceneEntityCfg("robot", joint_names=list(SERIALLEG_POLICY_LEG_JOINTS), preserve_order=True)
            },
            noise=Unoise(n_min=-0.01, n_max=0.01),
        )
        leg_joint_vel = ObsTerm(
            func=mdp.leg_joint_vel_obs,
            params={
                "asset_cfg": SceneEntityCfg("robot", joint_names=list(SERIALLEG_POLICY_LEG_JOINTS), preserve_order=True)
            },
            noise=Unoise(n_min=-1.5, n_max=1.5),
        )
        wheel_pos_zero = ObsTerm(
            func=mdp.wheel_pos_obs,
            params={
                "asset_cfg": SceneEntityCfg("robot", joint_names=list(SERIALLEG_WHEEL_JOINTS), preserve_order=True)
            },
        )
        wheel_vel = ObsTerm(
            func=mdp.wheel_vel_obs,
            params={
                "asset_cfg": SceneEntityCfg("robot", joint_names=list(SERIALLEG_WHEEL_JOINTS), preserve_order=True)
            },
        )
        last_actions = ObsTerm(func=mdp.last_actions_obs)
        jump_commands = ObsTerm(func=mdp.jump_commands_obs, params={"asset_cfg": SceneEntityCfg("robot")})

        def __post_init__(self) -> None:
            self.enable_corruption = True
            self.concatenate_terms = True

    @configclass
    class CriticCfg(ActorCfg):
        """Actor observations followed by 6D privileged state (40D total)."""

        base_lin_vel = ObsTerm(func=mdp.base_lin_vel_obs, params={"asset_cfg": SceneEntityCfg("robot")})
        wheel_contact_forces = ObsTerm(
            func=mdp.wheel_contact_force_obs,
            params={
                "sensor_cfg": SceneEntityCfg(
                    "contact_forces",
                    body_names=["l_wheel_Link", "r_wheel_Link"],
                    preserve_order=True,
                )
            },
        )
        base_height = ObsTerm(func=mdp.flat_base_height_obs, params={"asset_cfg": SceneEntityCfg("robot")})

        def __post_init__(self) -> None:
            self.enable_corruption = False
            self.concatenate_terms = True

    actor: ActorCfg = ActorCfg()
    critic: CriticCfg = CriticCfg()


@configclass
class EventCfg:
    """Basic reset, domain-randomization and push events."""

    physics_material = EventTerm(
        func=mdp.randomize_rigid_body_material,
        mode="startup",
        params={
            "asset_cfg": SceneEntityCfg("robot", body_names=".*"),
            "static_friction_range": (0.2, 1.5),
            "dynamic_friction_range": (0.2, 1.5),
            "restitution_range": (0.0, 0.5),
            "num_buckets": 64,
            "make_consistent": True,
        },
    )
    add_base_mass = EventTerm(
        func=mdp.randomize_rigid_body_mass,
        mode="startup",
        params={
            "asset_cfg": SceneEntityCfg("robot", body_names="base_link"),
            "mass_distribution_params": (-0.5, 1.5),
            "operation": "add",
            "recompute_inertia": True,
        },
    )
    base_com = EventTerm(
        func=mdp.randomize_rigid_body_com,
        mode="startup",
        params={
            "asset_cfg": SceneEntityCfg("robot", body_names="base_link"),
            "com_range": {"x": (-0.05, 0.05), "y": (-0.05, 0.05), "z": (-0.05, 0.05)},
        },
    )
    actuator_gains = EventTerm(
        func=mdp.randomize_actuator_gains,
        mode="startup",
        params={
            "asset_cfg": SceneEntityCfg("robot", joint_names=list(_POLICY_JOINTS), preserve_order=True),
            "stiffness_distribution_params": (0.9, 1.1),
            "damping_distribution_params": (0.9, 1.1),
            "operation": "scale",
        },
    )
    reset_base = EventTerm(
        func=mdp.reset_root_state_uniform,
        mode="reset",
        params={
            "asset_cfg": SceneEntityCfg("robot"),
            "pose_range": {"x": (-0.1, 0.1), "y": (-0.1, 0.1), "yaw": (-math.pi, math.pi)},
            "velocity_range": {},
        },
    )
    reset_robot_joints = EventTerm(
        func=mdp.reset_joints_by_offset,
        mode="reset",
        params={
            "asset_cfg": SceneEntityCfg("robot"),
            "position_range": (0.0, 0.0),
            "velocity_range": (0.0, 0.0),
        },
    )
    push_robot = EventTerm(
        func=mdp.push_by_setting_velocity,
        mode="interval",
        interval_range_s=(5.0, 6.0),
        params={
            "asset_cfg": SceneEntityCfg("robot"),
            "velocity_range": {"x": (0.0, 0.0), "y": (0.0, 0.0)},
        },
    )


@configclass
class RewardsCfg:
    """IsaacLab official manager-based locomotion reward terms only."""

    track_lin_vel_xy_exp = RewTerm(
        func=mdp.track_lin_vel_xy_exp,
        weight=1.0,
        params={"command_name": "base_velocity", "std": math.sqrt(0.25)},
    )
    track_ang_vel_z_exp = RewTerm(
        func=mdp.track_ang_vel_z_exp,
        weight=0.5,
        params={"command_name": "base_velocity", "std": math.sqrt(0.25)},
    )
    lin_vel_z_l2 = RewTerm(func=mdp.lin_vel_z_l2, weight=-2.0)
    ang_vel_xy_l2 = RewTerm(func=mdp.ang_vel_xy_l2, weight=-0.05)
    joint_torques_l2 = RewTerm(
        func=mdp.joint_torques_l2,
        weight=-1.0e-5,
        params={"asset_cfg": SceneEntityCfg("robot", joint_names=list(_POLICY_JOINTS), preserve_order=True)},
    )
    joint_acc_l2 = RewTerm(
        func=mdp.joint_acc_l2,
        weight=-2.5e-7,
        params={"asset_cfg": SceneEntityCfg("robot", joint_names=list(_POLICY_JOINTS), preserve_order=True)},
    )
    action_rate_l2 = RewTerm(func=mdp.action_rate_l2, weight=-0.01)
    flat_orientation_l2 = RewTerm(func=mdp.flat_orientation_l2, weight=-2.5)
    undesired_base_contact = RewTerm(
        func=mdp.undesired_contacts,
        weight=-1.0,
        params={
            "sensor_cfg": SceneEntityCfg("contact_forces", body_names="base_link"),
            "threshold": 1.0,
        },
    )


@configclass
class TerminationsCfg:
    """Official flat-locomotion termination terms."""

    time_out = DoneTerm(func=mdp.time_out, time_out=True)
    bad_orientation = DoneTerm(
        func=mdp.bad_orientation,
        params={"asset_cfg": SceneEntityCfg("robot"), "limit_angle": 0.5236},
    )
    base_contact = DoneTerm(
        func=mdp.illegal_contact,
        params={
            "sensor_cfg": SceneEntityCfg("contact_forces", body_names="base_link"),
            "threshold": 1.0,
        },
    )


@configclass
class CurriculumCfg:
    """Legacy flat command/push stages without any jump curriculum."""

    flat_velocity_and_push = CurrTerm(
        func=mdp.flat_velocity_and_push,
        params={
            "command_name": "velocity_height",
            "push_event_name": "push_robot",
            "steps_per_policy_iteration": 64,
            "velocity_stages": _VELOCITY_STAGES,
            "push_stages": _PUSH_STAGES,
        },
    )


##
# Environment configuration
##


@configclass
class Se3RlLabEnvCfg(ManagerBasedRLEnvCfg):
    # Scene settings
    scene: Se3RlLabSceneCfg = Se3RlLabSceneCfg(num_envs=4096, env_spacing=4.0)
    # Basic settings
    observations: ObservationsCfg = ObservationsCfg()
    actions: ActionsCfg = ActionsCfg()
    commands: CommandsCfg = CommandsCfg()
    events: EventCfg = EventCfg()
    # MDP settings
    rewards: RewardsCfg = RewardsCfg()
    terminations: TerminationsCfg = TerminationsCfg()
    curriculum: CurriculumCfg = CurriculumCfg()

    # Post initialization
    def __post_init__(self) -> None:
        """Post initialization."""
        # general settings
        self.decimation = 4
        self.episode_length_s = 20
        # viewer settings
        self.viewer.eye = (8.0, 0.0, 5.0)
        # simulation settings
        self.sim.dt = 0.005
        self.sim.render_interval = self.decimation
