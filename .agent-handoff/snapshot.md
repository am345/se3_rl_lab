# Handoff Snapshot

## Current State

- Last updated: 2026-07-13 09:00（Asia/Shanghai）
- Workspace: 本机 `D:\RoboMaster\se3_rl_lab`；训练机 SSH alias `se3_rl_lab_gpufree`；远端根目录 `/root/gpufree-data/se3-workspace/se3_rl_lab`。
- Git: 本地位于 `codex/height-conditioned-recovery`，跟踪同名 `origin` 分支；功能提交 `8f5ee8e`（`Complete height-conditioned recovery contract`）已推送。用户本轮只要求 commit/push，未创建 PR。
- Current objective: height-conditioned recovery contract、评估修复、训练验收与抖动诊断已发布；下一步等待用户确认相机锁 z 与真实控制平滑方案。
- Current status: fresh run `recovery_height_default_fresh_5k` 已健康完成 5000 iterations；最终落盘 `model_4999.pt`。抖动已定位为确定性 actor 闭环极限环，eval 相机逐帧跟随 root z 又放大了画面抖动；collision、固定 5 ms delay、Kd 和 restitution 均不是独立振荡源。生产控制逻辑未因诊断修改，相关源码/测试/文档已推送；`.codex/` 与 `artifacts/` 本地产物明确未提交。

## Completed Training

- Process: launcher/Python 已正常退出；watchdog 状态为 `COMPLETE`。
- Log: `/tmp/recovery_height_default_fresh_5k.log`
- Run directory: `/root/gpufree-data/se3-workspace/se3_rl_lab/logs/rsl_rl/serialleg_flat_closed_chain/2026-07-12_20-32-29_recovery_height_default_fresh_5k`
- Contract: fresh seed 42、4096 env、5000 iterations、`resume=false`、height-conditioned action/reset/reward default、new yaw reward。
- Final health: iteration 4999、reward 259.81、value loss 0.1753、std 0.33、`leg_dof_acc=-0.0044`、catastrophic 0、无 NaN/OOM/Traceback；安全跨过历史 476 与 3195 故障窗口。
- Final checkpoint: `model_4999.pt`，4,441,781 bytes，SHA256 `c3aed3f72be660bd44a269df04be52ed2fd063ca316886ea720bac4cc31f3027`。

## Failed Training

- Run name: `recovery_ref_std_fresh_5k`
- Former PID: `28338`（已退出）
- Log: `/tmp/recovery_ref_std_fresh_5k.log`
- Run directory: `/root/gpufree-data/se3-workspace/se3_rl_lab/logs/rsl_rl/serialleg_flat_closed_chain/2026-07-12_16-00-33_recovery_ref_std_fresh_5k`
- Contract: fresh seed 42、4096 env、5000 iterations、`resume=false`、save interval 500。
- Last normal window: iteration 3192 reward 244.77、std 0.36、catastrophic 0；3193 开始异常，3195 reward `-1.11e7`、value loss `6.97e13`、`leg_dof_acc=-3.29e5`，3204 catastrophic 超过 10%，后续长期约 40–60%。
- Final log: iteration 3606 reward `-128870.74`、std 0.50、catastrophic 0.3959；进程随后无 Python traceback 地退出。系统检查无本次 OOM/GPU Xid/coredump/磁盘满，精确退出信号 `UNKNOWN`。
- Checkpoints: `model_3000.pt` 位于故障前，作为最后可恢复候选；`model_3500.pt` 保存于污染后，禁止直接 resume。两者 tensor 均 finite，但这不代表 3500 行为健康。
- 该 run 始终使用启动时加载的旧纯指数 yaw reward；后来写入源码的 `sigma_cmd_scale=0.4/ratio_blend=0.2` 与本次崩溃无因果关系。
- PPO 直接污染源已确认是 `leg_dof_acc`（四个主动腿关节 acceleration L2）；`lin_vel_z`/`ang_vel_xy` 是同次物理爆炸的次生项。dataset 原始速度、joint-acc reset 历史伪差分、fixed-tendon 轻微越界和单个 cache row 均已排除为独立触发源。
- 20k train cache 全量单控制周期扫描：全部 finite，最大净 active acceleration 854.16 rad/s²、joint velocity 16.34 rad/s，无 catastrophic。model3000 固定均值/真实 Gaussian std 分别完成 12.3M/16.4M transitions，均无 catastrophic。
- 上游 actor/action 失控已确认：普通 reset（非 cache）episode 的 32-step 历史起点 age148 时，`lf0` mean 已达 `+17.90`；age165–179 又出现 `rf0` mean 从 `-2.41` 单调外飘至 `-17.74`。最终 action `-18.62` 经 `0.25` scale 生成 `rf0=-4.378 rad` 目标，右闭链接触失稳；`r_drive_bar_Joint` 达 `-625.29 rad/s`、`-101256 rad/s²`，`rf1_Link` 接触力 `7241 N`、passive wrapped error `2.50 rad`。
- 最终极端 action 不是 Gaussian 尾部：该维 mean `-17.74`、std `0.572`、sample z-score `-1.52`。上一拍 raw action 会经 34D actor observation 的 `last_actions` 槽回灌并参与放大，但最初 mean 外飘早于当前 32-step 捕获窗口；不能把 `last_actions` 表述为已证明的唯一首因。已排除 exploration std、dataset/cache reset、reset 第一拍和新 yaw reward。

