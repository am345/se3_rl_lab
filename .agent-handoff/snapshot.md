# Handoff Snapshot

## Current State

- Last updated: 2026-07-10
- Last agent: Codex
- Workspace root: `/home/am345/se3_rl_lab`
- Current objective: 迁移 SerialLeg flat 的非跳跃基础训练链路，先用 IsaacLab 官方 locomotion rewards 验证 Isaac Sim 行为，再在 finetune 阶段适配自定义奖励。
- Current status: delayed 6D action 与 34D/40D observation 已实现、验证并通过 PR #4 squash merge。下一阶段只接入官方基础 locomotion rewards，旧 flat 自定义奖励推迟到 finetune，jump command 默认关闭。依赖配置已改为 portable sibling paths `../IsaacLab/source/...`，真实 `uv sync --locked` 与 AppLauncher task registry probe 均通过。handoff 文档已取消 ignore 并纳入仓库版本控制，支持跨电脑恢复。
- Delayed-action contract: action order 由 `SERIALLEG_CONTRACT.policy_joint_order` 派生；腿为 position target、scale `0.25 rad`，轮为 velocity target、scale `45 rad/s`。每侧 action 使用 `[front joint, active tendon coordinate]`，右侧 tendon coefficients 已按 policy order 重排为 `(-1,+1)`；active target clamp 为 `[lower-0.20, upper]`。
- Delay/reset contract: 默认 `4–6 ms` 在 `physics_dt=0.005 s` 下逐环境量化为 1 physics step；FIFO 在 physics step 更新，partial reset 只清目标 env 的 raw/delayed/FIFO 并重采样 delay。
- Observation contract: actor 精确 34D、critic 为 actor 34D + privileged 6D = 40D；显式只索引 4 policy leg + 2 wheel joints，passive 与 virtual-root joints 不进入 policy observation。布局和 scale 位于 `mdp/observations.py`。
- Transitional command behavior: `velocity_height` 尚未迁移时，command 5D + jump 3D 明确输出零；接入后仍严格要求 `[num_envs,8]`，但当前阶段 jump command 默认关闭，末 3D 保持零。
- Reward migration decision: 基础验收阶段只配置 IsaacLab 官方 manager-based locomotion rewards，不迁移旧 flat 自定义奖励；command-driven 高度、分段/联合跟踪、轮腿专属 penalty/gating 等统一推迟到 finetune。
- Command normalization decision: 当前继续保留旧 observation scale `(2.0, 0.25, 5.0, 5.0, 5.0)` 以维持 legacy policy/checkpoint 接口；是否按最终 command range 做中心化归一化已推迟到 finetune 阶段，列为低优先级，不阻塞当前迁移。
- Validation: Ruff/diff check 通过；`scripts/test_serialleg_observations.py` 为 `4 passed`；CPU 1-env 8+8 task smoke 和 compact-CUDA 1-env 2+2 task smoke 均退出 0，实际 observation manager 报 actor `(34,)` / critic `(40,)`，passive effort 为 0。
- Runtime peaks: CPU zero/controlled loop `3.529e-04/2.154e-04 m`；compact CUDA `3.487e-04/2.059e-04 m`，均低于 task `1e-3 m` gate。
- Active files: `.gitignore`、`README.md`、`pyproject.toml`、`uv.lock`、`AGENT_HANDOFF.md`、`AGENT_SESSION_PROMPTS.md`、`.agent-handoff/*.md`。任务源码、资产与环境 cfg 未改。
- Blockers: 无本轮逻辑 blocker。默认 CUDA capacity 仍受并行 Kyber 训练占用约 `5.3 GiB` 影响；本轮只使用 compact single-env gate。IsaacSim 仍有既存 inotify `errno=28` 日志噪声。
- Immediate next actions:
  - 迁移 flat `velocity_height` commands、基础 events/domain randomization、terminations 和非跳跃 curriculum；保持 jump 3D 为零。
  - 配置 IsaacLab 官方基础 locomotion rewards，并做固定状态与 CPU/CUDA 短 rollout 验收。
  - 随后迁移 RSL-RL PPO/GRU 与 obs-group mapping/checkpoint 合同。
  - GPU 空闲后做默认 capacity、多环境与长 rollout 定标。
- Open questions:
  - UNKNOWN: fixed tendon + external loops 在主动 delayed control、CUDA 多环境和长训练下的稳定性；当前只完成 CPU/compact-CUDA 单环境短 gate。
  - LOW: finetune 时是否将 command observation 改为按最终范围归一化，并制定旧 checkpoint 的适配/重训策略。

## Recovery Summary

- fixed-tendon USD/YAML 未改，本轮不会触发 USD SHA stale gate。
- IsaacLab 必须作为 sibling source checkout 存在于 `../IsaacLab`，并 checkout 已验证 commit `b4c321024792976150ca55fddb26fa34480d974e`；不要改回用户目录绝对路径，也不要用 Git subdirectory wheel 代替。
- RL action/observation 已不再是模板占位；后续从非跳跃 command、官方基础 reward、termination/curriculum 继续，自定义奖励留到 finetune。
