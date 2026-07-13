# Copyright (c) 2026, SE3 RL Lab contributors.
# SPDX-License-Identifier: BSD-3-Clause

"""Height-conditioned SerialLeg policy defaults shared by reset, actions, and rewards."""

from __future__ import annotations

import math

import torch

from se3_rl_lab.assets.robots.serialleg_contract import SERIALLEG_CONTRACT

_CACHE_POSE_ATTR = "_se3_height_conditioned_policy_default"
_CACHE_HEIGHT_ATTR = "_se3_height_conditioned_policy_default_height"
_LUT_SIZE = 1024
_FOURBAR_LUT_SIZE = 8192
_WHEEL_RADIUS = 0.06
_BASE_COM_X = -0.01780372
_LF1_BODY_XZ = (-0.12990117, 0.04639203)
_LF1_JOINT_XZ = (-0.05003347, -0.04149627)
_WHEEL_BODY_XZ = (-0.15699, -0.21049)
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
_HEIGHT_LUT_CACHE: dict[
    tuple[str, torch.dtype],
    tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor],
] = {}


def _active_limits() -> tuple[float, float]:
    lower = max(tendon.lower for tendon in SERIALLEG_CONTRACT.fixed_tendons.values())
    upper = min(tendon.upper for tendon in SERIALLEG_CONTRACT.fixed_tendons.values())
    return float(lower), float(upper)


def _output_knee_from_active_angle(active: torch.Tensor) -> torch.Tensor:
    """Reference four-bar solution sampled through the same 8192-point LUT."""
    lower, upper = _active_limits()
    alpha_grid = torch.linspace(lower, upper, _FOURBAR_LUT_SIZE, device=active.device, dtype=active.dtype)
    beta = -alpha_grid
    px = torch.cos(beta) * _DRIVE_X + torch.sin(beta) * _DRIVE_Z
    pz = -torch.sin(beta) * _DRIVE_X + torch.cos(beta) * _DRIVE_Z
    dx = px - _KNEE_X
    dz = pz - _KNEE_Z
    distance = torch.sqrt(torch.clamp(dx * dx + dz * dz, min=1.0e-12))
    ex = dx / distance
    ez = dz / distance
    along = (_CALF_LEN**2 - _COUPLER_LEN**2 + distance * distance) / (2.0 * distance)
    offset = torch.sqrt(torch.clamp(_CALF_LEN**2 - along * along, min=0.0))
    cx = _KNEE_X + along * ex - offset * ez
    cz = _KNEE_Z + along * ez + offset * ex
    knee_grid = torch.atan2(
        torch.sin(_CALF_ZERO_ANGLE - torch.atan2(cz - _KNEE_Z, cx - _KNEE_X)),
        torch.cos(_CALF_ZERO_ANGLE - torch.atan2(cz - _KNEE_Z, cx - _KNEE_X)),
    )
    return _interp_monotonic(active, alpha_grid, knee_grid)


