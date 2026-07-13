"""Pure reward kernels shared by runtime reward terms and regression tests."""

from __future__ import annotations

import torch


def angular_tracking_reward(
    error: torch.Tensor,
    command: torch.Tensor,
    gate: torch.Tensor,
    *,
    sigma: float,
    sigma_cmd_scale: float,
    ratio_blend: float,
) -> torch.Tensor:
    """Blend exponential precision with a directional large-error yaw signal."""
    command_magnitude = torch.abs(command)
    effective_sigma = float(sigma) * (1.0 + float(sigma_cmd_scale) * command_magnitude)
    exponential_reward = torch.exp(-(error**2) / effective_sigma) * gate

    blend = min(max(float(ratio_blend), 0.0), 1.0)
    if blend == 0.0:
        return exponential_reward

    ratio_denominator = torch.clamp(command_magnitude, min=1.0)
    ratio_reward = torch.clamp(1.0 - torch.abs(error) / ratio_denominator, 0.0, 1.0) * gate
    return (1.0 - blend) * exponential_reward + blend * ratio_reward
