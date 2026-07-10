# Copyright (c) 2026, SE3 RL Lab contributors.
# SPDX-License-Identifier: BSD-3-Clause

"""SerialLeg policy action terms."""

from __future__ import annotations

import math
from collections.abc import Sequence

import torch

from isaaclab.managers import ActionTerm, ActionTermCfg
from isaaclab.utils import configclass

from se3_rl_lab.assets.robots.serialleg_contract import SERIALLEG_CONTRACT


def delay_seconds_to_steps(delay_s: float, physics_dt: float) -> int:
    """Quantize a transport delay to the nearest physics step."""
    if physics_dt <= 0.0:
        raise ValueError(f"physics_dt must be positive, got {physics_dt}")
    if delay_s <= 0.0:
        return 0
    return max(0, math.floor(delay_s / physics_dt + 0.5))


class SerialLegDelayedAction(ActionTerm):
    """Delay raw 6D actions, then command four leg positions and two wheel velocities.

    The policy order comes from :data:`SERIALLEG_CONTRACT.policy_joint_order`. The
    first four dimensions retain the legacy closed-chain convention: for each side,
    ``[front_joint, active_tendon_coordinate]``. The final two dimensions are wheel
    velocity commands.
    """

    cfg: SerialLegDelayedActionCfg

    def __init__(self, cfg: SerialLegDelayedActionCfg, env) -> None:
        super().__init__(cfg, env)
        self._joint_names = SERIALLEG_CONTRACT.policy_joint_order
        if len(self._joint_names) != 6:
            raise ValueError(f"SerialLeg action contract must contain 6 joints, got {self._joint_names}")
        self._joint_ids, resolved_names = self._asset.find_joints(list(self._joint_names), preserve_order=True)
        if tuple(resolved_names) != self._joint_names:
            raise ValueError(
                f"SerialLeg action joint order mismatch: expected={self._joint_names} actual={tuple(resolved_names)}"
            )

        self._leg_joint_ids = self._joint_ids[:4]
        self._wheel_joint_ids = self._joint_ids[4:]
        self._raw_actions = torch.zeros(self.num_envs, self.action_dim, device=self.device)
        self._processed_actions = torch.zeros_like(self._raw_actions)
        self._leg_targets = torch.zeros(self.num_envs, 4, device=self.device)
        self._wheel_targets = torch.zeros(self.num_envs, 2, device=self.device)
        self._env_ids = torch.arange(self.num_envs, device=self.device, dtype=torch.long)

        if cfg.leg_scale <= 0.0 or cfg.wheel_scale <= 0.0:
            raise ValueError(f"action scales must be positive, got leg={cfg.leg_scale} wheel={cfg.wheel_scale}")
        if cfg.action_clip is not None and cfg.action_clip <= 0.0:
            raise ValueError(f"action_clip must be positive or None, got {cfg.action_clip}")
        if cfg.action_delay_min_s < 0.0 or cfg.action_delay_max_s < cfg.action_delay_min_s:
            raise ValueError(
                "action delay range must satisfy 0 <= min <= max, got "
                f"[{cfg.action_delay_min_s}, {cfg.action_delay_max_s}]"
            )
        if cfg.action_delay_s < 0.0:
            raise ValueError(f"action_delay_s must be non-negative, got {cfg.action_delay_s}")
        if cfg.active_rod_lower_target_overdrive < 0.0:
            raise ValueError(
                f"active_rod_lower_target_overdrive must be non-negative, got {cfg.active_rod_lower_target_overdrive}"
            )

        physics_dt = float(env.physics_dt)
        if not cfg.action_delay_enabled:
            self._min_delay_steps = self._max_delay_steps = 0
        elif cfg.action_delay_randomize:
            self._min_delay_steps = delay_seconds_to_steps(cfg.action_delay_min_s, physics_dt)
            self._max_delay_steps = delay_seconds_to_steps(cfg.action_delay_max_s, physics_dt)
        else:
            self._min_delay_steps = self._max_delay_steps = delay_seconds_to_steps(cfg.action_delay_s, physics_dt)
        self._delay_steps = torch.zeros(self.num_envs, device=self.device, dtype=torch.long)
        self._action_fifo = torch.zeros(
            self._max_delay_steps + 1,
            self.num_envs,
            self.action_dim,
            device=self.device,
        )

        policy_index = {name: index for index, name in enumerate(self._joint_names[:4])}
        tendon_specs: list[tuple[int, int, float, float, float, float, float]] = []
        for tendon in SERIALLEG_CONTRACT.fixed_tendons.values():
            if any(name not in policy_index for name in tendon.joint_names):
                raise ValueError(f"fixed tendon {tendon.name} does not map to policy leg joints")
            coefficient_by_index = {
                policy_index[name]: coefficient
                for name, coefficient in zip(tendon.joint_names, tendon.coefficients, strict=True)
            }
            first_index, second_index = sorted(coefficient_by_index)
            if second_index != first_index + 1 or first_index not in (0, 2):
                raise ValueError(f"fixed tendon {tendon.name} violates paired policy order: {tendon.joint_names}")
            first_coefficient = coefficient_by_index[first_index]
            second_coefficient = coefficient_by_index[second_index]
            if second_coefficient == 0.0:
                raise ValueError(f"fixed tendon {tendon.name} has zero second coefficient")
            tendon_specs.append(
                (
                    first_index,
                    second_index,
                    first_coefficient,
                    second_coefficient,
                    0.5 * (tendon.lower + tendon.upper),
                    tendon.lower,
                    tendon.upper,
                )
            )
        self._tendon_specs = tuple(sorted(tendon_specs))
        if len(self._tendon_specs) != 2:
            raise ValueError(f"SerialLeg action contract requires two fixed tendons, got {len(self._tendon_specs)}")
        self._resample_delay(self._env_ids)

    @property
    def action_dim(self) -> int:
        return 6

    @property
    def raw_actions(self) -> torch.Tensor:
        return self._raw_actions

    @property
    def processed_actions(self) -> torch.Tensor:
        return self._processed_actions

    @property
    def delay_steps(self) -> torch.Tensor:
        """Per-environment transport delay measured in physics steps."""
        return self._delay_steps

    @property
    def leg_targets(self) -> torch.Tensor:
        """Most recently applied leg position targets in policy joint order."""
        return self._leg_targets

    @property
    def wheel_targets(self) -> torch.Tensor:
        """Most recently applied wheel velocity targets in policy joint order."""
        return self._wheel_targets

    def process_actions(self, actions: torch.Tensor) -> None:
        if actions.shape != self._raw_actions.shape:
            raise ValueError(f"expected actions with shape {self._raw_actions.shape}, got {actions.shape}")
        incoming = actions.to(device=self.device, dtype=self._raw_actions.dtype)
        if self.cfg.action_clip is None:
            self._raw_actions.copy_(incoming)
        else:
            self._raw_actions.copy_(incoming.clamp(-self.cfg.action_clip, self.cfg.action_clip))

    def apply_actions(self) -> None:
        if self._max_delay_steps > 0:
            self._action_fifo[1:].copy_(self._action_fifo[:-1].clone())
        self._action_fifo[0].copy_(self._raw_actions)
        self._processed_actions.copy_(self._action_fifo[self._delay_steps, self._env_ids])

        defaults = self._asset.data.default_joint_pos[:, self._leg_joint_ids]
        self._leg_targets.copy_(defaults)
        for (
            first_index,
            second_index,
            first_coefficient,
            second_coefficient,
            active_midpoint,
            active_lower,
            active_upper,
        ) in self._tendon_specs:
            front_target = defaults[:, first_index] + self._processed_actions[:, first_index] * self.cfg.leg_scale
            active_target = (active_midpoint + self._processed_actions[:, second_index] * self.cfg.leg_scale).clamp(
                active_lower - self.cfg.active_rod_lower_target_overdrive, active_upper
            )
            self._leg_targets[:, first_index] = front_target
            self._leg_targets[:, second_index] = (active_target - first_coefficient * front_target) / second_coefficient

        default_wheel_vel = self._asset.data.default_joint_vel[:, self._wheel_joint_ids]
        self._wheel_targets.copy_(default_wheel_vel + self._processed_actions[:, 4:6] * self.cfg.wheel_scale)
        self._asset.set_joint_position_target(self._leg_targets, joint_ids=self._leg_joint_ids)
        self._asset.set_joint_velocity_target(self._wheel_targets, joint_ids=self._wheel_joint_ids)

    def reset(self, env_ids: Sequence[int] | slice | torch.Tensor | None = None) -> None:
        resolved = self._resolve_env_ids(env_ids)
        self._raw_actions[resolved] = 0.0
        self._processed_actions[resolved] = 0.0
        self._leg_targets[resolved] = 0.0
        self._wheel_targets[resolved] = 0.0
        self._action_fifo[:, resolved] = 0.0
        self._resample_delay(resolved)

    def _resolve_env_ids(self, env_ids: Sequence[int] | slice | torch.Tensor | None) -> torch.Tensor:
        if env_ids is None:
            return self._env_ids
        if isinstance(env_ids, slice):
            return self._env_ids[env_ids]
        return torch.as_tensor(env_ids, device=self.device, dtype=torch.long)

    def _resample_delay(self, env_ids: torch.Tensor) -> None:
        if env_ids.numel() == 0:
            return
        if self._min_delay_steps == self._max_delay_steps:
            self._delay_steps[env_ids] = self._min_delay_steps
        else:
            self._delay_steps[env_ids] = torch.randint(
                self._min_delay_steps,
                self._max_delay_steps + 1,
                (env_ids.numel(),),
                device=self.device,
            )


@configclass
class SerialLegDelayedActionCfg(ActionTermCfg):
    """Configuration for :class:`SerialLegDelayedAction`."""

    class_type: type[ActionTerm] = SerialLegDelayedAction
    leg_scale: float = 0.25
    wheel_scale: float = 45.0
    action_clip: float | None = 100.0
    action_delay_enabled: bool = True
    action_delay_s: float = 0.005
    action_delay_randomize: bool = True
    action_delay_min_s: float = 0.004
    action_delay_max_s: float = 0.006
    active_rod_lower_target_overdrive: float = 0.20


__all__ = ["SerialLegDelayedAction", "SerialLegDelayedActionCfg", "delay_seconds_to_steps"]
