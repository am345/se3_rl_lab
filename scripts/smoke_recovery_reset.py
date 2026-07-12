#!/usr/bin/env python3
"""Runtime gate for recovery dataset remap and closure-consistent joint reset."""

from __future__ import annotations

import argparse

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--num-envs", type=int, default=64)
parser.add_argument("--iteration", type=int, default=2000)
parser.add_argument("--steps", type=int, default=16)
parser.add_argument("--action-std", type=float, default=0.0)
parser.add_argument("--checkpoint", type=str, default=None)
AppLauncher.add_app_launcher_args(parser)
parser.set_defaults(headless=True, device="cuda:0")
ARGS = parser.parse_args()
APP = AppLauncher(ARGS, fast_shutdown=True).app

import gymnasium as gym  # noqa: E402
import se3_rl_lab.tasks  # noqa: F401, E402
import torch  # noqa: E402
from se3_rl_lab.assets.robots.serialleg_contract import SERIALLEG_CONTRACT  # noqa: E402
from se3_rl_lab.tasks.manager_based.se3_rl_lab.mdp.fourbar_reset import (  # noqa: E402
    policy_to_passive_pos,
)
from se3_rl_lab.tasks.manager_based.se3_rl_lab.mdp.recovery_events import (  # noqa: E402
    RECOVERY_PASSIVE_JOINTS,
)

from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402


def main() -> None:
    cfg = parse_env_cfg("SerialLeg-Recovery-v0", device=ARGS.device, num_envs=ARGS.num_envs, use_fabric=True)
    env = gym.make("SerialLeg-Recovery-v0", cfg=cfg)
    unwrapped = env.unwrapped
    unwrapped.common_step_counter = int(ARGS.iteration) * 24
    observations, _ = env.reset()
    robot = unwrapped.scene["robot"]
    wheel_body_ids, _ = robot.find_bodies(("l_wheel_Link", "r_wheel_Link"), preserve_order=True)
    wheel_pos_w = robot.data.body_link_pos_w[:, wheel_body_ids, :]
    wheel_bottom = wheel_pos_w[:, :, 2] - unwrapped.scene.env_origins[:, 2].unsqueeze(1) - 0.06
    min_wheel_bottom = float(wheel_bottom.min())
    if min_wheel_bottom < 0.0009:
        raise RuntimeError(f"wheel clearance mismatch after reset: {min_wheel_bottom:.6f} m")
    policy_ids, _ = robot.find_joints(list(SERIALLEG_CONTRACT.policy_joint_order[:4]), preserve_order=True)
    passive_ids, _ = robot.find_joints(list(RECOVERY_PASSIVE_JOINTS), preserve_order=True)
    tendon_ids, _ = robot.find_joints(list(SERIALLEG_CONTRACT.tendon_root_joint_names), preserve_order=True)
    cache_mask = unwrapped._recovery_cache_reset_mask
    expected_cache = 0.25 if ARGS.iteration >= 2000 else 0.10 if ARGS.iteration >= 1500 else 0.0
    actual_cache = float(cache_mask.float().mean())
    if expected_cache > 0.0 and not (0.5 * expected_cache <= actual_cache <= 1.5 * expected_cache):
        raise RuntimeError(f"cache ratio mismatch: expected≈{expected_cache} actual={actual_cache}")
    non_cache = ~cache_mask
    if torch.any(non_cache):
        expected_passive = policy_to_passive_pos(robot.data.joint_pos[non_cache][:, policy_ids])
        actual_passive = robot.data.joint_pos[non_cache][:, passive_ids]
        passive_error = float(torch.max(torch.abs(expected_passive - actual_passive)))
        if passive_error > 2.0e-4:
            raise RuntimeError(f"passive reset mismatch: {passive_error:.3e} rad")
    else:
        passive_error = 0.0
    tendon_pos = float(torch.max(torch.abs(robot.data.joint_pos[:, tendon_ids])))
    tendon_vel = float(torch.max(torch.abs(robot.data.joint_vel[:, tendon_ids])))
    if tendon_pos > 1.0e-4 or tendon_vel > 1.0e-4:
        raise RuntimeError(f"tendon-root reset mismatch: pos={tendon_pos:.3e} vel={tendon_vel:.3e}")
    for name, value in observations.items():
        if not torch.isfinite(value).all():
            raise RuntimeError(f"non-finite reset observation group: {name}")
    step_env = env
    policy = None
    if ARGS.checkpoint:
        from rsl_rl.runners import OnPolicyRunner

        from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper

        from isaaclab_tasks.utils import load_cfg_from_registry

        agent_cfg = load_cfg_from_registry("SerialLeg-Recovery-v0", "rsl_rl_cfg_entry_point")
        step_env = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)
        runner = OnPolicyRunner(step_env, agent_cfg.to_dict(), log_dir=None, device=agent_cfg.device)
        runner.load(ARGS.checkpoint)
        policy = runner.get_inference_policy(device=unwrapped.device)
        policy_obs = step_env.get_observations()

    max_reward = 0.0
    for step in range(ARGS.steps):
        if policy is None:
            action = torch.randn((ARGS.num_envs, 6), device=unwrapped.device) * ARGS.action_std
            observations, reward, terminated, truncated, _ = step_env.step(action)
        else:
            with torch.inference_mode():
                action = policy(policy_obs)
            policy_obs, reward, dones, _ = step_env.step(action)
            observations = policy_obs
        if not torch.isfinite(reward).all():
            bad = torch.nonzero(~torch.isfinite(reward), as_tuple=False).flatten()
            raise RuntimeError(f"non-finite reward at step={step} env_ids={bad[:16].tolist()}")
        if any(not torch.isfinite(value).all() for value in observations.values()):
            raise RuntimeError(f"non-finite observation at step={step}")
        max_reward = max(max_reward, float(torch.max(torch.abs(reward))))
    print(
        "[recovery-reset-smoke] "
        f"envs={ARGS.num_envs} iteration={ARGS.iteration} cache_ratio={actual_cache:.3f} "
        f"steps={ARGS.steps} action_std={ARGS.action_std:.3f} "
        f"checkpoint={ARGS.checkpoint or 'none'} "
        f"passive_error={passive_error:.3e} tendon_pos={tendon_pos:.3e} "
        f"tendon_vel={tendon_vel:.3e} max_abs_reward={max_reward:.3f} passed=true"
        f" wheel_clearance_after_min={min_wheel_bottom:.4f}"
    )
    env.close()


if __name__ == "__main__":
    try:
        main()
    finally:
        APP.close()
