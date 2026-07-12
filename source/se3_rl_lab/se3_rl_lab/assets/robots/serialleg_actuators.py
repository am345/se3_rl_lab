# Copyright (c) 2026, SE3 RL Lab contributors.
# SPDX-License-Identifier: BSD-3-Clause

"""Explicit SerialLeg actuator models for Isaac Lab."""

from __future__ import annotations

from itertools import pairwise

import torch

from isaaclab.actuators import IdealPDActuator, IdealPDActuatorCfg
from isaaclab.utils import configclass
from isaaclab.utils.types import ArticulationActions


class TorqueSpeedCurveActuator(IdealPDActuator):
    """PD actuator clipped by a piecewise-linear ``abs(speed) -> torque`` envelope."""

    cfg: TorqueSpeedCurveActuatorCfg

    def __init__(self, cfg: TorqueSpeedCurveActuatorCfg, *args, **kwargs) -> None:
        super().__init__(cfg, *args, **kwargs)
        curve = torch.tensor(cfg.torque_speed_curve, dtype=torch.float, device=self.computed_effort.device)
        self._curve_speed = curve[:, 0].contiguous()
        self._curve_torque = curve[:, 1].contiguous()
        self._joint_vel = torch.zeros_like(self.computed_effort)

    def compute(
        self,
        control_action: ArticulationActions,
        joint_pos: torch.Tensor,
        joint_vel: torch.Tensor,
    ) -> ArticulationActions:
        self._joint_vel.copy_(joint_vel)
        return super().compute(control_action, joint_pos, joint_vel)

    def _clip_effort(self, effort: torch.Tensor) -> torch.Tensor:
        speed = torch.abs(self._joint_vel).contiguous()
        upper = torch.searchsorted(self._curve_speed, speed).clamp(
            min=1,
            max=self._curve_speed.numel() - 1,
        )
        lower = upper - 1
        speed_lower = self._curve_speed[lower]
        speed_upper = self._curve_speed[upper]
        torque_lower = self._curve_torque[lower]
        torque_upper = self._curve_torque[upper]
        ratio = (speed - speed_lower) / (speed_upper - speed_lower)
        torque_limit = torque_lower + ratio * (torque_upper - torque_lower)
        torque_limit = torch.where(speed <= self._curve_speed[0], self._curve_torque[0], torque_limit)
        torque_limit = torch.where(speed >= self._curve_speed[-1], self._curve_torque[-1], torque_limit)
        torque_limit = torch.minimum(torque_limit, self.effort_limit)
        return torch.clamp(effort, min=-torque_limit, max=torque_limit)


@configclass
class TorqueSpeedCurveActuatorCfg(IdealPDActuatorCfg):
    """Configuration for :class:`TorqueSpeedCurveActuator`."""

    class_type: type = TorqueSpeedCurveActuator
    torque_speed_curve: tuple[tuple[float, float], ...] = ()

    def __post_init__(self) -> None:
        if len(self.torque_speed_curve) < 2:
            raise ValueError("torque_speed_curve must contain at least two points")
        speeds = [float(point[0]) for point in self.torque_speed_curve]
        torques = [float(point[1]) for point in self.torque_speed_curve]
        if any(speed < 0.0 for speed in speeds):
            raise ValueError("torque_speed_curve speeds must be non-negative")
        if any(torque < 0.0 for torque in torques):
            raise ValueError("torque_speed_curve torques must be non-negative")
        if any(next_speed <= speed for speed, next_speed in pairwise(speeds)):
            raise ValueError("torque_speed_curve speeds must be strictly increasing")
        if any(next_torque > torque for torque, next_torque in pairwise(torques)):
            raise ValueError("torque_speed_curve torques must be monotonically non-increasing")


__all__ = ["TorqueSpeedCurveActuator", "TorqueSpeedCurveActuatorCfg"]
