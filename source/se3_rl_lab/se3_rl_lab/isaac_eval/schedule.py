"""Deterministic scheduling helpers for fixed-command Isaac evaluations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvaluationTiming:
    """Durations applied to a fixed-command evaluation rollout."""

    total_duration_s: float
    protected_duration_s: float


def configure_fixed_command_eval(
    env_cfg: Any,
    *,
    scenario_count: int,
    scenario_duration_s: float,
    guard_duration_s: float = 1.0,
) -> EvaluationTiming:
    """Keep timeout and command resampling outside the complete eval rollout."""
    if scenario_count <= 0:
        raise ValueError("scenario_count must be positive")
    if scenario_duration_s <= 0.0:
        raise ValueError("scenario_duration_s must be positive")
    if guard_duration_s <= 0.0:
        raise ValueError("guard_duration_s must be positive")

    total_duration_s = scenario_count * scenario_duration_s
    protected_duration_s = total_duration_s + guard_duration_s
    env_cfg.episode_length_s = max(float(env_cfg.episode_length_s), protected_duration_s)
    env_cfg.commands.velocity_height.resampling_time_range = (
        protected_duration_s,
        protected_duration_s,
    )
    return EvaluationTiming(
        total_duration_s=total_duration_s,
        protected_duration_s=protected_duration_s,
    )


def set_command_and_refresh_observations(
    env: Any,
    unwrapped_env: Any,
    *,
    vx: float,
    yaw_rate: float,
    height: float,
) -> Any:
    """Apply one scenario command before producing its first policy observation."""
    term = unwrapped_env.command_manager.get_term("velocity_height")
    term._command[:, :] = 0.0
    term._command[:, 0] = vx
    term._command[:, 1] = yaw_rate
    term._command[:, 4] = height
    refresh_height_default = getattr(term, "refresh_height_default_cache", None)
    if callable(refresh_height_default):
        refresh_height_default()
    return env.get_observations()