def _leg_vector(output_knee: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    body = output_knee.new_tensor(_LF1_BODY_XZ)
    joint = output_knee.new_tensor(_LF1_JOINT_XZ)
    wheel = output_knee.new_tensor(_WHEEL_BODY_XZ)
    cos_q = torch.cos(output_knee)
    sin_q = torch.sin(output_knee)
    rot_joint_x = cos_q * joint[0] + sin_q * joint[1]
    rot_joint_z = -sin_q * joint[0] + cos_q * joint[1]
    rot_wheel_x = cos_q * wheel[0] + sin_q * wheel[1]
    rot_wheel_z = -sin_q * wheel[0] + cos_q * wheel[1]
    return (
        body[0] + joint[0] - rot_joint_x + rot_wheel_x,
        body[1] + joint[1] - rot_joint_z + rot_wheel_z,
    )


def _height_lut(device: torch.device, dtype: torch.dtype):
    key = (str(device), dtype)
    cached = _HEIGHT_LUT_CACHE.get(key)
    if cached is not None:
        return cached
    lower, upper = _active_limits()
    active = torch.linspace(lower, upper, _LUT_SIZE, device=device, dtype=dtype)
    output_knee = _output_knee_from_active_angle(active)
    vec_x, vec_z = _leg_vector(output_knee)
    length = torch.sqrt(torch.clamp(vec_x * vec_x + vec_z * vec_z, min=1.0e-12))
    order = torch.argsort(length)
    cached = (active[order], length[order], active, vec_x, vec_z)
    _HEIGHT_LUT_CACHE[key] = cached
    return cached


def _interp_monotonic(x: torch.Tensor, xp: torch.Tensor, fp: torch.Tensor) -> torch.Tensor:
    x = torch.clamp(x, min=xp[0], max=xp[-1])
    index = torch.searchsorted(xp, x, right=True).clamp(1, xp.numel() - 1)
    x0, x1 = xp[index - 1], xp[index]
    y0, y1 = fp[index - 1], fp[index]
    ratio = (x - x0) / torch.clamp(x1 - x0, min=1.0e-12)
    return y0 + ratio * (y1 - y0)


def policy_default_from_height(command_height: torch.Tensor) -> torch.Tensor:
    """Return policy-order ``[lf0, l_drive_bar, rf0, r_drive_bar]`` defaults."""
    height = command_height.reshape(-1).to(dtype=torch.float32)
    active_by_length, length_grid, active_grid, vec_x_grid, vec_z_grid = _height_lut(height.device, height.dtype)
    target_x = torch.full_like(height, _BASE_COM_X)
    target_z = height.new_tensor(_WHEEL_RADIUS) - height
    target_length = torch.sqrt(target_x * target_x + target_z * target_z).clamp(min=length_grid[0], max=length_grid[-1])
    active = _interp_monotonic(target_length, length_grid, active_by_length)
    vec_x = _interp_monotonic(active, active_grid, vec_x_grid)
    vec_z = _interp_monotonic(active, active_grid, vec_z_grid)
    lf = torch.atan2(vec_x, -vec_z) - torch.atan2(target_x, -target_z)
    rf = -lf
    return torch.stack((lf, lf - active, rf, rf + active), dim=1)


def update_height_default_cache(
    env,
    command_name: str,
    env_ids: torch.Tensor | None = None,
    command: torch.Tensor | None = None,
) -> torch.Tensor:
    """Update the per-environment default from the current command height."""
    command = env.command_manager.get_command(command_name) if command is None else command
    if command.ndim != 2 or command.shape[1] <= 4:
        raise ValueError(f"{command_name} must expose height at column 4, got {tuple(command.shape)}")
    heights = command[:, 4].detach()
    cache = getattr(env, _CACHE_POSE_ATTR, None)
    height_cache = getattr(env, _CACHE_HEIGHT_ATTR, None)
    invalid = not isinstance(cache, torch.Tensor) or cache.shape != (env.num_envs, 4) or cache.device != heights.device
    height_invalid = (
        not isinstance(height_cache, torch.Tensor)
        or height_cache.shape != (env.num_envs,)
        or height_cache.device != heights.device
    )
    if invalid or height_invalid:
        cache = policy_default_from_height(heights)
        height_cache = heights.clone()
        setattr(env, _CACHE_POSE_ATTR, cache)
        setattr(env, _CACHE_HEIGHT_ATTR, height_cache)
        return cache
    ids = torch.arange(env.num_envs, device=heights.device) if env_ids is None else env_ids.to(heights.device)
    cache[ids] = policy_default_from_height(heights[ids])
    height_cache[ids] = heights[ids]
    return cache


def get_height_default(env, command_name: str, *, device, dtype) -> torch.Tensor:
    cache = getattr(env, _CACHE_POSE_ATTR, None)
    if not isinstance(cache, torch.Tensor) or cache.shape != (env.num_envs, 4) or cache.device != torch.device(device):
        cache = update_height_default_cache(env, command_name)
    return cache.to(device=device, dtype=dtype)


__all__ = ["get_height_default", "policy_default_from_height", "update_height_default_cache"]
