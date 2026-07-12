# Copyright (c) 2026, SE3 RL Lab contributors.
# SPDX-License-Identifier: BSD-3-Clause

"""SerialLeg output-shaft motor specifications shared by simulation backends."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class MotorSpec:
    """Output-shaft DC motor parameters and torque-speed envelope."""

    name: str
    rated_voltage: float
    gear_ratio: float
    stall_torque: float
    no_load_speed: float
    rated_torque: float
    rated_current: float
    stall_current: float
    phase_resistance: float
    torque_speed_curve: tuple[tuple[float, float], ...] = ()

    @property
    def no_load_speed_rpm(self) -> float:
        """Return output-shaft no-load speed in revolutions per minute."""

        return self.no_load_speed * 60.0 / (2.0 * math.pi)

    @property
    def rotor_kt(self) -> float:
        """Return the approximate rotor-side torque constant in N m/A."""

        return self.stall_torque / (self.stall_current * self.gear_ratio)

    @property
    def rotor_ke(self) -> float:
        """Return the approximate rotor-side back-EMF constant in V s/rad."""

        return self.rated_voltage / (self.no_load_speed * self.gear_ratio)

    def torque_limit_np(self, velocity: np.ndarray | float) -> np.ndarray:
        """Return the available output torque magnitude at ``velocity``."""

        speed = np.abs(np.asarray(velocity, dtype=np.float64))
        if self.torque_speed_curve:
            curve = np.asarray(self.torque_speed_curve, dtype=np.float64)
            return np.interp(
                speed,
                curve[:, 0],
                curve[:, 1],
                left=float(curve[0, 1]),
                right=float(curve[-1, 1]),
            )

        vel_at_effort_limit = self.no_load_speed * (1.0 + self.rated_torque / self.stall_torque)
        speed_clipped = np.clip(speed, 0.0, vel_at_effort_limit)
        return np.minimum(
            self.stall_torque * (1.0 - speed_clipped / self.no_load_speed),
            self.rated_torque,
        ).clip(min=0.0)

    def clip_effort_np(
        self,
        effort: np.ndarray | float,
        velocity: np.ndarray | float,
    ) -> np.ndarray:
        """Clip output torque against the motor's four-quadrant envelope."""

        effort_arr = np.asarray(effort, dtype=np.float64)
        if self.torque_speed_curve:
            limit = self.torque_limit_np(velocity)
            return np.clip(effort_arr, -limit, limit)

        velocity_arr = np.asarray(velocity, dtype=np.float64)
        vel_at_effort_limit = self.no_load_speed * (1.0 + self.rated_torque / self.stall_torque)
        vel_clipped = np.clip(velocity_arr, -vel_at_effort_limit, vel_at_effort_limit)
        top = self.stall_torque * (1.0 - vel_clipped / self.no_load_speed)
        bottom = self.stall_torque * (-1.0 - vel_clipped / self.no_load_speed)
        return np.clip(
            effort_arr,
            np.maximum(bottom, -self.rated_torque),
            np.minimum(top, self.rated_torque),
        )


# Digitized C620 current-loop load characteristic mapped from 19:1 to the
# wheel's 14:1 reduction. Values are expressed at the gearbox output shaft.
M3508_C620_14_TORQUE_SPEED_CURVE: tuple[tuple[float, float], ...] = (
    (0.00, 3.71),
    (32.93, 3.71),
    (49.07, 3.61),
    (57.82, 3.54),
    (63.65, 3.46),
    (65.29, 3.39),
    (65.70, 3.32),
    (67.43, 2.95),
    (69.28, 2.21),
    (70.90, 1.47),
    (71.37, 0.74),
    (71.81, 0.00),
)

M3508_C620_14 = MotorSpec(
    name="M3508-C620-14to1",
    rated_voltage=24.0,
    gear_ratio=14.0,
    stall_torque=3.71,
    no_load_speed=71.81,
    rated_torque=3.71,
    rated_current=20.0,
    stall_current=20.0,
    phase_resistance=0.194,
    torque_speed_curve=M3508_C620_14_TORQUE_SPEED_CURVE,
)

DM8009P = MotorSpec(
    name="DM-8009P-2EC",
    rated_voltage=24.0,
    gear_ratio=9.0,
    stall_torque=40.0,
    no_load_speed=160.0 * 2.0 * math.pi / 60.0,
    rated_torque=20.0,
    rated_current=20.0,
    stall_current=50.0,
    phase_resistance=0.145,
)


__all__ = [
    "DM8009P",
    "M3508_C620_14",
    "M3508_C620_14_TORQUE_SPEED_CURVE",
    "MotorSpec",
]
