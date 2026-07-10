# Copyright (c) 2022-2025, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

import isaaclab.sim as sim_utils
from isaaclab.assets import ArticulationCfg, AssetBaseCfg
from isaaclab.envs import ManagerBasedRLEnvCfg
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
        history_length=1,
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
    """Configuration for events."""

    reset_scene = EventTerm(func=mdp.reset_scene_to_default, mode="reset")


@configclass
class RewardsCfg:
    """Reward terms for the MDP."""

    # (1) Constant running reward
    alive = RewTerm(func=mdp.is_alive, weight=1.0)
    # (2) Failure penalty
    terminating = RewTerm(func=mdp.is_terminated, weight=-2.0)


@configclass
class TerminationsCfg:
    """Termination terms for the MDP."""

    # (1) Time out
    time_out = DoneTerm(func=mdp.time_out, time_out=True)


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
    events: EventCfg = EventCfg()
    # MDP settings
    rewards: RewardsCfg = RewardsCfg()
    terminations: TerminationsCfg = TerminationsCfg()

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
