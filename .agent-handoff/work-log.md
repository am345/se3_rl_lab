# Current Work Log

## 2026-07-12 model2000/model4999 视觉与控制抖动因果诊断

- 用户确认 noisy/no-noise 两段 MP4 观感均“非常抖”，因此撤回“关闭 eval observation corruption 已解决视觉抖动”的推断。逐帧蓝色轮廓、背景网格与 telemetry 均显示约 4.5–5 Hz 主峰。
- production camera 每拍跟随 root x/y/z。相同 seed、相同前 50-step 物理轨迹仅把诊断 camera z 固定到 0.26 m 后，底部背景垂直逐帧位移 RMS `0.508→0.095 px`，约降 81%；生成 5.98 秒 H.264 诊断 MP4 `artifacts/recovery_eval/model_2000-height-default-xy-camera-diagnostic.mp4`。该实验未修改生产源码。
- 新建并清理临时 headless probe，记录 policy raw/processed action、leg/wheel target、joint state/effort、root pose/velocity 与逐 body contact。model2000 forward 稳态 actor/leg-target/root-z/contact 同频约 `4.67 Hz`；raw action/target delta RMS `0.533/0.152`，root-z std `1.899 mm`，pitch-rate std `1.418 rad/s`。
- 碰撞审计显示直立 baseline 仅左右轮接地，两轮法向力同相；底盘、腿和连杆无误触地。固定 restitution=0 后 root-z std `1.855 mm`。4–6 ms action delay 在 5 ms physics step 下恒定为 1 step；关闭后 root-z std `1.853 mm`。Kd `3→6` 将 leg qvel RMS `2.43→1.49 rad/s`，但 root-z std 仍 `1.887 mm`。三者都不消除极限环。
- fresh 训练健康完成 iteration 4999：reward 259.81、value 0.1753、std 0.33、`leg_dof_acc=-0.0044`、catastrophic 0；watchdog `COMPLETE`。最终 `model_4999.pt` SHA256 `c3aed3f72be660bd44a269df04be52ed2fd063ca316886ea720bac4cc31f3027`。
- 相同 probe 检查 model4999：forward root-z std `1.625 mm`、pitch-rate std `1.505 rad/s`、action/target delta RMS `0.666/0.204`，说明完整 5k 未消除抖动式动态平衡。参考 commit `93f6ba2` 的 PD `60/3`、wheel Kd `0.08`、4–6 ms delay、50 Hz control 与当前一致，且参考同样只有 reward 级 action rate/smoothness、无硬 low-pass。
- 本机临时 probe 脚本、raw frames 与 contact telemetry 已清理；保留用户可看的短诊断 MP4。远端 `/tmp/jitter_probe*` 与 `/tmp/se3_camera_z_diag` 清理时 SSH alias 突然无输出退出，是否删除成功未确认，重连后应补查；均为 `/tmp` scratch，不影响 run。production control/camera 未在本轮修改。

## 2026-07-12 model 2000 视频抖动诊断

- Telemetry 证明六场景 command 每 200 步内严格恒定，只在场景边界切换；排除 command 重采样抖动。baseline raw action 每拍 delta RMS 为约 0.40–0.58，腿 target 为 0.10–0.16 rad，抖动在进入 PD/碰撞前已存在；运动场景腿 action 有约 4.4 Hz 主峰。
- 固定 seed 短 A/B 的 stand steps25–49：baseline action/target/qvel/torque/contact delta RMS `0.2769/0.0597/0.4478/2.201/22.995`；no-delay `0.2784/0.0607/0.5188/2.047/17.656`；Kd=6 `0.2692/0.0591/0.3561/2.195/18.353`；zero restitution `0.2766/0.0596/0.4359/2.199/23.293`。
- 关闭 eval actor observation corruption 后为 `0.0642/0.0246/0.0729/0.404/8.120`，action/qvel/torque 分别约降 77%/84%/82%。根因是 eval worker 沿用训练配置 `enable_corruption=True`；尤其 scaled leg velocity noise `±1.5` 等价于原速度 `±6 rad/s`。参考仓库 play 明确用 `enable_corruption=not play`。
- 所有 `[DEBUG]`/临时 worker 字段、A/B 配置、checkpoint 副本、diag metrics/reports/logs 已删除；正式 worker 恢复并通过 Ruff，原 model2000 latest_result 已恢复。
- 用户授权重录后，在正式 eval worker 创建环境前设置 `env_cfg.observations.actor.enable_corruption=False`；训练 cfg 不变。新增静态回归，Ruff 与 experiment/recovery `18 passed`。同一 model2000 完整重录通过，产物 `model_2000-height-default-no-noise-*` 已同步本地，旧 noisy MP4 保留。

## 2026-07-12 height-conditioned default 完整迁移与 fresh 5k

- 将参考仓库 height-conditioned default 作为统一 contract 迁移：参考四连杆 8192/1024 点 LUT、per-env height cache、command resample 刷新、非-cache recovery reset 基准、action 零点、三个关节姿态 reward 和固定命令 eval 刷新均使用同一 4D policy default。
- settled-state cache rows 继续整行覆盖 root/policy/passive/wheel 状态，不强行改写为 height default；非-cache 随机化从当前 command height 对应腿型开始，随后重新求 passive joints 并执行 wheel clearance lift。
- 参考 0.20/0.22/0.26/0.30/0.32 m 输出逐点锁定，误差阈值 `2e-6 rad`；64-env mixed reset 与 4096-env/1-update CUDA gates 通过。
- 启动 fresh seed-42、4096-env、5000-iteration run `recovery_height_default_fresh_5k`；log `/tmp/recovery_height_default_fresh_5k.log`，run dir `2026-07-12_20-32-29_recovery_height_default_fresh_5k`。iteration 868 reward 251.18、value 0.2697、std 0.33、catastrophic 0。
- 部署远端独立 watchdog PID `29876`，每 30 秒更新 `/tmp/recovery_height_default_watchdog.status`；明确巨额 reward/value、catastrophic 扩散或 NaN/OOM/Traceback 时自动 SIGTERM 训练，避免污染继续写入 checkpoint。
- 对最新已落盘 `model_2000.pt` 运行完整 6×4 秒 eval 并录制 MP4；1199 frames/23.98 s/2,820,743 bytes，survival 1.0、vx/yaw RMSE 0.22453/0.37779、0 termination/non-finite。产物已同步到本地 `artifacts/recovery_eval/model_2000-height-default-*`；并行训练继续健康推进到 iteration 2299。

## 2026-07-12 recovery 污染源追踪（禁止兜底）

- 确认 PPO 直接污染项为 `leg_dof_acc`：它只覆盖 `lf0/l_drive_bar/rf0/r_drive_bar` 四个主动腿关节，3195 日志为 `-3.29e5`、3196 为 `-1.65e7`，后续峰值 `-9.37e20`；vertical/angular root velocity 项是次生污染。
- IsaacLab joint velocity reset 会同步 `_previous_joint_vel` 并将 joint_acc 清零；reward 又在物理步后、reset 前读取，因此巨峰是真实 PhysX velocity jump，不是 reset history 伪差分。
- 40k dataset 数值审计：root linear max 0.147 m/s、root angular max 0.346 rad/s、joint velocity <1 rad/s，全 finite，排除原始速度离群。
- dataset 中 fixed-tendon 坐标确有 MuJoCo 软限位残余越界（左最大 +0.00375 rad、右 +0.00233 rad），但 64+64 A/B 显示越界组不比刚好限内组更差；加入 interior 对照后各组均为约 10³ rad/s² 首步峰值，排除“越界本身”作为独立首因。
- 扫描全部 20k train cache rows，按真实 4 physics-substep 控制周期执行 zero delayed action：全部 finite，最大净 acceleration 854.16 rad/s²、joint velocity 16.34 rad/s、root linear/angular 0.766/4.056，0 个 catastrophic。排除任一 cache row 单独致炸。
- 用 model3000 重建 actor：deterministic mean 跑 3000 steps/12.3M transitions、Gaussian std 跑 4000 steps/16.4M transitions，均 0 catastrophic，reward abs max 约 2.38。说明静态 checkpoint、cache/reset、随机 action tail 单独不足；触发需要 PPO 继续更新、精确 RNG 或长时 solver/contact 历史之一。
- fresh seed-42、4096-env、保留 PPO 更新的探针在 iteration 476 可重复捕获 env 1587 严重事件：普通 reset 后 age 180、非 cache reset；`r_drive_bar_Joint=-625.29 rad/s`、`-101256 rad/s²`，`rf1_Link` 接触力 `7241 N`，passive wrapped error `2.50 rad`。
- 动作分布探针确认 `rf0` 最终 action `-18.62` 对应 mean `-17.74`、std `0.572`、z-score `-1.52`，不是 Gaussian 尾部。32-step 历史起点 age148 时 `lf0` mean 已达 `+17.90`；age165–179 的 `rf0` mean 又为 `-2.41,-3.36,-5.37,...,-17.74`，说明 actor 整体先离开物理动作域，异常随后转移至右腿。
- 上一拍 action 会通过 actor observation 的 `last_actions` 槽回灌并参与后续放大；但 mean 最初外飘早于已捕获窗口，且 age164→165 还伴随 leg velocity/base angular velocity 变化，因此当前证据不足以把 `last_actions` 定为唯一首因。
- action wrapper 的 `clip_actions=None`，ActionTerm 仅在 `±100` clip；`-18.62 × 0.25` 将 `rf0` 目标推至 `-4.378 rad`。这一不可实现的腿目标先打爆右闭链，`leg_dof_acc` 再把巨额有限负 reward 写入 PPO。
- 临时 diagnostic scripts 已从本地和远端清理；生产代码、reward/reset/termination/课程均未修改，正式训练未恢复。

## 2026-07-12 recovery 5k iteration 3195 级联崩溃

- PID `28338` 已退出，日志完整停在 iteration 3606；无 Python traceback/NaN check/OOM 文本。主机内存、磁盘和 GPU 当前正常，内核无本次 OOM/Xid，coredump 为空；最终退出信号 `UNKNOWN`。
- 日志定位首个连续异常：3192 正常；3193 `leg_dof_acc` 从约 `-0.006` 到 `-0.0659`；3194 reward 77/value loss 1.44e4；3195 reward `-1.11e7`、value loss `6.97e13`、catastrophic 0.0067；3204 catastrophic 0.101，之后长期约 0.4–0.6。
- 首因不是 std：3195 std 仅 0.36；也不是 3400 cache stage，故障早 205 iterations。cache 在 2600 起为 45%，精确的罕见物理触发样本/动作仍未知。clearance adjustment 不是充分解释，历史更大 lift 在正常期出现过。
- 级联机制已由源码顺序确认：IsaacLab `step` 先 `termination_manager.compute()`，再 `reward_manager.compute()`，之后 reset；Recovery 的 vertical/angular velocity 与 joint acceleration L2 项无 cap。catastrophic termination 可防 NaN，但不能阻止终止帧的巨额有限 reward 进入 PPO。
- `model_3000.pt` 是最后一个故障前 checkpoint；`model_3500.pt` 已污染。两者 actor/critic state tensors finite，3000 actor std param 0.410、3500 为 0.532，但 finite checkpoint 不等于健康策略。
- 尝试用 checkpoint smoke 做 postmortem：首次命令因 PowerShell 变量提前展开误传 `model_.pt`，已终止并清理；第二次 model3000 runner 在 180 秒内未完成，已终止清理，未作为证据。未修改代码、未恢复训练。

