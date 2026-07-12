# Copyright (c) 2026, SE3 RL Lab contributors.
# SPDX-License-Identifier: BSD-3-Clause

"""Closed-chain reset kinematics derived from the canonical SerialLeg geometry."""

from __future__ import annotations

import math

import torch

_KNEE_X = -0.17993464
_KNEE_Z = 0.00489576
_CALF_X = 0.05003347
_CALF_Z = 0.04149627
_DRIVE_X = 0.04009536
_DRIVE_Z = 0.04530576
_COUPLER_X = -0.16999653
_COUPLER_Z = 0.00108627
_COUPLER_LEN = math.hypot(_COUPLER_X, _COUPLER_Z)
_CALF_LEN = math.hypot(_CALF_X, _CALF_Z)
_CALF_ZERO_ANGLE = math.atan2(_CALF_Z, _CALF_X)


def _wrap(value: torch.Tensor) -> torch.Tensor:
    return torch.atan2(torch.sin(value), torch.cos(value))


def _passive_left(active_angle: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Return left output-knee and coupler angles for an active-rod angle."""
    alpha = active_angle.clamp(0.0, math.radians(129.95 - 43.46))
    beta = -alpha
    cos_b = torch.cos(beta)
    sin_b = torch.sin(beta)
    px = cos_b * _DRIVE_X + sin_b * _DRIVE_Z
    pz = -sin_b * _DRIVE_X + cos_b * _DRIVE_Z
    dx = px - _KNEE_X
    dz = pz - _KNEE_Z
    distance = torch.sqrt((dx * dx + dz * dz).clamp_min(1.0e-12))
    ex = dx / distance
    ez = dz / distance
    along = (_CALF_LEN**2 - _COUPLER_LEN**2 + distance * distance) / (2.0 * distance)
    height = torch.sqrt((_CALF_LEN**2 - along * along).clamp_min(0.0))
    cx = _KNEE_X + along * ex - height * ez
    cz = _KNEE_Z + along * ez + height * ex
    knee = _wrap(active_angle.new_tensor(_CALF_ZERO_ANGLE) - torch.atan2(cz - _KNEE_Z, cx - _KNEE_X))
    coupler_local = active_angle.new_tensor(math.atan2(_COUPLER_Z, _COUPLER_X))
    coupler_world = torch.atan2(cz - pz, cx - px)
    coupler = _wrap(coupler_local - coupler_world - beta)
    return knee, coupler


def policy_to_passive_pos(policy_pos: torch.Tensor) -> torch.Tensor:
    """Map [LF0, L-drive, RF0, R-drive] to [LF1, L-coupler, RF1, R-coupler]."""
    left_active = policy_pos[:, 0] - policy_pos[:, 1]
    right_active = policy_pos[:, 3] - policy_pos[:, 2]
    left_knee, left_coupler = _passive_left(left_active)
    right_knee, right_coupler = _passive_left(right_active)
    return torch.stack((left_knee, left_coupler, -right_knee, -right_coupler), dim=1)


def policy_to_passive_vel(policy_pos: torch.Tensor, policy_vel: torch.Tensor) -> torch.Tensor:
    """Map policy velocities to passive velocities with numerical kinematic Jacobians."""
    eps = 1.0e-3
    left_lo = policy_pos.clone()
    left_hi = policy_pos.clone()
    left_lo[:, 1] += eps
    left_hi[:, 1] -= eps
    right_lo = policy_pos.clone()
    right_hi = policy_pos.clone()
    right_lo[:, 3] -= eps
    right_hi[:, 3] += eps
    left_j = (policy_to_passive_pos(left_hi)[:, :2] - policy_to_passive_pos(left_lo)[:, :2]) / (2.0 * eps)
    right_j = (policy_to_passive_pos(right_hi)[:, 2:] - policy_to_passive_pos(right_lo)[:, 2:]) / (2.0 * eps)
    left_rate = (policy_vel[:, 0] - policy_vel[:, 1]).unsqueeze(1)
    right_rate = (policy_vel[:, 3] - policy_vel[:, 2]).unsqueeze(1)
    return torch.cat((left_j * left_rate, right_j * right_rate), dim=1)


__all__ = ["policy_to_passive_pos", "policy_to_passive_vel"]
