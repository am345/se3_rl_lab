# Copyright (c) 2026, SE3 RL Lab contributors.
# SPDX-License-Identifier: BSD-3-Clause

"""Non-jumping SerialLeg velocity/height command terms."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import MISSING
from typing import TYPE_CHECKING

import torch

from isaaclab.assets import Articulation
from isaaclab.managers import CommandTerm, CommandTermCfg
from isaaclab.utils import configclass

if TYPE_CHECKING:
    from isaaclab.envs import ManagerBasedRLEnv


class VelocityHeightCommand(CommandTerm):
    """Sample the strict legacy-compatible 8D flat command.

    The layout is ``[vx, yaw_rate, pitch, roll, height, jump, jump_height,
    jump_phase]``.  This migration stage is deliberately non-jumping, so the
    final three fields remain exactly zero for the lifetime of the term.
    """

    cfg: VelocityHeightCommandCfg

    def __init__(self, cfg: VelocityHeightCommandCfg, env: ManagerBasedRLEnv):
        super().__init__(cfg, env)
        self.robot: Articulation = env.scene[cfg.asset_name]
        self._command = torch.zeros((self.num_envs, 8), device=self.device)
        self._standing = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        self.metrics["error_vel_x"] = torch.zeros(self.num_envs, device=self.device)
        self.metrics["error_vel_yaw"] = torch.zeros(self.num_envs, device=self.device)
        self._validate_cfg()

    @property
    def command(self) -> torch.Tensor:
        """The strict 8D command tensor."""
        return self._command

    def _validate_cfg(self) -> None:
        ranges = {
            "lin_vel_x_range": self.cfg.lin_vel_x_range,
            "ang_vel_yaw_range": self.cfg.ang_vel_yaw_range,
            "pitch_range": self.cfg.pitch_range,
            "roll_range": self.cfg.roll_range,
            "height_range": self.cfg.height_range,
            "standing_height_range": self.cfg.standing_height_range,
        }
        invalid = {name: value for name, value in ranges.items() if value[0] > value[1]}
        if invalid:
            raise ValueError(f"velocity_height ranges must be ordered: {invalid}")
        if not 0.0 <= self.cfg.standing_ratio <= 1.0:
            raise ValueError(f"standing_ratio must be in [0, 1], got {self.cfg.standing_ratio}")
        positive = {
            "diff_drive_wheel_radius": self.cfg.diff_drive_wheel_radius,
            "diff_drive_half_track": self.cfg.diff_drive_half_track,
            "diff_drive_max_wheel_speed": self.cfg.diff_drive_max_wheel_speed,
            "diff_drive_wheel_speed_fraction": self.cfg.diff_drive_wheel_speed_fraction,
        }
        invalid_positive = {name: value for name, value in positive.items() if value <= 0.0}
        if invalid_positive:
            raise ValueError(f"differential-drive parameters must be positive: {invalid_positive}")

    def _update_metrics(self) -> None:
        max_command_steps = self.cfg.resampling_time_range[1] / self._env.step_dt
        self.metrics["error_vel_x"] += (
            torch.abs(self._command[:, 0] - self.robot.data.root_lin_vel_b[:, 0]) / max_command_steps
        )
        self.metrics["error_vel_yaw"] += (
            torch.abs(self._command[:, 1] - self.robot.data.root_ang_vel_b[:, 2]) / max_command_steps
        )

    def _resample_command(self, env_ids: Sequence[int]) -> None:
        env_ids = torch.as_tensor(env_ids, dtype=torch.long, device=self.device)
        count = int(env_ids.numel())
        if count == 0:
            return

        self._command[env_ids] = 0.0
        self._standing[env_ids] = torch.rand(count, device=self.device) < self.cfg.standing_ratio
        standing_ids = env_ids[self._standing[env_ids]]
        moving_ids = env_ids[~self._standing[env_ids]]

        if standing_ids.numel() > 0:
            self._command[standing_ids, 4] = self._sample_uniform(
                int(standing_ids.numel()), self.cfg.standing_height_range
            )

        if moving_ids.numel() > 0:
            moving_count = int(moving_ids.numel())
            lin_vel = self._sample_uniform(moving_count, self.cfg.lin_vel_x_range)
            yaw_vel = self._sample_uniform(moving_count, self.cfg.ang_vel_yaw_range)
            lin_vel, yaw_vel = self._constrain_diff_drive(lin_vel, yaw_vel)
            self._command[moving_ids, 0] = lin_vel
            self._command[moving_ids, 1] = yaw_vel
            self._command[moving_ids, 2] = self._sample_uniform(moving_count, self.cfg.pitch_range)
            self._command[moving_ids, 3] = self._sample_uniform(moving_count, self.cfg.roll_range)
            self._command[moving_ids, 4] = self._sample_uniform(moving_count, self.cfg.height_range)

    def _sample_uniform(self, count: int, value_range: tuple[float, float]) -> torch.Tensor:
        return torch.empty(count, device=self.device).uniform_(*value_range)

    def _constrain_diff_drive(self, lin_vel: torch.Tensor, yaw_vel: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        if not self.cfg.constrain_diff_drive_commands:
            return lin_vel, yaw_vel

        budget = (
            self.cfg.diff_drive_wheel_radius
            * self.cfg.diff_drive_max_wheel_speed
            * self.cfg.diff_drive_wheel_speed_fraction
        )
        half_track = self.cfg.diff_drive_half_track
        lin_vel = lin_vel.clamp(-budget, budget)
        lower = torch.maximum(
            torch.full_like(lin_vel, self.cfg.ang_vel_yaw_range[0]),
            torch.maximum((-budget - lin_vel) / half_track, (lin_vel - budget) / half_track),
        )
        upper = torch.minimum(
            torch.full_like(lin_vel, self.cfg.ang_vel_yaw_range[1]),
            torch.minimum((budget - lin_vel) / half_track, (lin_vel + budget) / half_track),
        )
        yaw_vel = lower + torch.rand_like(yaw_vel) * (upper - lower).clamp_min(0.0)
        return lin_vel, yaw_vel

    def _update_command(self) -> None:
        moving = ~self._standing
        self._command[:, 0] = torch.where(
            moving & (self._command[:, 0].abs() < self.cfg.lin_vel_deadband),
            torch.zeros_like(self._command[:, 0]),
            self._command[:, 0],
        )
        self._command[:, 1] = torch.where(
            moving & (self._command[:, 1].abs() < self.cfg.yaw_deadband),
            torch.zeros_like(self._command[:, 1]),
            self._command[:, 1],
        )
        self._command[:, 5:8] = 0.0


@configclass
class VelocityHeightCommandCfg(CommandTermCfg):
    """Configuration for :class:`VelocityHeightCommand`."""

    class_type: type = VelocityHeightCommand
    asset_name: str = MISSING
    lin_vel_x_range: tuple[float, float] = (-0.4, 0.4)
    ang_vel_yaw_range: tuple[float, float] = (-1.0, 1.0)
    pitch_range: tuple[float, float] = (0.0, 0.0)
    roll_range: tuple[float, float] = (0.0, 0.0)
    height_range: tuple[float, float] = (0.20, 0.32)
    standing_height_range: tuple[float, float] = (0.20, 0.32)
    lin_vel_deadband: float = 0.1
    yaw_deadband: float = 0.1
    standing_ratio: float = 0.1
    constrain_diff_drive_commands: bool = True
    diff_drive_wheel_radius: float = 0.06
    diff_drive_half_track: float = 0.20
    diff_drive_max_wheel_speed: float = 45.0
    diff_drive_wheel_speed_fraction: float = 0.9


class PlanarVelocityCommand(CommandTerm):
    """Expose an official locomotion-compatible ``[vx, vy, yaw]`` view."""

    cfg: PlanarVelocityCommandCfg

    @property
    def command(self) -> torch.Tensor:
        source = self._env.command_manager.get_command(self.cfg.source_command_name)
        if source.ndim != 2 or source.shape != (self.num_envs, 8):
            raise ValueError(
                f"{self.cfg.source_command_name} must have shape ({self.num_envs}, 8), got {tuple(source.shape)}"
            )
        return torch.stack((source[:, 0], torch.zeros_like(source[:, 0]), source[:, 1]), dim=1)

    def _update_metrics(self) -> None:
        pass

    def _resample_command(self, env_ids: Sequence[int]) -> None:
        pass

    def _update_command(self) -> None:
        pass


@configclass
class PlanarVelocityCommandCfg(CommandTermCfg):
    """Configuration for the derived official-reward command view."""

    class_type: type = PlanarVelocityCommand
    source_command_name: str = "velocity_height"

    def __post_init__(self) -> None:
        self.resampling_time_range = (5.0, 5.0)
