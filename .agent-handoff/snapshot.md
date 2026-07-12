# Handoff Snapshot

## Current State

- Last updated: 2026-07-12 16:23（Asia/Shanghai）
- Workspace: 本机 `D:\RoboMaster\se3_rl_lab`；训练机 SSH alias `se3_rl_lab_gpufree`；远端根目录 `/root/gpufree-data/se3-workspace/se3_rl_lab`。
- Git: PR [#9](https://github.com/am345/se3_rl_lab/pull/9) 已 squash merge 到 `main`，merge commit `46edeee`；远端功能分支已删除，本地位于 `main`。
- Current objective: 使用已迁移的腿/轮 T-N 电机模型，从头训练 5000 iterations 的 `SerialLeg-Recovery-v0`，并抑制旧 run 的 action std 失控。
- Current status: 旧 run 已停止；Recovery 专用 PPO 配置已落地并通过 4096-env 单更新门禁；新 5k 正在运行。

## Active Training

- Run name: `recovery_ref_std_fresh_5k`
- PID: `28338`
- Log: `/tmp/recovery_ref_std_fresh_5k.log`
- Run directory: `/root/gpufree-data/se3-workspace/se3_rl_lab/logs/rsl_rl/serialleg_flat_closed_chain/2026-07-12_16-00-33_recovery_ref_std_fresh_5k`
- Contract: fresh seed 42、4096 env、5000 iterations、`resume=false`、save interval 500。
- Post-merge health: iteration 705，std 0.58、mean reward 189.30、catastrophic/NaN/Traceback 均为 0；已跨过 iteration 650，下一历史敏感窗口为 835。

## Configuration Change

- 仓库只注册 `SerialLeg-Recovery-v0`，使用 `RecoveryPPORunnerCfg`；flat task 仍使用 `PPORunnerCfg`。`SerialLeg-Recovery-Loco-v0`、dense tracking rewards 与专用速度范围已删除。
- Recovery 保持 feed-forward MLP、24-step rollout 和现有 PPO 结构，只对齐参考 recovery 的四项随机策略参数：`init_std=0.5`、`entropy_coef=0.00516`、`learning_rate=3e-4`、`desired_kl=0.008`。
- 旧 `recovery_motor_tn_fresh_5k` 在 iteration 约 907 停止；其 std 从 1.01 增至约 2.96，并在 iteration 727–733 出现巨额负 reward，不再继续使用。

## Motor And Action Contract

- Policy 输出仍为 6D：4 个腿位置目标 + 2 个轮速度目标；腿/轮 action scale 为 `0.25 rad / 45 rad/s`。
- 腿使用 `DCMotorCfg` 四象限 T-N 包络；轮使用 `TorqueSpeedCurveActuator` 的 M3508+C620 14:1 实测曲线；仿真 actuator 全速域 gate 已通过。
- Recovery reset 保留完整 policy/passive/wheel/tendon-root 写入与 dataset cache 混合，不含 rollout settle。

## Validation

- 远端静态回归：`17 passed`；相关 Ruff check/format 通过。
- 4096-env/1-update gate：iteration 0 `Mean action std=0.50`、`Mean reward=-4.09`，无 NaN/OOM。
- Gate 生成的运行时 YAML 确认为 `num_steps_per_env=24`、`init_std=0.5`、`entropy_coef=0.00516`、`learning_rate=0.0003`、`desired_kl=0.008`。

## Next Actions / Risks

1. 继续监控新 run 跨过 iteration 835、1500、2000、5000，重点检查 std、NaN、catastrophic termination 与 dataset 混入。
2. 在 model 500 处检查六维 std 参数，确认轮 action 噪声未再次进入长期饱和区。
3. 5k 完成后运行同一 recovery eval，比较 linear/yaw RMSE、自起成功率并录制 MP4。
4. 当前无 blocker；尚未跨过历史敏感窗口，因此不能提前宣称长训练稳定性已验收。

## Active Files

- `source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/agents/rsl_rl_ppo_cfg.py`
- `source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/__init__.py`
- `scripts/test_recovery_contract.py`
- `.agent-handoff/{snapshot,work-log,validation,decisions,backlog,risks}.md`