## Model 1000 Evaluation

- 用户所称 `model_999.pt` 在当前 save naming 下实际为 `model_1000.pt`。
- 6 场景 × 4 秒 `SerialLeg-Recovery-v0` eval 已按 camera-v2 与 deterministic schedule 修复重录：H.264、1280×720、50 FPS、1199 frames、23.98 s、3,029,675 bytes。
- Camera-v2 只跟随 root 平移，世界朝向固定；水平 FOV 从 60° 扩为 78°（+30%）。
- 本地产物：`artifacts/recovery_eval/model_1000-recovery-eval.mp4`、`model_1000.metrics.json`、`model_1000.evaluation.md`、`model_1000-yaw-{start,end}-v2.png`。
- Eval bugfix: episode timeout 与 command resampling 均延后到完整 suite 之后；场景命令先写入并刷新 observation，再调用 policy。runtime telemetry 为 1200 rows、0 termination、0 command mismatch、0 non-finite。
- Summary: survival 1.0、vx RMSE 0.2096 m/s、yaw RMSE 0.3345 rad/s、non-finite 0。

## Model 2000 / 4999 Jitter Evaluation

- Checkpoint: completed height-default run 的 `model_2000.pt`；eval 使用独立 1-env seed-47 worker，后续另以相同探针检查最终 `model_4999.pt`。
- MP4: remote `isaac_eval/videos/model_2000-step-0.mp4`；H.264、1280×720、50 FPS、1199 frames、23.98 s、2,820,743 bytes。
- Summary: survival 1.0、vx RMSE 0.22453 m/s、yaw RMSE 0.37779 rad/s、1200 steps、0 termination、0 non-finite；max loop residual 0.0009758 m。
- Local artifacts: `artifacts/recovery_eval/model_2000-height-default-{recovery-eval.mp4,metrics.json,evaluation.md}`。
- Jitter diagnosis: 每场景 command 恒定。关闭 eval actor corruption 确实降低早期窗口 action/qvel/torque，但没有消除稳态视觉抖动；model2000 forward 稳态仍出现 `4.67 Hz` actor/leg-target/root-z/contact 同频极限环，raw action/leg target delta RMS 为 `0.533/0.152`，root pitch 角速度 std `1.42 rad/s`。
- Collision: 直立稳态只有 `l_wheel_Link/r_wheel_Link` 接地，两轮法向力同相；底盘、腿、连杆均无误触地。restitution 固定 0 后 root-z std `1.899→1.855 mm`，基本不变。
- Delay/PD: 4–6 ms delay 在 5 ms physics step 下恒定量化为 1 步，不是随机 jitter；关闭 delay 后 root-z std `1.899→1.853 mm`。腿 Kd `3→6` 虽降低 leg qvel RMS `2.43→1.49 rad/s`，root-z std 仍为 `1.887 mm`。两者均不消除极限环。
- Camera: production camera 同时跟随 root x/y/z。完全相同的前 1 秒轨迹只锁定相机 z 后，背景垂直逐帧位移 RMS `0.508→0.095 px`（约降 81%）；说明相机显著放大画面抖动，但真实机器人仍在振荡。6 秒诊断 MP4 为 `artifacts/recovery_eval/model_2000-height-default-xy-camera-diagnostic.mp4`。
- Final checkpoint: model4999 相同探针仍有极限环；forward root-z std `1.625 mm`、pitch-rate std `1.50 rad/s`、action/target delta RMS `0.666/0.204`。训练完成没有消除控制抖动。
- No-noise rerecord: `model_2000.pt` 同一 6×4 秒 suite 重录为 H.264 1280×720@50 FPS、1199 frames、23.98 s、2,778,025 bytes；survival 1.0、vx/yaw RMSE 0.22289/0.38080、0 non-finite。新本地产物为 `artifacts/recovery_eval/model_2000-height-default-no-noise-*`；旧 noisy 本地 MP4 保留用于 A/B。

