"""Deterministic camera geometry for Isaac evaluation videos."""

from __future__ import annotations

import math
from collections.abc import Sequence

CAMERA_WORLD_EYE_OFFSET = (0.0, -2.4, 0.57)
CAMERA_FOV_SCALE = 1.3
MAX_HORIZONTAL_FOV_DEG = 150.0


def translated_follow_view(
    root_position: Sequence[float],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Return a camera view that follows translation without following root rotation."""
    if len(root_position) != 3:
        raise ValueError(f"root_position must contain 3 values, got {len(root_position)}")
    target = tuple(float(value) for value in root_position)
    eye = tuple(value + offset for value, offset in zip(target, CAMERA_WORLD_EYE_OFFSET, strict=True))
    return eye, target


def widened_focal_length(
    horizontal_aperture: float,
    focal_length: float,
    fov_scale: float = CAMERA_FOV_SCALE,
) -> tuple[float, float, float]:
    """Return focal length and old/new horizontal FOV values in degrees."""
    if horizontal_aperture <= 0.0 or focal_length <= 0.0:
        raise ValueError("horizontal_aperture and focal_length must be positive")
    if fov_scale <= 0.0:
        raise ValueError("fov_scale must be positive")
    current_fov = 2.0 * math.atan(horizontal_aperture / (2.0 * focal_length))
    target_fov = min(current_fov * fov_scale, math.radians(MAX_HORIZONTAL_FOV_DEG))
    target_focal_length = horizontal_aperture / (2.0 * math.tan(target_fov / 2.0))
    return target_focal_length, math.degrees(current_fov), math.degrees(target_fov)
