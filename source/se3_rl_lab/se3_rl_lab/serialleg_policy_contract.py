"""Lightweight SerialLeg policy I/O constants shared by runtime and deployment tools."""

ACTOR_OBSERVATION_DIM = 34
CRITIC_OBSERVATION_DIM = 40
RECOVERY_OBSERVATION_HISTORY_LENGTH = 5
RECOVERY_COMMAND_OBSERVATION_DIM = 8
RECOVERY_PROPRIOCEPTION_OBSERVATION_DIM = 26
RECOVERY_PRIVILEGED_PROPRIOCEPTION_DIM = 32
RECOVERY_ACTOR_OBSERVATION_DIM = (
    RECOVERY_COMMAND_OBSERVATION_DIM
    + RECOVERY_PROPRIOCEPTION_OBSERVATION_DIM * RECOVERY_OBSERVATION_HISTORY_LENGTH
)
RECOVERY_CRITIC_OBSERVATION_DIM = (
    RECOVERY_COMMAND_OBSERVATION_DIM
    + RECOVERY_PRIVILEGED_PROPRIOCEPTION_DIM * RECOVERY_OBSERVATION_HISTORY_LENGTH
)
OBSERVATION_CLIP = 100.0
COMMAND_SCALE = (2.0, 0.25, 5.0, 5.0, 5.0)

ACTOR_OBSERVATION_LAYOUT = {
    "base_ang_vel": slice(0, 3),
    "projected_gravity": slice(3, 6),
    "commands": slice(6, 11),
    "leg_joint_pos": slice(11, 17),
    "leg_joint_vel": slice(17, 21),
    "wheel_pos_zero": slice(21, 23),
    "wheel_vel": slice(23, 25),
    "last_actions": slice(25, 31),
    "jump_commands": slice(31, 34),
}
CRITIC_PRIVILEGED_LAYOUT = {
    "base_lin_vel": slice(34, 37),
    "wheel_contact_forces": slice(37, 39),
    "base_height": slice(39, 40),
}

RECOVERY_COMMAND_LAYOUT = {
    "commands": slice(0, 5),
    "jump_commands": slice(5, 8),
}
RECOVERY_PROPRIOCEPTION_TERM_DIMS = {
    "base_ang_vel": 3,
    "projected_gravity": 3,
    "leg_joint_pos": 6,
    "leg_joint_vel": 4,
    "wheel_pos_zero": 2,
    "wheel_vel": 2,
    "last_actions": 6,
}
RECOVERY_PROPRIOCEPTION_LAYOUT = {
    "base_ang_vel": slice(0, 15),
    "projected_gravity": slice(15, 30),
    "leg_joint_pos": slice(30, 60),
    "leg_joint_vel": slice(60, 80),
    "wheel_pos_zero": slice(80, 90),
    "wheel_vel": slice(90, 100),
    "last_actions": slice(100, 130),
}
RECOVERY_PRIVILEGED_TERM_DIMS = {
    **RECOVERY_PROPRIOCEPTION_TERM_DIMS,
    "base_lin_vel": 3,
    "wheel_contact_forces": 2,
    "base_height": 1,
}
RECOVERY_PRIVILEGED_LAYOUT = {
    **RECOVERY_PROPRIOCEPTION_LAYOUT,
    "base_lin_vel": slice(130, 145),
    "wheel_contact_forces": slice(145, 155),
    "base_height": slice(155, 160),
}
RECOVERY_OBSERVATION_GROUP_DIMS = {
    "command": RECOVERY_COMMAND_OBSERVATION_DIM,
    "proprio": RECOVERY_PROPRIOCEPTION_OBSERVATION_DIM * RECOVERY_OBSERVATION_HISTORY_LENGTH,
    "privileged": RECOVERY_PRIVILEGED_PROPRIOCEPTION_DIM * RECOVERY_OBSERVATION_HISTORY_LENGTH,
}

__all__ = [name for name in globals() if name.isupper()]