## Configuration Change

- 仓库只注册 `SerialLeg-Recovery-v0`，使用 `RecoveryPPORunnerCfg`；flat task 仍使用 `PPORunnerCfg`。`SerialLeg-Recovery-Loco-v0`、dense tracking rewards 与专用速度范围已删除。
- Recovery 保持 feed-forward MLP、24-step rollout 和现有 PPO 结构，只对齐参考 recovery 的四项随机策略参数：`init_std=0.5`、`entropy_coef=0.00516`、`learning_rate=3e-4`、`desired_kl=0.008`。
- Recovery yaw tracking 已启用参考 flat reward 的大误差梯度语义：`sigma_cmd_scale=0.4`、`ratio_blend=0.2`；保留 Recovery 权重 `1.5` 与直立门控。参考 Recovery-Discovery 在 `93f6ba2` 实际配置为 `0/0`，因此这是用户明确要求的语义迁移，不是逐参数照抄 Discovery。
- 旧 `recovery_motor_tn_fresh_5k` 在 iteration 约 907 停止；其 std 从 1.01 增至约 2.96，并在 iteration 727–733 出现巨额负 reward，不再继续使用。
- Recovery 已完整启用 height-conditioned default：command height 通过参考四连杆 LUT 生成 4D policy 默认腿型；command 重采样同步 per-env cache；非-cache reset、action 零点、`stand_still`/`joint_pos_penalty`/`joint_mirror` reward 与固定命令 eval 共用该 cache。cache reset 仍保留 settled-state 完整关节状态。

## Motor And Action Contract

- Policy 输出仍为 6D：4 个腿位置目标 + 2 个轮速度目标；腿/轮 action scale 为 `0.25 rad / 45 rad/s`。
- 腿使用 `DCMotorCfg` 四象限 T-N 包络；轮使用 `TorqueSpeedCurveActuator` 的 M3508+C620 14:1 实测曲线；仿真 actuator 全速域 gate 已通过。
- Recovery reset 保留完整 policy/passive/wheel/tendon-root 写入与 dataset cache 混合，不含 rollout settle。

## Validation

- 远端静态回归：`25 passed`；相关 Ruff check/format 通过。
- 64-env/8-step reward runtime gate：reward/observation finite，`max_abs_reward=1.176`，reset/passive/tendon/clearance 合同通过。
- 4096-env/1-update gate：iteration 0 `Mean action std=0.50`、`Mean reward=-4.09`，无 NaN/OOM。
- Gate 生成的运行时 YAML 确认为 `num_steps_per_env=24`、`init_std=0.5`、`entropy_coef=0.00516`、`learning_rate=0.0003`、`desired_kl=0.008`。
- Height-default 5 点数值与参考仓库在 `2e-6 rad` 内一致；静态回归 `17 passed`、Ruff 通过。
- 64-env iteration-2000 mixed reset gate：cache ratio 0.266、height cache error 0、zero-action target error 0、passive/tendon error 0、wheel clearance 0.0010 m。
- 4096-env/1-update height-default gate：98,304 steps、std 0.50、catastrophic 0、无 NaN/OOM。

## Next Actions / Risks

1. 与用户确认后再分两条实施：录像相机改为只跟随 x/y（渲染修复）；控制端增加可训练的 action rate limiter/low-pass 或加强平滑约束并 fresh retrain（真实抖动修复）。不要把 eval-only filter 直接套到旧 checkpoint。
2. 若继续控制修复，先做固定 seed 的 actor-output→leg-target→pitch/contact 回归，目标是消除 4–5 Hz 主峰；PD/delay/restitution 只作为联合 A/B，不再单独当根因。
3. `model_3500.pt`（旧失败 run）已污染，禁止 resume；健康完成 run 的最终 checkpoint 是 `model_4999.pt`。

## Active Files

- `source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/agents/rsl_rl_ppo_cfg.py`
- `source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/__init__.py`
- `source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/{recovery_env_cfg.py,mdp/reward_math.py,mdp/rewards.py}`
- `source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/mdp/{height_defaults,actions,commands,recovery_events}.py`
- `source/se3_rl_lab/se3_rl_lab/isaac_eval/{camera,schedule,worker}.py`
- `scripts/test_experiment_tools.py`
- `scripts/test_recovery_contract.py`
- `.agent-handoff/{snapshot,work-log,validation,decisions,backlog,risks}.md`