## 2026-07-12 Recovery yaw 大误差梯度语义

- 对照 `se3_wheel_leg_spring_add@93f6ba2`：当前与参考 Recovery-Discovery 原配置均为固定 `sigma=0.25` 的纯指数 yaw reward；“高 yaw 大误差保留梯度”来自同分支 flat reward 的 `sigma_cmd_scale=0.4`、`ratio_blend=0.2`。
- 按用户要求只迁移这两个 yaw tracking 语义；保留 Recovery term 名、权重 `1.5`、直立门控、其余 24 个 reward、command/PPO/reset/termination 不变。线速度 reward 仍使用 Recovery 的 adaptive pure-exp 语义。
- 新增纯函数 `angular_tracking_reward`：`sigma_eff=sigma*(1+scale*|cmd|)`，再混合 exponential 与比例项。`cmd=12/error=6` 回归锁定 reward≈0.1、error gradient `<-0.01`；旧固定 sigma exp 为 `exp(-144)`，float32 下近零。
- test-first RED 命中配置缺少两个参数；GREEN 为四组回归 `25 passed`，Ruff format/check 通过。64-env/8-step CUDA runtime gate 通过，reward/obs finite、`max_abs_reward=1.176`。
- 正式训练 PID `28338` 未停止；到 iteration 3100 为 std 0.35、mean reward 242.08、catastrophic 0。由于 Python 进程已在启动时加载旧 reward，该 run 不包含新语义；需要新进程/重新训练才能做有效 A/B。

## 2026-07-12 eval deterministic schedule bugfix

- 只修改 eval 链路：新增 `isaac_eval/schedule.py`，在 `gym.make` 前将 episode timeout 与 command resampling 设到完整 suite 时长加 1 秒之后；未修改训练 task、reward、command curriculum、reset 或 termination。
- 场景切换顺序改为“写入固定命令 → 刷新 policy observation → policy inference”，删除逐 step 重写命令的旧路径，避免边界第一步使用上一场景命令 observation。
- test-first 红灯确认 `ModuleNotFoundError`；实现后 experiment/recovery/actuator/observation 共 `24 passed`，Ruff format/check 通过。
- 用 `model_1000.pt` 重跑 6×4 秒完整 eval：1200 telemetry rows、0 termination、0 command mismatch（`abs_tol=1e-6`）、0 non-finite；vx/yaw RMSE 从受 timeout 污染的 `0.3206/0.4129` 降为 `0.2096/0.3345`。
- MP4 为 H.264 1280×720@50 FPS、23.98 秒、1199 frames，已覆盖同步到 `artifacts/recovery_eval/model_1000-recovery-eval.mp4`。并行训练 PID `28338` 未停止，验证后运行到 iteration 2671。

## 2026-07-12 eval camera-v2

- 用户反馈 yaw-relative camera 旋转观感不适；改为固定世界 eye offset `(0.0,-2.4,0.57) m`，eye/target 每帧只加相同 root translation，不再读取 root quaternion/yaw。
- 新增纯函数 camera geometry 模块与两项测试；水平 FOV 按角度精确乘 `1.3`，runtime 日志确认 `60.00°→78.00°`、focal length `18.148→12.939`。
- recovery/actuator/observation/experiment tests 共 `22 passed`，相关 Ruff check/format 与 diff check 通过。
- 完整重录 model_1000：H.264 1280×720@50 FPS、23.98 s、1199 frames、3.08 MB；yaw_left 13.0/15.5 s 抽帧的地面网格方向一致，机器人在固定世界视角内旋转，确认 camera 不随 yaw 转动。
- 新 MP4 覆盖本地 `artifacts/recovery_eval/model_1000-recovery-eval.mp4`；训练并行运行到 iteration 1650，std 0.42、mean reward 227.82、catastrophic/NaN/Traceback 0。

## 2026-07-12 model_1000 recovery eval MP4

- 当前 run 不存在 `model_999.pt`，按 RSL-RL save naming 使用对应的 `model_1000.pt`。
- 与 4096-env 训练并行完成 1-env/seed47、6 scenarios × 4 s eval；录制 H.264 1280×720@50 FPS、23.98 s、1199 frames、4.82 MB，无 eval Traceback/Error/NaN。
- metrics: score 49.432、survival 0.9992、vx RMSE 0.3206 m/s、yaw RMSE 0.4129 rad/s、non-finite 0；仅 yaw_right 发生 1 次 termination。
- MP4、metrics、report 和 6 s preview 已同步到本地 `artifacts/recovery_eval/model_1000-*`；抽帧确认机器人、相机与目标/实际速度箭头可见。
- 录制结束后正式训练到 iteration 1228，std 0.46、mean reward 219.13、catastrophic/NaN/Traceback 0。

## 2026-07-12 Recovery/Motor PR

- 创建分支 `codex/recovery-motor-model`，提交 `e506dda Implement recovery task and motor envelopes` 并推送到 `origin`。
- GitHub App 创建 PR 因 integration 403 失败，按发布流程使用已认证 `gh` CLI 成功创建 Draft PR [#9](https://github.com/am345/se3_rl_lab/pull/9)。
- PR 正文记录当前 5k progress（iteration 487、std 0.79、mean reward 140.69、无 NaN/Traceback/OOM）、旧 std 失控/reward 爆点、历史 PhysX NaN、电机固定 limit 问题和未跨过的长训练风险。
- 明确排除本地 `.codex/` 和 `artifacts/` 生成产物；reset dataset、USD、电机/recovery 代码、测试和文档均已纳入提交。
- 用户授权后将 PR 转 Ready 并 squash merge 到 `main`，merge commit `46edeee`；本地/远端 main 已同步，功能分支已删除。
- Merge 收尾时训练到 iteration 705，std 0.58、mean reward 189.30、catastrophic 0、无 NaN/Traceback，已跨过 iteration 650。

## 2026-07-12 删除 Recovery-Loco

- 按用户要求删除 `SerialLeg-Recovery-Loco-v0` Gym 注册、`RecoveryLocoEnvCfg`、`RecoveryLocoRewardsCfg`、三组 `_LOCO_*` 速度限制、两个 dense Smooth-L1 tracking reward 函数。
- 静态契约改为确认 loco task/dense terms 不存在；远端 recovery/actuator/observation 回归 `17 passed`，Ruff check/format 通过。
- 当前正式训练使用 `SerialLeg-Recovery-v0`，进程启动时已加载基础 recovery 配置，因此本次删除不改变其运行时环境；PR 前更新到 iteration 427、std 0.83、mean reward 87.22、catastrophic 0、无 NaN/Traceback。

## 2026-07-12 recovery 参考随机策略参数重启 5k

- 停止旧 `recovery_motor_tn_fresh_5k`：PID `22920` 最终约 iteration 907，mean std 约 2.96；进程与 GPU 占用已清理。
- 新增 `RecoveryPPORunnerCfg`，保持 MLP/24-step rollout 不变，对齐参考值 `init_std=0.5`、`entropy=0.00516`、`lr=3e-4`、`desired_kl=0.008`；Recovery 使用新配置，flat 保持原配置。
- 静态回归 `17 passed`，Ruff check/format 通过；4096-env/1-update runtime gate 显示 std 0.50、无 NaN/OOM，保存的 agent YAML 与目标参数一致。
- 启动 fresh 5k：run `recovery_ref_std_fresh_5k`，PID `28338`，日志 `/tmp/recovery_ref_std_fresh_5k.log`，run dir `2026-07-12_16-00-33_recovery_ref_std_fresh_5k`。iteration 108 时 std 0.75、catastrophic 0、无非有限值。

## 2026-07-12 fresh recovery 5k

- Preflight: RTX 4090 空闲（约 24 GB free）、数据盘剩余 28 GB、无残留训练进程。
- Gate: `SerialLeg-Recovery-v0`、4096 env、1 PPO update 通过；98,304 steps、30.7k steps/s、`catastrophic_state=0`、无 NaN/OOM。
- Formal run: fresh seed 42、4096 env、5000 iterations、`resume=false`、save interval 500；run name `recovery_motor_tn_fresh_5k`。
- Runtime: PID `22920`；日志 `/tmp/recovery_motor_tn_fresh_5k.log`；run dir `logs/rsl_rl/serialleg_flat_closed_chain/2026-07-12_15-28-33_recovery_motor_tn_fresh_5k`。
- Initial health: iteration 0–31 已运行，首轮约 29.9k steps/s、catastrophic 0、无 NaN/Traceback/OOM，ETA 约 4h34m。
- Later diagnosis: mean action std 由 1.01 单调增至约 2.96；iteration 727–733 出现巨额负 reward。用户授权后，该 run 已在约 iteration 907 停止并由参考随机策略参数的 fresh run 取代。

## 2026-07-12 YAML action-scale 单一来源

- Objective: 消除 YAML `40/3.71` 与实际 policy `0.25/45` 的矛盾。
- Changes: `robot_config.yaml` 改为 legs `0.25`、wheels `45.0`；`SerialLegDelayedActionCfg` 默认值通过 `SERIALLEG_CONTRACT` 读取，不再维护第二份数字；静态测试锁定 YAML→contract→action wiring；README 同步。
- Asset: YAML SHA 变化后重建 collision-only USD，磁盘 `--check` 报告 13 links/12 tree joints/2 loops/2 tendons/54 meshes/7102 faces/2 cylinders/0 visuals、质量 `12.72874553 kg`、大小 `536348 bytes`。
- Runtime: config probe 输出 `yaml 0.25 45.0` / `runtime 0.25 45.0`；64-env CUDA recovery 16-step gate 通过，reward/obs finite、passive/tendon error 0、wheel clearance 0.0010 m。

## 2026-07-12 电机扭矩—速度模型迁移

- Objective: 迁移 `se3_wheel_leg_closedchain_obs34` 的腿部四象限 DC motor 与轮部实测非线性 T-N 包络，不改 policy/action I/O、reward、reset 或 termination。
- Changed files:
  - `source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg_motors.py`: 新增共享 `MotorSpec`、DM-8009P 参数及 M3508+C620 14:1 的 12 点曲线。
  - `source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg_actuators.py`: 新增 IsaacLab `TorqueSpeedCurveActuator`，按当前关节速度分段线性插值并裁剪显式 PD 扭矩。
  - `source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg.py`: 腿切换为 `DCMotorCfg`，轮切换为曲线 actuator，passive linkage 保持 implicit zero actuator。
  - `scripts/test_serialleg_actuators.py`: 新增曲线点、插值、正反转、四象限腿电机和 wiring/action 合同测试。
  - `README.md`: 记录显式 actuator、参数来源以及 YAML/action-scale 边界。
- Result: 远端 IsaacLab 实例化为 `DCMotor`/`TorqueSpeedCurveActuator`，定点裁剪与参考值一致；64-env CUDA recovery reset + 16-step random rollout 通过，无 non-finite。
- Follow-up: 新增 `scripts/smoke_serialleg_motor_envelopes.py`，在实际 runtime actuator 上全速域采样 801 点并与共享 `MotorSpec` 对照；腿/轮最大误差分别为 `5.836e-06/7.366e-06 N·m`。同时生成腿/轮 T-N 包络可视化，README 补充 gate 命令。
- Remaining risks: 尚未用新 dynamics 跑 4096-env PPO update 或正式从头训练；低速目标区仍处于轮曲线恒扭矩平台，跟踪改善幅度需实训评估。

## 2026-07-12 recovery locomotion finetune（已删除）

- 新增 recovery-loco task、固定实用速度范围与两个 dense tracking reward terms。
- 从原 recovery `model_1999.pt` 成功 resume；1-update runtime gate 后启动 1000-iteration finetune。
- 该独立任务、专用速度范围和 dense reward 已按用户后续要求从代码删除，不再是活跃训练路径。

## 2026-07-12 model_1999 recovery eval MP4

- 修正 eval worker 对 recovery reset 无 `pose_range` 参数的兼容性。
- 录制 H.264 1280×720@50 FPS、23.98 秒 MP4，抽帧确认 collision preview、相机与箭头可见。
- 将 MP4 和 metrics 从远端同步到 `artifacts/recovery_eval/`。

## 2026-07-12 确定性定位 recovery NaN

- 第二次正式 run 在 iteration 210 失败，推翻“wheel clearance 是 NaN 根因”的判断。
- 插桩复现到 env 2821 的完整 PhysX state 同步变 NaN，之前 raw policy action 达 627.8；contact force 仍 finite。
- 对照参考源码确认 recovery 保留 `catastrophic_state`；本仓库 timeout-only 测试和配置属于不完整迁移。
- 恢复 hard-error termination 后，同 seed 原始 400-iteration repro 通过；临时 debug 插桩已清理。

## 2026-07-12 recovery iteration-835 NaN

- 定位旧训练在 iteration 835、82,182,144 steps 后 reward NaN；dataset 尚未启用。
- 1024 env、iteration 650、1200 steps 的随机动作 std 1.0/9.1 均未复现。
- 参考 recovery 启用了 `align_root_height_to_wheels=True` 和最终 collision snap；当前迁移此前遗漏了 joint randomization 后的实际 wheel clearance 修正。
- 已在 `recovery_events.py` 增加 post-joint-reset wheel lift，并扩展 `smoke_recovery_reset.py` 的持续/策略/clearance 诊断能力。
- 已启动 fresh `recovery_full_2k_wheel_clearance`。

## 2026-07-11 — 完整reset运行时gate通过并启动正式2k

- 新增 `scripts/smoke_recovery_reset.py`；64-env和4096-env iteration-2000 gate均通过，4096 env cache比例25.3%、passive误差0、两个tendon-root position/velocity为0，16步reward/observation有限。
- 4096-env/100-iteration PPO soak完成9830400 steps，无NaN或异常退出；源码grep确认无runtime settle和debug钩子。
- fresh `recovery_full_2k` 已启动，日志 `/tmp/recovery_full_2k.log`；第4轮约58k steps/s、显存4.9 GiB、无NaN。

## 2026-07-11 — 完整迁移 recovery dataset/passive reset

- 重新核对最新 `se3_wheel_leg_spring_add@058b800`，确认正式 Recovery-Discovery 使用 `serialleg_closedchain_stair_v3_40k.npz`、五姿态混合、cache ratio curriculum和完整 joint reset。
- 新增四连杆 policy→passive position/velocity映射；标准 reset同步写4 policy、4 passive、2 wheel和2 virtual tendon-root；cache按名称将10-joint样本映射到当前12-joint资产。
- 复用40k NPZ（20k train/20k eval），cache比例为 iteration `1500/2000/2600/3400/4200` 的 `10%/25%/45%/60%/70%`；删除会污染PPO rollout的零动作settle。
- 本地 Ruff/diff通过，dataset/schema/passive映射测试 `5 passed`。服务器恢复后已同步全部核心源码与NPZ，5个文件本地/远端SHA一致；远端同一测试 `5 passed`。确认GPU空闲且无训练进程，未启动Isaac环境或训练。

## 2026-07-11 — 修复 recovery reset 后 PhysX NaN 并重启 2k

- 定位钩子两次捕获到单 env root/joint state 爆炸至 `1e13–1e23`，首个非有限 reward 分别为 `leg_dof_acc`/`tracking_lin_vel`；reward 不是根因。
- 迁移完整机器人包络 clearance；单独使用仍在第 52 轮复现。随后为 recovery reset 增加 40 physics-step 零动作 settle，并在 action term 中只对 settle env 清 raw/processed/FIFO。
- 带诊断与清理诊断后的两次 4096-env/100-iteration soak 均完成 983 万 steps，无 NaN；临时 `[DEBUG-recovery-nan]` 已移除。
- fresh run `2026-07-11_17-42-49_recovery_2k_settle` 已启动；第 18 轮正常，预计约 50 分钟。

## 2026-07-11 — 启动 recovery 2k fresh 训练

- 远端数据盘剩余 28 GB、RTX 4090 空闲后，从零启动 `SerialLeg-Recovery-v0`：4096 env、2000 PPO iterations、run `2026-07-11_16-52-22_recovery_2k`。
- 后台日志为 `/tmp/recovery_2k_20260711_165215.log`；第 19 轮约 84k steps/s、mean reward 45.43、显存约 4.5 GiB，预计约 40 分钟。

## 2026-07-11 — 新增 SerialLeg recovery 微调任务

- 注册 `SerialLeg-Recovery-v0`，继承 flat scene/action/observation/command/curriculum/PPO，只替换 recovery reward、reset 和 termination。
- `RecoveryRewardsCfg` 锁定 `se3_wheel_leg_spring_add` Recovery-Discovery 的 25 个 term 与权重；新增姿态/高度/稳定、腿轮动作正则、能耗、限位和接触实现，`diagnostics` 恒返回零。
- reset 按 iteration `0/300/650/1000/1400` 从 `±15°` 扩展到全姿态，并随机化 root xy/yaw/线角速度；termination 只保留 timeout。
- 更新 README、实验工具链文档和 run manifest reward profile；新增 `scripts/test_recovery_contract.py`。
- 远端 CUDA 完成 1 env/24 steps/1 PPO update；6D action、34D/40D observation、25 reward 与 timeout-only termination 均成功实例化并执行。

## 2026-07-11 — eval 录制相机跟随机器人

- eval worker 新增逐控制步相机更新：以机器人 root yaw 旋转侧后方 offset，保持约 `2.4 m` 横向距离和 `0.57 m` 高差，target 始终指向 root。
- 1 秒 × 6 scenarios 短测中对 forward 段 1.10s/1.90s 抽帧，机器人始终位于画面中央附近而地面网格发生相对移动；随后完整 24 秒 MP4/RRD 重录并覆盖本地交换目录。

## 2026-07-11 — 放大 eval 速度 debug_vis 箭头

- 将目标/实际速度箭头基准 scale 从 `(0.45, 0.06, 0.06)` 放大到 `(1.0, 0.18, 0.18)`，速度长度倍率从 `2.0` 提高到 `3.0`，离机器人高度从 `0.18 m` 提高到 `0.35 m`。
- 先用 0.5 秒短测检查，再完成 4 秒 × 6 scenarios 重录；抽帧确认绿色/蓝色箭头在 1280×720 画面中清晰可辨，最终 MP4/RRD 已覆盖本地交换目录版本。

## 2026-07-11 — 修复 debug-vis MP4 中机器人外壳静止

- Diagnosis: telemetry 和新增的 `base_world_x/y` 证明策略与物理刚体正常移动；问题只发生在 render-only collision preview。副本原先作为 replicated articulation body prim 的子节点，未可靠继承 tensor-driven body transforms，因此视频里的外壳停在初始位置。
- Fix: preview 改为独立 world-space Xform 树，保存每个 body 的 transform op，并在 rollout 每步从 `robot.data.body_pos_w/body_quat_w` 显式同步；不修改 collision-only USD，也不参与物理。
- Result: 0.5 秒短测中前进段 0.55s/0.95s 抽帧确认外壳位置和姿态均变化；随后完整重录 4 秒 × 6 scenarios 的 MP4/RRD 并复制到本地交换目录。

## 2026-07-11 — eval MP4 增加速度 debug_vis

- `VelocityHeightCommand` 按 IsaacLab marker 合同新增绿色目标速度与蓝色实际速度箭头，默认训练不开启；eval worker 显式启用。
- 为稳定录制 marker，eval-only 关闭 Fabric、固定 reset x/y/yaw=0 并使用侧视相机；训练仍保留 Fabric 和随机 reset。
- 完整 24 秒 debug-vis MP4/RRD/metrics 已复制到 `D:\RoboMaster\se3_checkpoint_exchange\model_499_flat_basic_24s`，抽帧确认箭头可见。

## 2026-07-11 — model_499 完整 flat-basic 录制

- 使用 six-scenario、每场景 4 秒的完整 eval 录制 `model_499.pt`；生成 23.98 秒/1199 帧/1280×720 MP4 与同 rollout 的 334KB Rerun。
- MP4、RRD、metrics 和 Markdown 报告已复制到本机 `D:\RoboMaster\se3_checkpoint_exchange\model_499_flat_basic_24s`，便于直接查看和交换。

## 2026-07-11 — finetune 前两阶段实验工具链完成

- Lifecycle: 新增 `se3rl` Python CLI，覆盖 train/resume/play/eval/record/runs/compare；run resolver 支持 path/name/唯一子串和 latest/best/iteration checkpoint，manifest/status 持久记录 Git/合同/训练/评估状态。
- Isaac Eval: 独立 worker + `flat-basic` 六 scenario；collision-only robot 从 54 meshes/2 cylinders 创建 render-only copies，自动输出 MP4、metrics、逐步 telemetry、context 和 latest result，不改物理 USD。
- Diagnostics: 同一次 rollout 生成 Rerun `.rrd`、单 checkpoint Markdown 和 compare report；统一 score 更新 best checkpoint。Rerun 固定 0.20.3，因 0.31.4/NumPy 2 与 IsaacLab NumPy `<2` 冲突。
- Runtime gates: 64-env CLI train/1 update 通过并生成 manifest/status；model_499 完整 eval 生成全部产物，抽帧确认机器人可见；pure tests `3 passed`、Ruff/format/uv lock/diff checks 通过。
- Docs/scope: 新增 `docs/experiment_tooling.md` 并更新 README；未实现 Viser/MuJoCo sim2sim，未修改资产/YAML/USD，未开始 legacy reward finetune。

## 2026-07-11 — collision-only USD 策略回放可视化

- Play CLI: `scripts/rsl_rl/play.py` 新增 `--show_colliders`；环境创建后将 PhysX `SETTING_DISPLAY_COLLIDERS` 设为 `2`（All），使 collision-only SerialLeg 在普通策略回放窗口中可见。
- Runtime: 关闭旧的不可见 play，使用 `DISPLAY=:20`、1 env、CUDA 和 `model_499.pt` 重启；日志确认 collider visualization 与 checkpoint 加载，Isaac Sim GUI 常驻 PID `6622`。
- Docs/validation: README 增加 collision-only play 命令和说明；远端 Ruff check/format 通过。

## 2026-07-11 — 4096-env/500-iteration 平地训练

- Runtime: 默认 PhysX capacity、4096 environments 完成 500 PPO iterations/49,152,000 steps，训练约 `470.93s`，最终迭代吞吐约 `110,765 steps/s`；运行中显存观测约 4.65 GiB，无 OOM 或异常退出。
- Learning result: mean reward 从启动 gate 的 `0.19` 增至最终 `26.30`，最终 episode length `985.91/1000`；termination time-out/bad-orientation/base-contact 分别为 `0.9981/0.0016/0.0005`，线速度/偏航 tracking reward 为 `0.9382/0.4432`。
- Artifact/scope: 保存 `model_499.pt`。500 轮仅到 velocity curriculum stage 1，push stage 仍为 0，因此可判定已学会当前课程范围的稳定平地运动，不能声称已通过最终高速范围、push robustness、长回放闭链 residual 或 sim2sim。

## 2026-07-11 — 4096-env CUDA 默认容量短训练通过

- Preflight: 远端 RTX 4090 空闲（约 24 GB 可用），数据盘剩余 29 GB，无并行训练进程；项目 clean `main@efa13d9`。
- Runtime: 使用默认 PhysX capacity 直接启动 4096 environments，完成 24 steps/env、总计 98,304 samples 和 1 PPO update，退出 0；吞吐约 `35,871 steps/s`，生成约 4.44 MB `model_0.pt`。
- Scope: 证明 GPU 空闲时 4096-env 默认容量可启动并完成短训练；未采集运行中峰值显存，也未完成多 iteration、push curriculum、长 rollout、termination 分布趋势或 fixed-tendon enabled/disabled A/B。

## 2026-07-11 — PPO rollout 改为 24 steps

- Config: 按用户要求将 `PPORunnerCfg.num_steps_per_env` 从 64 改为 24，并同步将 command/push curriculum 的 `steps_per_policy_iteration` 改为 24，保持课程阶段仍按 PPO iteration 计数。
- Runtime validation: 远端 4-env CPU/headless 完成 24 steps/env、总计 96 samples 和 1 PPO update，退出 0；actor/critic 仍为 34D/40D，9 个官方 reward 与 curriculum 正常加载。
- Scope: README 和 handoff 已同步；未修改资产/YAML/USD、奖励权重、PPO 其他超参数或目标规模 PhysX capacity。

## 2026-07-11 — Feed-forward MLP/PPO 与 checkpoint round-trip

- Policy: 按用户决定移除 GRU 迁移方向，`rsl_rl_ppo_cfg.py` 改用新版分离式 `RslRlMLPModelCfg`；actor/critic 均为 `[512,256,128]` + ELU，actor 34D/normalization off/scalar Gaussian std 1，critic 40D/empirical normalization on。
- Runner/PPO: 本次初始实现使用 64-step rollout 对齐 curriculum，后续已按上方新记录改为 24；默认 5000 iterations、每 500 保存。PPO 对齐 Kyber 基础值：clip `0.2`、entropy `0.01`、5 epochs、4 mini-batches、adaptive lr `1e-3`、gamma/lam `0.99/0.95`、KL `0.01`、grad norm `1.0`。
- Runtime validation: 远端 4-env CPU simulation 完成 256 steps 和 1 PPO update，模型结构与 normalization 实际解析正确并生成 `model_0.pt`；第二次训练成功加载该 checkpoint 并继续完成 1 update。
- Docs/scope: README 和 handoff 已记录 MLP/PPO 合同、验证命令、旧 GRU checkpoint 不兼容及下一步；未改资产/YAML/USD，未做目标规模 CUDA 训练或长 rollout。

## 2026-07-11 — 非跳跃基础环境语义与官方 locomotion rewards

- Commands: 新增 IsaacLab `VelocityHeightCommand`，严格输出 legacy 8D；当前 pitch/roll 与 jump 3D 恒零，height `[0.20,0.32] m`，速度范围按 `0/400/800/1200/1600/2000` policy iteration 扩展并施加差速轮速预算。删除 observation 的缺 term 全零 fallback。
- Official reward bridge: 新增内部 `PlanarVelocityCommand`，只把同一 command 映射为 `[vx,0,yaw]`；9 个 reward term 直接引用 IsaacLab 官方 tracking/velocity/torque/acceleration/action-rate/orientation/contact 函数，未配置旧 flat 自定义 reward。
- Environment semantics: 接入官方 material、base mass/COM、policy actuator gain randomization，xy/yaw reset、standing joint reset、课程化 interval push；termination 使用官方 timeout、bad orientation 和 base contact。
- Gates: task smoke 新增 strict command、差速预算、manager function identity、课程终态与固定状态 tracking reward 检查；CPU 1/4-env 8+8、compact-CUDA 1/4-env 4+4 均通过，passive effort 为 0，loop residual `<4.624e-4 m`。
- Scope: 未修改资产/YAML/USD 或旧自定义 reward。1-env CPU 64+64 零动作旧 gate 会触发新 termination，因此默认 smoke 改为 8+8；长 rollout 留给有策略控制的训练验收。

## 2026-07-11 — 固化 `WIN-46S653M0DI0` 的 GPUFree 执行环境

- Machine mapping: 本机名 `WIN-46S653M0DI0` 时，默认使用 SSH alias `se3_rl_lab_gpufree`；实际 endpoint、私钥和凭据只留在本机 SSH 配置。
- Remote setup: 两个 sibling 仓库位于 `/root/gpufree-data/se3-workspace/`，项目/IsaacLab 分别固定为 `01e1c1a`/`b4c3210`；`.venv` 已按 lock 完整同步。
- Network: 保留本机代理 `127.0.0.1:7897` → 远端 `127.0.0.1:7890` 的 reverse forward；为 PyTorch/NVIDIA/PyPI 大包补充直连域名经验。GUI 通过本机 `3000` → 远端 Selkies `3000` 的 local forward。
- Runtime: RTX 4090 CUDA matrix、Isaac Sim headless SerialLeg smoke、`Xorg :20` NVIDIA OpenGL 与 Isaac Sim GUI window 均通过。
- Documentation: 更新 handoff index、snapshot、workspace、decisions、validation、risks 和 backlog；未修改任务源码、资产、依赖或远端环境。

## 2026-07-10 — handoff 改为 Git 跟踪

- Scope: 按用户要求删除 `.gitignore` 中 `AGENT_HANDOFF.md`、`AGENT_SESSION_PROMPTS.md`、`.agent-handoff/` 三项规则；本轮将首次提交完整 multi-document handoff，支持另一台电脑直接恢复。
- Safety: 发布前凭据模式扫描通过；未发现 token、私钥或 API key。历史绝对路径仅用于验证证据，不参与运行配置。
- Publication scope: 与 sibling-relative IsaacLab sources、README 非跳跃基础奖励范围和跨机安装说明作为同一变更集；任务源码、资产与环境 cfg 不在范围内。

## 2026-07-10 — 移除 IsaacLab 用户目录绝对路径

- Portability: 将五个 `[tool.uv.sources]` 从 `/home/am345/IsaacLab/source/...` 改为 sibling editable paths `../IsaacLab/source/...`，刷新 `uv.lock`；tracked 配置与 lock 不再包含用户目录绝对路径。
- Rejected attempt: 曾将五个 package 固定到官方 Git commit 的 monorepo subdirectories；`uv lock/sync` 可完成，但 AppLauncher import 因 wheel 缺少相邻 `config/extension.toml` 失败，因此未保留该方案。
- Validation: 相对路径方案的 `uv lock --check`、真实 `uv sync --locked`、`git diff --check` 和 unbuffered AppLauncher registry probe 均通过；task 为 `SerialLeg-Flat-ClosedChain-v0`。README 已记录 sibling clone、IsaacLab commit 和 portable VSCode 设置。

## 2026-07-10 — 基础 locomotion reward 与非跳跃阶段范围确认

- Decision: 基础迁移验收阶段只配置 IsaacLab 官方 manager-based locomotion rewards，先验证 SerialLeg 在 Isaac Sim 下的物理与训练链路；旧 flat 自定义奖励统一推迟到 finetune。
- Jump boundary: 当前不迁移跳跃；`velocity_height` 接入后仍使用严格 8D 合同，但 jump command 默认关闭、末 3D 保持零，不接入跳跃奖励、事件或 curriculum。
- Documentation only: 更新 README 与 handoff 的 snapshot/decisions/backlog/risks/work-log；未修改任务源码、奖励实现或环境配置，未运行 runtime 测试。

## 2026-07-10 — 合并 PR #4

- Preflight: PR #4 head 固定为 `554af978bd8d8623193b818ee86f6b55bc849cde`，状态 `MERGEABLE/CLEAN`，无 pending/failing checks 或 review blocker。
- Mutation: GitHub App 的 ready mutation 因 integration 403 失败，按 plugin fallback 使用已认证 `gh` 标记 ready，并用 `--match-head-commit` 执行 squash merge。
- Result: PR #4 已 MERGED，merge commit `c9233d5d5749945e1649b8c09e6becb607841f86`；远端发布分支已删除。本地 `main` 已 fast-forward，与 `origin/main` SHA 一致且 tracked status clean。
- Cleanup note: squash merge 后原 `554af97` 不在 `main` 祖先链，普通 `git branch -d` 拒绝删除本地发布分支；未使用强制删除，分支仅本地保留。

## 2026-07-10 — 发布 delayed action / observations draft PR

- Branch/commit: 从同步的 `main=f4e1121` 创建 `agent/migrate-delayed-action-observations`，显式暂存本轮 7 个文件并提交 `554af97 Migrate delayed action and observations`。
- Push: 远端同名分支已创建并设置 upstream；本地 HEAD、远端 branch 均为 `554af978bd8d8623193b818ee86f6b55bc849cde`，tracked status clean。
- PR: GitHub App 创建因 integration 403 失败，按 `github:yeet` fallback 使用已认证 `gh` 创建 draft PR #4：`https://github.com/am345/se3_rl_lab/pull/4`。PR 为 `OPEN/MERGEABLE`、base=`main`、head branch/SHA 正确、当前无 checks。
- Scope: 仅发布 delayed action、34D/40D observations、task smoke、聚焦测试和 README；本地私有 handoff 文件未进入 commit。未标记 ready、未合并。

## 2026-07-10 — delayed 6D action 与 34D/40D observations 迁移

- Action: 新增 IsaacLab `SerialLegDelayedAction`，恢复旧 flat 的腿位置 `0.25 rad` / 轮速度 `45 rad/s` policy 接口；policy order 从新 contract 派生，左右 active-tendon coordinate、上下 clamp、逐环境 physics-step FIFO 和 partial reset 均有 runtime probe。
- Observation: 新增 actor 34D / critic 40D 精确布局、旧 scale、finite clamp、leg sin/cos phase + active angle、last clipped policy action、wheel force 和 flat base height；显式 policy joint selection 防止 passive/virtual-root 泄漏。
- Transitional boundary: command term 未迁移时 8 个 command slots 明确为零；term 存在后严格校验 8D。未修改 `robot_config.yaml` 或 USD，避免 asset SHA stale。
- Gates: 新增 `scripts/test_serialleg_observations.py`（4 passed），扩展 task smoke 的 action FIFO/tendon/clamp/reset 与 actor/critic shape gates；CPU 1-env 8+8 和 compact CUDA 1-env 2+2 rollout 均退出 0，passive effort 为 0。
- Docs: README 当时已刷新动作/观测合同；后续 flat commands/events/rewards/terminations/curriculum 与 feed-forward MLP/PPO 现均已完成，见本文件顶部 2026-07-11 条目。
- Follow-up decision: legacy command scale 的合理性审计发现最终 `vx=±2.4 m/s` 会映射为 actor `±4.8`，height 也未中心化；用户决定当前不改，作为低优先级 finetune 项记录，并要求届时一并处理 checkpoint/deploy/sim2sim 兼容。

## 2026-07-10 — PR #3 发布并合并

- 从 `main` 创建 `agent/fixed-tendon-virtual-roots`，提交 `0409fe3 add fixed tendon virtual roots` 并推送。
- 创建 ready PR #3；合并前状态为 `MERGEABLE/CLEAN`，无 required checks 或 review blocker。
- PR #3 已 squash merge 为 `f4e1121`，远端发布分支已删除；本地 `main` fast-forward 后与 `origin/main` 完全一致，tracked status clean。

## 2026-07-10 — viewer 主动杆整周窗口与联合夹角限位

- 将 4 个 leg control 从 standing `±0.35 rad` offset 改为 absolute joint targets；每根杆以 standing angle 为中心覆盖一个完整 `2π` 操作窗口。
- 不添加单杆机械限位；拖动某杆时按该侧 fixed-tendon coefficients 投影 changed target，使 coupled coordinate 保持 `[0, 1.50953527005] rad`。
- 面板新增每侧 target/actual coupled angle；reset/zero 批量恢复 standing targets 并清零 wheel velocities，避免逐 slider callback 的中间投影污染 reset。
- README、headless 240-frame demo 和非 headless 5-frame GUI 启动路径均已同步/验证。

## 2026-07-10 — 方案 B fixed-tendon USD 生成与 CPU runtime 验收

- Decision: 用户验收左右各一个 virtual revolute/mount 的 URDF 方案 B 后，授权生成 USD；该方案现为 canonical/runtime topology。
- Changes: contract 升至 schema v3；USD converter author/校验 2 个 fixed tendon；asset 与三个 smoke 移除旧 11/10 假设，两个 tendon roots 明确不受 actuator 控制。
- Artifact: collision-only USD 为 13 links / 12 tree joints / 2 external loops / 2 fixed tendons、54 mesh + 2 Cylinder，`536323 bytes`，质量 `12.72874553 kg`。
- Runtime: CPU free-space 64 步、完整 Gym task 和 external-loop enabled/disabled A/B 均通过。standing coupled coordinate 保持约 `1.316677 rad`，root drift `8.453e-07 rad`，free-space loop residual `3.111e-07 m`。
- Gate adjustment: 新拓扑下右侧 A/B ratio 为 `412.2x`，默认 ratio gate 从 `1000x` 调整为 `400x`；absolute closed/open gates 保持。

## 2026-07-10 — 发布 SerialLeg runtime/YAML/task gate

- Publish: 从 `main` 创建 `agent/migrate-serialleg-runtime`，将本轮 15 个文件的 USD runtime、Kyber 风格 YAML contract、task reset/contact 和 CPU/CUDA smoke 改动提交为 `b53d5e9 Migrate SerialLeg runtime to validated USD config`，并推送到同名远端分支。
- PR: GitHub App 创建 PR 因 integration 权限返回 403，按 `github:yeet` fallback 使用已认证 `gh` 成功创建 draft PR #2：`https://github.com/am345/se3_rl_lab/pull/2`，base=`main`、head=`agent/migrate-serialleg-runtime`、状态 OPEN。
- Verify: commit 后本地 HEAD 与 `origin/agent/migrate-serialleg-runtime` 均为 `b53d5e9`，tracked working tree clean；PR 元数据核对通过。
- Merge: 用户授权后将 PR #2 标记 ready，并以 head SHA guard 对 `b53d5e9` 执行 squash merge；结果为 `0e0f401`。PR 状态 MERGED，远端发布分支已删除，本地 `main` 已 fast-forward 到 `origin/main`。

## 2026-07-10 — SerialLeg task-level CPU/CUDA gate

- Gate: 新增 `scripts/smoke_serialleg_task.py`，单环境检查 Gym make/reset/short rollout、11 bodies/10 DOFs、6D action order/scale、actuator exact partition、4 passive DOF 零 target/effort、standing reset、finite states、loop residual、root/joint speed 与 ContactSensor force。支持 `--compact-gpu-buffers` 仅用于低显存单环境 gate。
- Task fixes: `UsdFileCfg.activate_contact_sensors=True`，scene 新增 whole-body `ContactSensorCfg`；`EventCfg.reset_scene_to_default` 修复 `env.reset()` 未写回 standing state（原最大关节误差 `1.601 rad`）。
- Kyber comparison: IsaacLab 无 loop residual gate；通用 solver `6/2`，高冲击 Lens recovery/multi-distill 为 `8/4`。MuJoCo closed-chain projection 对 pose residual `>1e-3` 和 velocity residual `>1e-5` 发 warning。用户确定 `dt=0.005`、`decimation=4`；SerialLeg 最终使用 `16/4` solver 和 `1e-3 m` task pose gate。
- Parameter evidence: `8/4 @ 0.005/4` CPU/CUDA zero peaks `1.093e-3/1.148e-3 m` 略超 gate；`16/4 @ 0.005/4` 降为 `3.956e-4/4.756e-4 m`。未采用虽通过但成本过高的 `48/12`，也按用户要求放弃 `dt=0.0025/decimation=8`。
- Final CPU: default buffers，zero/controlled loop `3.956e-4/5.298e-5 m`，contact `117.324/64.981 N`，root linear `0.943/0.017 m/s`，passive effort `0/0`，退出 0。
- Final CUDA: 默认 buffers 在另一 Kyber 4096-env 训练占用 `5300 MiB` 显存时，`mGpuContactPairsDev` 请求 `671088640 bytes` OOM；compact single-env buffers 下 zero/controlled loop `4.756e-4/5.399e-5 m`，contact `118.362/73.374 N`，passive effort `0/0`，退出 0。

## 2026-07-10 — SerialLeg Kyber 风格 YAML contract 迁移

- Config: 用 `assets/robots/serialleg/robot_config.yaml` schema v2 替换 167 行 TOML；集中 robot identity/path、root/standing pose、6D policy order、legs/wheels/passive groups、三个 joint profiles、loop armature 和 USD importer/gates。
- Derivation: `serialleg_contract.py` 从 canonical URDF 解析 links、tree joint parent/child、damping/friction 和 spherical loop endpoint/local poses；YAML 不再重复这些派生事实。新 loader 强校验 exact keys、numeric/quaternion/path、URDF identity、rooted tree、group exact partition、policy set/order、loop schema 和 importer wheel/collision 不变量。
- Consumers: converter、free/closed-chain smokes、viewer、IsaacLab asset 统一消费 YAML contract；asset init state 现从 YAML 派生完整 root pos/rot。添加显式 `pyyaml` 依赖，package-data 改为 `*.yaml`，README 更新。
- Artifact: 旧 USD 被 path/SHA gate 按预期拒绝；重建后为 `534403 bytes`，11 links/10 tree joints/2 loops/54 meshes/2 cylinders/0 visuals，`--check` 通过。
- Runtime: CPU free-space 64-step residual `3.388e-07 m`；CPU closed-chain A/B 两侧 closed peaks `9.444e-07/2.175e-06 m`，open `0.2584/0.08859 m`，与迁移前一致。
- Packaging: direct wheel 包含 YAML 和新 USD、不包含旧 TOML；临时 wheel/build/egg-info 已清理。

## 2026-07-10 — SerialLeg task asset 入口切换为 USD

- Changes: `assets/robots/serialleg.py` 将 `MjcfFileCfg` 替换为 `UsdFileCfg`，路径从 `SERIALLEG_CONTRACT.runtime_usd` 派生；删除 MJCF importer extension、MJCF 路径常量、custom cloned spawner 及运行时手工创建 spherical loop joints 的代码。
- Preserved: standing pose、policy/passive joint 分组、三个 actuator groups 和 action scale 继续从 contract 派生；USD 内已 authored 的 external spherical constraints 不在 runtime 重建。
- Validation: USD 文件存在；`compileall`、旧入口残留搜索、`git diff --check` 通过；Isaac Sim headless 配置导入输出 `spawn=UsdFileCfg`、`exists=True`和 actuators `('legs', 'wheels', 'closed_chain_passive')`。
- Scope: 按用户要求只完成第 1 步；未运行 `gym.make/reset/step` 或 task-level PhysX smoke。

## 2026-07-10 — 统一 SerialLeg 资产文件 basename

- Rename: canonical MJCF/URDF/USD 改为 `serialleg_closed_chain_complex_collision.{xml,urdf,usd}`；第二个 MJCF 因不能与 canonical 共用 `.xml`，改为 `serialleg_closed_chain_complex_collision_isaaclab_import.xml`。
- References: 更新 MJCF→URDF/USD converters、contract、asset config、smoke、`.gitignore` 和 `.gitattributes`；进一步将两个 MJCF model、URDF robot、contract robot_name、converter gates 和 USD default prim 全部迁移为新名。业务源码中旧名称引用为 0。
- Rebuild: canonical URDF SHA `280d74c4...dd3e`；USD `534455 bytes`，default prim `/serialleg_closed_chain_complex_collision`，54 meshes/7102 faces/2 cylinders/0 visual。
- Validation: URDF/USD `--check`、CPU 64-step asset smoke、CPU closed-chain A/B、viewer `both` demo、Ruff/py_compile/diff check 全通过；残差与重命名前一致。
- Publish: commit `03c3ab6` 经 draft PR #1 发布；PR 随后标记 ready 并 squash merge 为 `42b0973 Unify SerialLeg asset naming (#1)`。本地/远端 `main` 已同步，发布分支已删除。

## 2026-07-10 — Force-push 重写 GitHub main

- Preflight: 本地 HEAD `72a2cd8`、工作树干净、恢复 bundle 验证通过；只读远端 SHA 仍为预期旧值 `87e145a`，无并发提交。
- Mutation: 执行精确 `--force-with-lease=refs/heads/main:87e145a...`，GitHub 返回 `87e145a...72a2cd8 main -> main (forced update)`；随后 fetch 并恢复 `main -> origin/main` upstream。
- Verification: `git ls-remote`、本地 HEAD、`origin/main` 和全新单分支 clone HEAD 均为 `72a2cd89552a0041111e2edfcbbc1c0a4c198c12`。远端新 clone `.git=516778 bytes`、worktree `1595755 bytes`、total `2112533 bytes`、pack `461.36 KiB`。
- Cleanup: 删除 `/tmp/se3_rl_lab_remote_verify` 与 clone log；保留旧历史 recovery bundle。

## 2026-07-10 — 本地 Git 历史重写与对象压缩

- Backup: 创建并验证 `/tmp/se3_rl_lab_pre_rewrite_87e145a.bundle`，`61899823 bytes`，包含旧 main、origin/main 与 Codex checkpoint refs 的完整历史。
- Rewrite: 将已验证的当前 index tree `a2475bf...` 写成无父 root commit `72a2cd89552a0041111e2edfcbbc1c0a4c198c12`，替换本地 `main`；删除旧 `refs/codex/*`、本地 `refs/remotes/origin/main`，解除 upstream。
- GC: 执行 `git reflog expire --expire=now --all` 和 `git gc --prune=now --aggressive`。最终 `.git` 从 `70987926` 降至 `1110734 bytes`；pack objects `461.35 KiB`，unreachable objects=0，commit_count=1，root parent count=0，工作树干净。
- Size: committed snapshot `1595755 bytes`；最终工作区排除 `.git/.venv` 为 `1692600 bytes`；整个目录为 `19358001643 bytes`，主要是未纳入 Git 的 `.venv`。
- Remote boundary: 只读 `git ls-remote` 显示 GitHub `main` 仍为旧 `87e145a`；未获独立 force-push 授权，因此未修改远端。

## 2026-07-10 — 执行 collision-only mesh 瘦身

- Changes: 从 canonical 与 IsaacLab-import MJCF 删除 23 个 visual mesh assets/geoms；MJCF→URDF gate 改为 0 visual/54 collision meshes；contract 允许 `expected_visual_count=0`；USD converter/README/package-data 同步为全链 collision-only。删除 253 个非闭包 mesh（`241018421 bytes`）和 3 个旧 surrogate/fidelity MJCF。
- Artifacts: 重建 URDF SHA 为 `60719e0d...b36c`；重建 USD 为 `534446 bytes`，仍是 54 mesh/7102 faces/2 cylinders/0 visual。mesh 树从 307 文件/`241378057 bytes` 降至精确 54 文件/`359636 bytes`，整个 `serialleg/` 为 `962770 bytes`。
- Validation: canonical/import MJCF/URDF 引用集合与磁盘 54 文件完全相等；URDF/USD `--check`、CPU free/ground、CUDA ground、CPU/CUDA closed-chain A/B、viewer 240-frame demo、Ruff/py_compile/diff check 全通过。direct wheel `309906 bytes`，只包含 54 个 STL。
- Cleanup: 删除本轮产生的 `build/`、egg-info、Ruff/Python cache、`/tmp/serialleg*` logs 和临时 wheel。
- Scope: 未切换 task runtime；下一步仍是将 `serialleg.py` 改为 `UsdFileCfg` 并做 task-level gate。

## 2026-07-10 — SerialLeg mesh 精确引用审计

- Objective: 在删除 mesh 前建立现存 MJCF、canonical URDF、源码和打包路径的精确引用闭包。
- Result: mesh 树共 307 文件/`241378057 bytes`；canonical 链 77 文件/`117809618 bytes`，拆分为 54 collision/`359636 bytes` 与 23 visual/`117449982 bytes`；所有现存 MJCF/URDF 均不引用的安全删除集合为 213 文件/`6062061 bytes`。旧 surrogate/fidelity 模型还独占引用 17 文件/`117506378 bytes`。
- Recommendation: 采用 collision-only canonical 链，保留 32 个 base collision、6 个 `sw_collision_v3` leg collision 和 16 个 `leg_coacd_v1` mesh；删除 visual/旧模型/无引用 mesh 后重建 URDF/USD 并重跑静态、CPU/CUDA 和 GUI gates。该方案需用户确认后执行，本轮尚未删除 mesh。

## 2026-07-10 — 清理安全中间产物

- Objective: 在不触碰 SerialLeg 交付文件和 mesh 资产的前提下，删除已确认可再生的构建、缓存和临时验证产物。
- Changes: 删除 `source/se3_rl_lab/build/`、`dist/`、仓库内（排除 `.venv`）全部 `__pycache__/`、`.ruff_cache/`，以及 24 个 `/tmp/serialleg*` 文件。
- Result: 清理前合计约 `299 MB`；清理后上述目录/文件均无残留，Git 状态中的 9 个新增交付文件与原有源码修改保持不变。
- Next: 单独盘点 `serialleg/meshes/` 的引用闭包，先给出 mesh 保留/删除建议，不直接删除。

## 2026-07-10

- Objective: 将 collision viewer 升级为同时支持 collision 目视验收和主动关节/闭链约束交互验收的 GUI 工具。
- Changed files/config:
  - `scripts/view_serialleg_collisions.py`: 从 `serialleg_contract.toml` 加载 joint groups/default pose/loop frames/actuator settings；54 mesh + 2 cylinder preview 改为挂在对应刚体下的 render-only children，使其自动跟随机构运动。新增 omni.ui 面板：4 active leg position offsets、2 wheel velocities、reset/zero、4 passive positions、2 loop residuals/status。viewer 默认 fixed base，可 `--floating-base`；`--demo-motion` 支持自动动画和 bounded headless gate。headless 模式不强制导入未加载的 `omni.ui`。
  - `README.md`: 记录滑块语义、passive/residual 面板、reset/zero、fixed/floating base 和 demo-motion 命令。
- Result: 静态 render 5-frame 通过；CPU render demo 240-frame 通过，max residual `1.122e-04 m < 2e-04 m`，leg/wheel/passive motion `1.768/2.734/1.841 rad`；`both` demo 30-frame 通过；GUI 在修正 Isaac Sim 5.1 `ui.Label` API 后成功创建，实际交互后正常退出并记录 residual `1.069e-04 m`、leg/wheel/passive motion `1.592/0.6732/1.401 rad`。
- Scope boundary: 滑块命令、fixed base 和 preview children 只存在 viewer runtime stage，不修改磁盘 USD/task，也不代表未来 task action 语义。

- Objective: 在 task runtime 切换前定量验收两条 external spherical joints 的动态闭链效果。
- Changed files/config:
  - `scripts/smoke_serialleg_closed_chain.py`: 新增 CPU/CUDA A/B gate；同 stage 生成 `Closed` 与仅运行时禁用 loop joints 的 `OpenControl`，向四个 endpoint bodies 施加相同的成对反向 5 N 周期力/力矩，跟踪逐 loop residual、关节运动和有限状态。默认 gate 为 closed `<2e-5 m`、open `>1e-3 m`、ratio `>1000x`、joint motion `>1e-3 rad`。
  - `README.md`: 增加 CPU/CUDA closed-chain-effect 命令、A/B 设计与阈值说明。
- Result: CPU closed peaks `9.444e-07/2.175e-06 m`、open `0.2584/0.08859 m`、ratios `273651x/40732x`；CUDA closed `2.104e-06/5.765e-06 m`、ratios `122810x/15367x`；closed 关节运动约 `0.806 rad`。最终收紧阈值后 CPU/CUDA 均退出 0。
- Scope boundary: 未修改磁盘 USD 或 task runtime；`OpenControl` 禁用 loop 只存在于运行 stage。当前 gate 为无重力/无地面外力激励，不代表主动 actuator+接触+长 rollout/多环境已通过。

- Objective: 完成 SerialLeg USD 地面接触力 smoke，验证 custom wheel Cylinder 和 mesh-backed body 的 CPU/CUDA contact tensor。
- Changed files/config:
  - `scripts/smoke_serialleg_usd.py`: 新增 `--ground-contact`；默认生成 ground plane、从 `0.24 m` 运行 400 步，启用全部 11 刚体 ContactReporter，静态强制两轮各有一个 direct `Cylinder`、拒绝 `collisionApproximateCylinders=True`，跟踪逐 body `net_forces_w` 峰值，要求两轮和至少一个 mesh-backed body 均 `>=1 N`。free-space/ground 默认 residual gates 分别为 `1e-5/2e-4 m`。
  - `README.md`: 增加 CPU/CUDA ground-contact 命令、验收语义和分开 residual gate 说明。
- Result: CPU 400-step 轮峰值 `128.573/125.795 N`、mesh-backed `base_link=2976.983 N`、residual `9.380e-05 m`；CUDA 轮峰值 `129.882/125.926 N`、`base_link=2960.022 N`、contact tensor 在 `cuda:0`、residual `1.175e-04 m`。两路均退出 0；CPU free-space 回归仍为 `3.388e-07 m`。
- Scope boundary: 未修改 USD/URDF/converter 物理资产或 task runtime；地面 smoke 为独立 asset-level gate，不代表受控站立或长 rollout 已通过。

- Objective: 让 collision viewer 的实体渲染同时支持 wheel `Cylinder`，修复左右轮在默认 `render` 模式中缺失。
- Changed files/config:
  - `scripts/view_serialleg_collisions.py`: preview 收集从仅 `UsdGeom.Mesh` 扩展为 54 个 `Mesh` + 2 个 `UsdGeom.Cylinder`；圆柱副本保留 source radius/height/axis/extent 和 standing world transform，日志分别报告 `preview_meshes` / `preview_cylinders`。
  - `README.md`: 明确 viewer 实体模式覆盖 54 mesh + 2 wheel cylinders，统一使用 collision geometry 描述。
- Result: Ruff format/check、`py_compile`、`git diff --check` 通过；5-frame CPU/headless `render` gate 退出 0，报告 11 bodies/10 DOFs、`preview_meshes=54 preview_cylinders=2`。
- Result update: 修正后 GUI `render` viewer 已交互式启动，运行时同样报告 `preview_meshes=54 preview_cylinders=2`；等待用户目视验收 wheel 实体。
- Scope boundary: 只修改 viewer 临时渲染 stage 和文档；未修改 USD 物理资产、URDF、converter 或 task runtime。

- Objective: 参考 Kyber `convert_usd.py`，将 SerialLeg joint/importer/runtime 参数收敛为单一声明式 contract，并保持现有 USD 物理策略。
- Changed files/config:
  - `assets/robots/serialleg/serialleg_contract.toml`: 新增 schema v1，声明资产路径、11-link/10-tree-joint/2-loop topology、6D policy order、4 passive joints、standing pose、source dynamics、armature、三组 actuator/action scale、importer 设置和 USD gate。
  - `assets/robots/serialleg_contract.py`: 新增纯 Python dataclass loader；严格验证 keys/types/finite values、rooted tree、loop endpoints、actuator exact partition、policy order、wheel cylinder 和 collision-from-visuals 不变量。
  - `scripts/convert_serialleg_urdf_to_usd.py`: topology/dynamics/importer/gate 常量改由 contract 派生；USD metadata 新增 contract path/SHA，并在 `--check` 中验证 SHA/importer/loop-armature metadata。
  - `assets/robots/serialleg.py` / `se3_rl_lab_env_cfg.py`: default pose、joint groups、actuator 参数和 action scale 改由 contract 派生；旧 MJCF helper 的 loop local poses 也改为 contract 数据，但 task 尚未切换 spawner。
  - `source/se3_rl_lab/{pyproject.toml,setup.py}` / `README.md`: 打包 TOML，统一 Python 3.11 合同并新增中文 contract 文档。
- Result: contract probe 报告 11/10/2、policy 6、passive 4；asset probe 的三组 actuator/action scale 与原值一致。USD 重建为 `534788 bytes`，`--check` 与 64-step CPU smoke 通过，residual 保持 `3.388e-07 m`。direct wheel 包含 loader/TOML/USD。
- Scope boundary: 未把 `SerialLeg-Flat-ClosedChain-v0` 切换到 USD，未恢复 fixed-tendon/contact semantics，也未修改训练 observation/reward/PPO。

- Objective: 将 collision-only USD 的 Isaac Sim 查看体验从绿色物理线框改为默认实体预览。
- Changed files/config:
  - `scripts/view_serialleg_collisions.py`: 新增 `--view-mode {render,collision,both}`，默认 `render`。PhysX collider mesh 在 overlay 关闭时会被 viewport 隐藏，因此 viewer stage 内按 standing world transform 从 54 个 collision meshes 创建无物理 API 的 render-only preview copies，并绑定蓝灰 `UsdPreviewSurface`/dome/key lights；不修改 runtime USD 或其磁盘体积。`both` 保留实体加 PhysX overlay，`collision` 保留原纯调试行为。
  - `README.md`: 记录三种 viewer 模式和命令；明确实体预览是 collision mesh，不是已移除的原始高模 visual。
- Result: `render`、`both` 各通过 CPU/headless 5-frame 启动 gate，均报告 11 bodies/10 DOFs 和 `preview_meshes=54`。
- Result update: 用户已确认 Isaac Sim GUI collision 视觉效果验收通过。
- Remaining work: 若需要原始贴图/高模外观，应另建不用于训练的简化 visual preview asset。

- Objective: 修复 collision-only USD 在 Isaac Sim GUI 中只显示 wheel ring 的问题。
- Changed files/config:
  - `scripts/convert_serialleg_urdf_to_usd.py`: flatten 后在可编辑的 `Flattened_Prototype` prim 上，将 54 个 STL collision 的 `CollisionAPI`/`MeshCollisionAPI` 从 importer wrapper `Xform` 迁移到实际 `Mesh` leaf；复制 `collisionEnabled=true` 和 `convexHull` approximation，删除 wrapper API。静态 gate 现强制 54 个 direct mesh collider、0 non-geometry wrapper collider、direct API enabled、`convexHull`。
  - `assets/robots/serialleg/usd/serialleg_closed_chain_v3_train_obb_trim.usd`: 重建为 `534493 bytes` 的 collision-only crate。
- Result: 磁盘 `--check` 通过；独立 schema 检查报告 `direct_mesh_colliders=54`、`wrapper_colliders=0`、approximation=`convexHull`；64-step CPU free-space smoke 仍为 `3.388e-07 m` residual；collision viewer headless 5 frames 通过。
- Remaining work: 用户需重新启动 GUI viewer 做最终目视确认；仍需地面接触 smoke 证明接触响应。

- Objective: 诊断用户在 Isaac Sim collision viewer 中只看到两个绿色轮环、画面怪的原因。
- Changed files/config:
  - `.agent-handoff/snapshot.md` / `.agent-handoff/work-log.md` / `.agent-handoff/validation.md` / `.agent-handoff/backlog.md` / `.agent-handoff/risks.md`: 记录 viewer 目视验收失败原因和后续修正方向。
- Evidence: 用户截图只显示左右 wheel collider；USD schema 检查显示 2 个 direct `Cylinder` collider，而 54 个 mesh collision 为 `Xform` prim 上的 `PhysicsCollisionAPI,PhysicsMeshCollisionAPI`，`physics:approximation=convexHull`，其子 `Mesh` active 且有点面但自身没有 `CollisionAPI`。PhysX/viewport collider overlay 当前只可靠显示了 direct primitive cylinder。
- Result: 结论不是 mesh 太大或相机错位，而是当前 importer/flatten 后的 mesh collider schema 与 viewer overlay 显示路径不匹配；当前 GUI 不能作为 54 个 mesh collision 的目视验收。
- Scope boundary: 未修改 converter、USD、viewer 脚本或训练 task；只做只读诊断与 handoff 记录。

- Objective: 提供可交互 Isaac Sim collision viewer，让用户目视核对 collision-only USD。
- Changed files/config:
  - `scripts/view_serialleg_collisions.py`: 新增 GUI/CPU viewer，加载已验证 USD，使用 standing joint state 和 `0.22 m` root height，禁用重力以保持姿态；通过官方 `physx_bindings.SETTING_DISPLAY_COLLIDERS=2` 自动打开全部 colliders，可选 `--show-joints`，`--frames` 支持 bounded gate。
  - `README.md`: 新增 viewer 命令、Eye 菜单路径和 collider 颜色说明。
- Result: Ruff/语法/whitespace 通过；`--headless --device cpu --frames 5` 报告 11 bodies/10 DOFs 并 exit 0。默认 GUI 命令已启动且进程保持运行，关闭 Isaac Sim 窗口即退出。
- Scope boundary: 未修改 USD、`serialleg.py`、env cfg 或训练 task。

- Objective: 完成并小型化第二阶段 `开链树形 URDF + spherical loop_joint → Isaac URDF importer → 树形 Articulation + 外部闭环约束 USD`，最终 USD 只保留 collision，不切换训练 task。
- Changed files/config:
  - `scripts/convert_serialleg_urdf_to_usd.py`: canonical URDF 仍保留 23 个 visual meshes；导入前临时替换成 11 个透明 `1e-6 m` dummy spheres，显式 `collision_from_visuals=False`，导入后用 inactive overrides 屏蔽 11 个 `visuals` scopes，再 flatten。新增 canonical layer documentation，清除语义可见 `/tmp` provenance，并强化 collision-only gate：54 meshes/7102 faces/21306 points+indices、2 cylinders、56 CollisionAPI、54 MeshCollisionAPI、0 active visual、0 orphan non-collision prototype、`<5 MiB`。
  - `scripts/smoke_serialleg_usd.py`: 新增默认 CPU/headless bounded PhysX smoke，严格检查 11 bodies/10 DOFs、全部 state finite、两条 attachment residual 和 `1e-05 m` threshold；进程级退出规避当前 inotify 耗尽导致的 Kit teardown 卡住。
  - `.gitignore` / `.gitattributes`: 为该小型 runtime USD 添加精确普通 Git exception；其他 USD 继续默认 ignore/LFS。
  - `README.md`: 记录 collision-only workaround、查看 collision 的方式、`~522 KiB` 与 `<5 MiB` gate，并刷新下一步迁移顺序。
  - `assets/robots/serialleg/usd/serialleg_closed_chain_v3_train_obb_trim.usd`: 最终 self-contained crate `534237 bytes`，SHA256 `1f60ac375785e14ffbb83f460742c29144dcdab1637b15f57ded87deea729523`，相对 full-visual 版本缩小 `99.6851%`。
- Result: 磁盘 gate 证明 default prim/root、11 rigid bodies、10-tree-joint connected graph、2 exact spherical loops、authored exclude、armature/damping/neutral drive、continuous limits、collision-only geometry、mass/units/dependencies均正确。CPU smoke 64 步报告 10 DOFs、max residual `3.388e-07 m`，没有 `closed articulation` 或非有限状态。
- Packaging/result: direct wheel 构建通过，wheel `63284796 bytes`，包含 `27399-byte` URDF 和 `534237-byte` USD。wheel 仍约 61M，来源是 package-data 中完整源 mesh 树，不是 runtime USD。
- Scope boundary: 未修改 `serialleg.py`、env cfg 或 task 注册；现有 task 仍走旧 MJCF custom spawner。fixed-tendon coupled limits、contact/equality solver 语义、地面/主动控制/长 rollout 稳定性留给下一阶段。

- Objective: 完成 SerialLeg 迁移第一阶段：`闭链 MJCF → 开链树形 URDF + spherical loop_joint`，本轮不生成 USD、不改任务运行时。
- Changed files/config:
  - `scripts/convert_serialleg_mjcf_to_urdf.py`: 新增 stdlib-only 确定性转换器、`--check` 模式，以及源模型/拓扑/mesh/惯量/geom/frame/loop residual 强校验。
  - `source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg/urdf/serialleg_closed_chain_v3_train_obb_trim.urdf`: 新增 11-link/10-tree-joint/2-spherical-loop-joint canonical 产物；保留 77 mesh refs 和精确惯量/geom frame，并为后续 USD postprocess 记录 deferred MJCF 语义与 armature 元数据。
  - `source/se3_rl_lab/pyproject.toml` / `source/se3_rl_lab/setup.py`: 将 `assets/robots/serialleg/urdf/*.urdf` 纳入 wheel package data。
- Result: 转换器生成与 `--check` 均通过；零姿态 closure residual 为 `0`，standing 最大为 `2.197e-07 m`。Isaac Sim 5.1 `URDFParseFile` 成功解析 11 links/10 joints，并明确识别两条 spherical loop joints。直接 wheel 构建通过且包含 URDF。
- Scope boundary: 未生成/保存 USD，未修改 `serialleg.py`、环境 cfg、MJCF 或 task 注册，未运行 SerialLeg PhysX smoke。fixed tendon limits、armature、contact/solver、spatial tendon 和 keyframe 留给后续 USD/运行时阶段。
- Remaining risks: importer-generated USD 的 `physics:excludeFromArticulation`、loop local frames、deferred semantics 和长期约束稳定性尚未验证；完整 sdist build 另有既存 `config/extension.toml` 缺包问题。

- Objective: 只读核对 Kyber 真闭链实现，并按用户确认记录 SerialLeg 下一阶段资产迁移方案；不修改实现。
- Changed files/config:
  - `.agent-handoff/snapshot.md`: 将当前目标和下一步改为“闭链 MJCF → 开链树形 URDF + loop_joint → importer-generated external constraints USD”，并注明实现暂停。
  - `.agent-handoff/decisions.md`: 收窄旧的“闭链不可行”结论，记录 Kyber 风格真闭链管线为主路线。
  - `.agent-handoff/backlog.md` / `.agent-handoff/risks.md`: 写入 URDF 转换、USD 静态 gate、单环境 runtime gate 及转换/稳定性风险。
  - `.agent-handoff/validation.md`: 记录 Kyber 静态核对证据和本轮有意未运行仿真。
- Evidence: K1/Lens/K2 canonical URDF 使用 `<loop_joint type="spherical">`；实际 USD loop prim 均为 `PhysicsSphericalJoint`，authored `physics:excludeFromArticulation=True`、`physxJoint:armature=0.005`。训练侧加载预生成 USD 并只对 active joints 建 actuator；MuJoCo 的 `<equality><connect>` 与 reset projection 是独立路径。当前 SerialLeg 手工 loop-joint spawner 未设置 exclude flag。
- Result: 用户确认后续应先把 MJCF 拆成开链 URDF，再由外部闭环约束闭合；本轮只更新本地 handoff 记忆，未改源码、资产、依赖或 Git 跟踪文件，未启动 IsaacSim/PhysX 仿真。
- Remaining risks: SerialLeg URDF 尚未生成；site-pair 局部 pose、树内 DOF、exclude flag、armature 和闭环稳定性仍需在用户授权后依次通过静态与单环境 CPU gate。

## 2026-07-09

- Objective: 写好交接文档并提交推送首个代码版本。
- Changed files/config:
  - `.gitattributes`: 移除 `*.obj` 的 Git LFS 规则，避免 GitHub LFS 配额阻塞当前 SerialLeg OBJ mesh 上传。
  - Git branch/history: 本地分支改为 `main`，首个提交 amend 为 `87e145a Initialize IsaacLab SerialLeg migration`。
  - `.agent-handoff/snapshot.md` / `.agent-handoff/work-log.md` / `.agent-handoff/validation.md` / `.agent-handoff/decisions.md` / `.agent-handoff/risks.md` / `.agent-handoff/backlog.md`: 记录提交、推送和 LFS 决策。
- Result: `main` 已成功推送到 `https://github.com/am345/se3_rl_lab.git` 并跟踪 `origin/main`。首次 push 因 GitHub LFS budget exceeded 失败，改为普通 Git 提交 OBJ mesh 后 push 成功。
- Remaining risks: SerialLeg 资产目录约 232M，当前作为普通 Git 文件进入仓库；后续可瘦身到实际需要 mesh 或在 LFS 配额恢复后重新评估资产存储策略。

- Objective: 将本地 Git 仓库关联到用户指定 GitHub 仓库。
- Changed files/config:
  - `.git/config`: 添加 `origin` remote。
  - `.agent-handoff/snapshot.md` / `.agent-handoff/work-log.md` / `.agent-handoff/validation.md`: 记录 remote 状态。
- Result: `origin` fetch/push 均指向 `https://github.com/am345/se3_rl_lab.git`；仓库当前仍未创建首个 commit。
- Remaining risks: 尚未 commit 或 push；远端访问/权限未做网络验证。

- Objective: 按用户要求直接使用 SerialLeg closed-chain MJCF 接入 IsaacLab，并派 subagents 并行调查资产/importer/smoke。
- Changed files:
  - `source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg/`: 从旧仓库复制 SerialLeg 资产；当前完整复制约 232M，闭链 XML 实际引用 77 个 mesh。
  - `source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg.py`: 新增 SerialLeg asset cfg、默认关节姿态、actuators、自定义 MJCF spawner 和 USD loop-joint 尝试。
  - `source/se3_rl_lab/se3_rl_lab/assets/__init__.py` / `assets/robots/__init__.py`: 新增资产包入口。
  - `source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/se3_rl_lab_env_cfg.py`: 从 CartPole 改为 SerialLeg 6D effort action、基础 observation/reward/termination。
  - `source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/__init__.py`: task id 改为 `SerialLeg-Flat-ClosedChain-v0`。
  - `source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/agents/rsl_rl_ppo_cfg.py`: experiment name 改为 `serialleg_flat_closed_chain`。
  - `source/se3_rl_lab/config/extension.toml`: 添加 `isaacsim.asset.importer.mjcf` 依赖。
  - `source/se3_rl_lab/pyproject.toml` / `source/se3_rl_lab/setup.py`: 改为发现子包并包含 SerialLeg XML/mesh package data。
  - `scripts/list_envs.py`: 过滤前缀从 `Template-` 改为 `SerialLeg-`。
- Result: 原始 closed-chain MJCF 不能直接由 IsaacSim importer 转入可训练 Articulation；兼容副本去掉 equality/tendon/site/floor/light 后可导入，手动补 USD loop joints 后又被 PhysX runtime 拒绝为 unsupported closed articulation。当前 `SerialLeg-Flat-ClosedChain-v0` one-shot smoke 未通过。
- Remaining risks: 当前 task 默认仍会尝试补 loop joints 并失败；下一步需要路线决策并可能回退为 surrogate/open-chain 可运行 task。

- Objective: 用户确认接受 EULA 后验证 IsaacSim/模板 task 运行链路。
- Changed files:
  - `.agent-handoff/snapshot.md`: 更新 EULA 后验证状态和 CUDA OOM 阻塞。
  - `.agent-handoff/backlog.md`: 标记 task 注册与 CPU/headless zero agent 验证完成，新增 CUDA OOM 和 inotify 后续项。
  - `.agent-handoff/risks.md`: 记录 EULA 状态、inotify watch 噪声、CUDA OOM 和 CPU fallback。
  - `.agent-handoff/validation.md`: 记录 EULA 后验证命令。
- Result: `OMNI_KIT_ACCEPT_EULA=YES` 下 IsaacSim 能启动；registry probe 确认 `Template-Se3-Rl-Lab-v0` 注册；CPU/headless zero agent 创建环境，打印 `Dict('policy': Box(-inf, inf, (1, 4), float32))` 和 `Box(-inf, inf, (1, 1), float32)` 后进入 simulation loop。
- Remaining risks: CUDA/headless zero agent 因 PhysX tensors CUDA OOM 失败；IsaacSim 启动有大量 inotify watch `errno=28` 日志。

- Objective: 跑通当前 uv 依赖方案的真实 `uv sync`。
- Changed files:
  - `.agent-handoff/snapshot.md`: 更新当前状态、下一步和 EULA 阻塞说明。
  - `.agent-handoff/backlog.md`: 标记真实 `uv sync` 完成，拆出 EULA 后的运行时验证待办。
  - `.agent-handoff/risks.md`: 移除“真实 sync 未运行”风险，记录 EULA/`pxr` import 风险。
  - `.agent-handoff/validation.md`: 记录本次同步和轻量验证。
  - `.agent-handoff/decisions.md`: 修正 handoff 忽略决策并记录本轮先沿用完整 lock 跑通同步。
- Result: `uv sync` 成功创建 `.venv`，安装 247 packages；`uv run python --version` 返回 Python 3.11.15。
- Remaining risks: IsaacSim/IsaacLab 运行时验证需要用户接受 NVIDIA Omniverse EULA；未擅自设置 `OMNI_KIT_ACCEPT_EULA`。

- Objective: 将 handoff 记忆文件加入 `.gitignore`。
- Changed files:
  - `.gitignore`: 添加 `AGENT_HANDOFF.md`、`AGENT_SESSION_PROMPTS.md`、`.agent-handoff/`。
  - `.agent-handoff/snapshot.md`: 标记 handoff memory 已忽略。
  - `.agent-handoff/backlog.md`: 完成 handoff 文件本地私有待办。
  - `.agent-handoff/risks.md`: 移除 handoff 是否提交的未知项。
  - `.agent-handoff/work-log.md`: 记录本次变更。
  - `.agent-handoff/validation.md`: 记录 ignore 验证。
- Result: handoff 记忆文件保持本地私有；`AGENTS.md` 和 `.claude/CLAUDE.md` 仍作为仓库规则文件保留。
- Remaining risks: 依赖策略仍需确认；真实 `uv sync` 尚未运行。

- Objective: 将 README 改为中文项目说明。
- Changed files:
  - `README.md`: 用中文重写官方模板 README，说明当前仓库状态、uv 命令、模板 task、迁移顺序和 Agent 接力入口。
  - `.agent-handoff/snapshot.md`: 更新当前状态和活跃文件。
  - `.agent-handoff/workspace.md`: 更新 README 描述。
  - `.agent-handoff/work-log.md`: 记录本次 README 中文化。
  - `.agent-handoff/validation.md`: 记录 README 复读检查。
- Result: README 已中文化；未改变代码或依赖配置。
- Remaining risks: 依赖策略仍需确认；真实 `uv sync` 尚未运行。

- Objective: 使用 IsaacLab 官方模板创建新仓库，并探索更纯正的 uv 工作流。
- Changed files:
  - `pyproject.toml`: 添加根 uv project、workspace、IsaacLab path sources、Isaac Sim 5.1.0、PyTorch cu128 index、`starlette==0.49.1` override、dev dependencies。
  - `source/se3_rl_lab/pyproject.toml`: 添加 package metadata 和 IsaacLab/RSL-RL 依赖。
  - `.python-version`: 固定 Python 3.11。
  - `.gitignore`: 忽略 `.venv/`。
  - `README.md`: 将官方 pip-style 命令改为 `uv sync` / `uv run`。
  - `uv.lock`: 生成当前锁文件。
- Result: `uv lock --check` 和 `uv sync --dry-run` 通过；未执行真实 `uv sync`。
- Remaining risks: 用户认为当前完整锁 Isaac Sim 方案可能过复杂；下一步应先确认是否简化。

- Objective: 建立持久多文档 Agent 接力机制。
- Changed files:
  - `AGENT_HANDOFF.md`: 创建接力索引。
  - `.agent-handoff/`: 创建结构化接力状态文件。
  - `AGENTS.md`: 如启用，创建或更新 Codex 项目级接力规则。
  - `.claude/CLAUDE.md`: 如启用，创建或更新 Claude Code 项目级接力规则。
  - `AGENT_SESSION_PROMPTS.md`: 创建常用会话恢复、继续、收尾、质量审查提示。
- Result: 初始多文档接力机制已生成。
- Remaining risks: 依赖方案仍需和用户确认；SerialLeg flat 迁移尚未开始。

## Work Log Guidelines

- 这里只保留近期且仍有操作价值的工作。
- 过期或过长历史压缩后移动到 `archive.md`。
- 优先写文件路径和具体结果，少写泛泛总结。
