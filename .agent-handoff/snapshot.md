# Handoff Snapshot

## Current State

- Last updated: 2026-07-14（Asia/Shanghai）
- Workspace: 本机 `/home/am345/se3_rl_lab`；训练机 SSH alias `se3_rl_lab_gpufree`；旧远端根目录 `/root/gpufree-data/se3-workspace/se3_rl_lab` 保持不动，本轮训练使用隔离快照 `/root/gpufree-data/se3-workspace/se3_rl_lab_scale45_std05`。
- Git: 训练合同、评估 telemetry 与压缩课程已通过 PR #10 合并到本地/远端 `main@917b7c5`；submodule 保持 `main@416b534`。未跟踪 `artifacts/` 明确未提交。
- Current objective: 压缩课程实现与发布已完成；下一步等待用户决定何时按新 `2000–2200` 预算启动 fresh training。
- Current status: standard/joint/cache 分别在 iteration `900/700/1600` 达到最终难度，velocity/push 在 `1500/1750` 达到最终范围。28 个聚焦测试、Ruff、64-env Recovery reset smoke 与 4-env flat curriculum smoke 均通过；PR #10 已 merge，远端 `main` 已核对。

## Early-Stopped Scale45/Std0.5 Training

- Run: `2026-07-14_13-56-55_recovery_history5_scale45_std05_fresh_5k`
- Remote root: `/root/gpufree-data/se3-workspace/se3_rl_lab_scale45_std05`；依赖解释器复用旧环境 `/root/gpufree-data/se3-workspace/se3_rl_lab/.venv/bin/python`，并以 `PYTHONPATH=<isolated-root>/source/se3_rl_lab` 锁定本轮源码。
- Contract: `SerialLeg-Recovery-v0`、seed 42、4096 env、5000 iterations、24 steps/env、`resume=false`、wheel scale `45.0`、Recovery Gaussian `init_std=0.5`、actor/critic `138D/168D`。
- Process/log: former PID/SID `2194` 已退出，训练机 GPU 回到约 66 MiB/0%；日志 `/tmp/recovery_history5_scale45_std05_fresh_5k.log`。
- Run directory: `/root/gpufree-data/se3-workspace/se3_rl_lab_scale45_std05/logs/rsl_rl/serialleg_flat_closed_chain/2026-07-14_13-56-55_recovery_history5_scale45_std05_fresh_5k`。
- Stop audit: iteration `3040/5000`、fatal count 0；SIGTERM 停止推进后 Isaac cleanup 未退出，SIGINT 2 秒内正常退出，未使用 SIGKILL。`model_2500.pt`/`model_3000.pt` 均已完整落盘。
- Best checkpoint: local `artifacts/recovery_eval/hard-suite-scale45-std05/model_2500/model_2500.pt`，5,868,725 bytes，SHA256 `3488dfb7f72a41ed5add8c8e7a6a106f9c193a2a3e4f495d434186d909e7f397`；72 tensors/1,461,681 values 全 finite，checkpoint iter 2500。
- Hard-suite result: model2500 1200 steps、0 termination/non-finite；vx/yaw/pitch/target-error/raw-action-delta/saturation 为 `0.16570/0.25178/0.49974/15.756/0.08270/2.46%`。相对同口径旧 model4000 分别为 `-6.0%/+13.0%/-3.8%/-6.8%/-44.0%/-29.8%`。
- Rejected later checkpoint: model3000 同合同 yaw/target-error/raw-action-delta 相对 model2500 恶化 `38.6%/18.2%/62.8%`；不作为最佳，不 resume。
- Recovery benchmark: standard/cache settled success 在 model500/1000/1500/2000/2500/3000 分别为 `0.39/0`、`98.05/98.44`、`99.22/99.61`、`99.61/100`、`98.05/100`、`99.22/99.61`%；当前 root/joint/cache 阈值明显晚于策略能力形成时间。
- Training-time evidence: iteration1000/1500/2000/3040 实测 elapsed `31:01/47:34/1:03:21/1:41:33`；2000 相对原计划5000预计节省约60%，1500约70%。
- Next action: 下一轮 fresh run 使用 `2000–2200` 预算，并在 1000/1500/1800/2000 checkpoint 执行 recovery/tracking/push gates。视觉/部署候选仍暂用 model2500，不能把 recovery-only 最优自动等同于 tracking 最优。

## WebSim Active Boundary

- Main repo owns: SerialLeg canonical MJCF/meshes、`robot_config.yaml`、observation/action/actuator truth、ONNX export metadata 与 launcher/documentation。
- Submodule owns: Python local server、React UI、MuJoCo WASM、ONNX Runtime Web、three.js render、interaction、telemetry 和浏览器 runtime managers。
- Integration contract: `se3_rl_lab.websim.deployment.v1`；禁止 submodule 通过 `../` import 父仓库源码，运行时必须显式接收 `run_root`/`asset_root`。
- Immediate next step: WebSim V2 保持当前版本；训练 GPU 已释放。若需要将新策略接入 WebSim，使用 model2500，不使用 model3000。
- Active WebSim service: 2026-07-14 13:31 重新启动于 exec session `31838`，HTTP/1.1 页面/API 与真实 scale45 runtime canary 均通过。
- Recovery result: 旧 `model_4500.pt` 已由 scale45/std0.5 的 model2500 候选取代；失败 checkpoint 仅保留作历史对照。
- Latest media handoff: 已生成并打开 `artifacts/recovery_eval/model4000-scale45-vs-model4500-scale10-side-by-side.mp4`（左：旧 model4000/scale45；右：当前 model4500/scale10；11.98 s、1280×360@50 FPS、599 frames，SHA256 `dedb56ad...fd2aa`）。旧单片位于 `artifacts/recovery_eval/model_4000-server-scale45/model_4000-scale45-isaac-eval.mp4`，当前单片位于 `artifacts/recovery_eval/model_4500-server/model_4500-isaac-eval.mp4`。

## Historical Incomplete Scale-10/Std-1 Training

- Former PID/session: remote PID `28576` 已退出；当前无该 run 训练进程。
- Log: `/tmp/recovery_history5_wscale10_std1_fresh_5k.log`
- Run directory: `/root/gpufree-data/se3-workspace/se3_rl_lab/logs/rsl_rl/serialleg_flat_closed_chain/2026-07-13_19-43-59_recovery_history5_wscale10_std1_fresh_5k`
- Contract: seed 42、4096 env、5000 iterations、24 steps/env、`resume=false`、save interval 500、wheel action scale `10.0`、Recovery Gaussian `init_std=1.0`、actor groups `command+proprio`、critic `command+privileged`。
- Checkpoints: `model_{0,500,...,4500}.pt` 已落盘；`model_4999.pt` 不存在。最后可用 `model_4500.pt` 为 5,868,725 bytes，SHA256 `168bd10af72c603586bcea760c6608c6ad5f731d48ab804be376d995fc2ed8c4`，本地路径 `artifacts/recovery_checkpoints/history5_wscale10_std1_fresh_5k/model_4500.pt`。

## Historical Local Isaac Sim Play

- Former local PID `888603` 已退出；命令为 `scripts/rsl_rl/play.py --task SerialLeg-Recovery-v0 --num_envs 1 --device cuda:0 --checkpoint .../model_4500.pt --show_colliders`。
- Window: `Isaac Sim 5.1.0`，X11 window `0x320000b`，1440×975，Map State `IsViewable`；本机 RTX 5060 显存约 4,542 MiB。
- Log: `/tmp/recovery_wscale10_std1_model4500_local_play.log`；模型加载成功，actor/critic 138D/168D，无 Traceback/OOM/assertion。既有 inotify `errno=28` watch-limit 噪声仍存在但未阻止 runtime。

## Wheel-Scale-10 / Std-1 Model 1000 Evaluation

- 固定 seed 47、6 scenarios × 4 秒、actor corruption 关闭、`--no-rerun`；actor/critic runtime 输入为 138D/168D。
- MP4 为 H.264 1280×720@50 FPS、1199 frames、23.98 秒、2,774,720 bytes，SHA256 `067276bd6aaeea009175f4213cc7015c236d6d4a8f2dfb0026c6d242ad889ab9`。
- 1200 steps、0 termination/non-finite，velocity/yaw-rate RMSE `0.16569/0.32235`；eval 日志无 Traceback/OOM/assertion/NaN。评估与复制后训练继续到 iteration 1133，显存约 5.0 GiB。

## Superseded Training Stopped By User Request

- Former PID `2577` / run `2026-07-13_17-24-18_recovery_history5_fresh_5k` 已在 iteration 4154/5000 停止，不得 resume 或误写为训练异常。
- 停止前 reward `251.63`、std `0.31`、catastrophic `0`；`model_4000.pt` 为 5,868,725 bytes，SHA256 `8bc4c47067fd4da7076c2d3dd15188efda32a01b15bcb2768e1e5bb4ba938c45`。
- 旧日志 `/tmp/recovery_history5_fresh_5k.log` 与旧 run directory/checkpoints 保留用于历史对比。

## History-5 Model 500 Evaluation

- 对正式 run 的 `model_500.pt` 完成 seed-47、6 场景 × 4 秒固定命令 eval；actor/critic runtime 输入确认 138D/168D，eval actor corruption 关闭。
- 远端 MP4: `isaac_eval/videos/model_500-step-0.mp4`；H.264、1280×720、50 FPS、1199 frames、23.98 s、2,933,035 bytes，SHA256 `0faac91344dae0ee942009f786d0d09ea12f482ff7c20c5695d5e49882799ece`。
- 本地产物: `artifacts/recovery_eval/model_500-history5-recovery-eval.mp4` 与 `model_500-history5.metrics.json`。
- Metrics: 1200 steps、0 termination、0 non-finite、vx/yaw RMSE `0.21508/0.70924`、max loop residual `0.002601 m`。抽取 stand/reverse/yaw_right 帧确认渲染有效，但 stand/yaw_right 可见明显侧倾或倒地；因此当前 `survival_rate=1.0` 只表示没有命中 catastrophic termination，不能解释为稳定站立或 recovery 成功。

## History-5 Model 1000 Evaluation

- 同 seed-47/6×4 秒合同评估 exit 0；MP4 为 H.264 1280×720@50 FPS、1199 frames、23.98 s、2,522,290 bytes，SHA256 `4827d724baabcd7dcd6276f4f2052df0e697e0e6cd2402af7b5616133528ca71`。
- 总 vx/yaw RMSE 从 model500 的 `0.21508/0.70924` 改善为 `0.14640/0.35554`；stand 为 `0.22301/1.08666→0.16683/0.40593`。用户查看并排 MP4 后确认 model1000 抖动已改善。stand base-height 整段去趋势 RMS/p2p 为 `24.68/121.4 mm`，但该口径混入姿态漂移与大幅运动，不能作为高频抖动的否定证据。
- 用户同时判定 tracking 仍然较差，与拆分 telemetry 一致：后半段 yaw-left 均值 `1.325` vs command `1.0`，yaw-right `-1.561` vs `-1.0`，forward-turn `1.050` vs `0.8`；forward/reverse 线速度仍约有 13% 欠冲/过冲。聚合 RMSE 下降只表示相对 model500 改善，不代表 tracking 合格。
- 本地产物：`artifacts/recovery_history5/model_1000-{step-0.mp4,metrics.json,telemetry.json}` 与 `model_500-vs-1000-side-by-side.mp4`。当前 flat-basic telemetry 仍缺 pitch-rate/action/wheel saturation，4–5 Hz 根因对比仍需专用 jitter probe。

## History-5 Model 2000 Evaluation

- 当时最新已落盘 checkpoint `model_2000.pt` 按 seed-47/6×4 秒/actor no-corruption/78° FOV/`--no-rerun` 同合同完成评估，worker exit 0。
- MP4 为 H.264 1280×720@50 FPS、1199 frames、23.98 s、2,353,573 bytes，SHA256 `8b1cd91f19cf1e4a2d8596c75971089001f4c048eb1f1925c5102c3d768e7b22`。本地产物为 `artifacts/recovery_history5/model_2000-{step-0.mp4,metrics.json,telemetry.json}`。
- 1200 steps、0 termination/non-finite、vx/yaw RMSE `0.16774/0.24523`；相比 model1000 的 `0.14640/0.35554`，yaw 聚合改善但 vx 变差，尤其 stand/reverse vx RMSE 为 `0.27276/0.22349`。这些聚合指标不代替用户对抖动与 tracking 的视觉验收。

## History-5 Model 2500 Forward 2 m/s Evaluation

- 不修改生产源码，以独立 custom-eval 目录运行 seed-47 单场景 8 秒固定 command：`vx=2.0 m/s`、yaw 0、height 0.26 m，其余 command 为 0。输出未覆盖标准六场景产物。
- MP4 为 H.264 1280×720@50 FPS、399 frames、7.98 s、1,271,481 bytes，SHA256 `586288bba673076d6fafdb0b0c72f6ea770dc03af3b9b6416e02458626688f2b`。本地产物为 `artifacts/recovery_history5/model_2500-forward-2mps-{step-0.mp4,metrics.json,telemetry.json}`。
- 400 steps、0 termination/non-finite；整段 vx RMSE `1.306 m/s` 包含从静止加速的瞬态，后 4 秒平均 vx `1.9047 m/s`、RMSE `0.0991 m/s`，后 2 秒平均 `1.8967 m/s`。视觉稳定性等待用户验收。

## History-5 Model 3000 Height 0.35 m / Forward 1.5 m/s Evaluation

- 以独立 custom-eval 目录运行 seed-47 单场景 8 秒固定 command：`height=0.35 m`、`vx=1.5 m/s`、yaw 0，其余 command 0。0.35 m 高于训练 `height_range=(0.20, 0.32)` 上限，因此是轻度 OOD 高度泛化测试；未修改产品源码或覆盖 standard eval。
- MP4 为 H.264 1280×720@50 FPS、399 frames、7.98 s、1,348,208 bytes，SHA256 `29a80335f9fc4b9277a56df1f67cd26670cd553215164e7d04ec34bb06bb2a27`。本地产物为 `artifacts/recovery_history5/model_3000-h035-vx15-{step-0.mp4,metrics.json,telemetry.json}`。
- 400 steps、0 termination/non-finite。后 4 秒 vx mean/RMSE `1.3848/0.1317 m/s`，height mean/RMSE `0.3486/0.0044 m`；后 2 秒分别为 `1.3907/0.1275 m/s` 与 `0.3500/0.0027 m`，yaw RMS `0.1383 rad/s`。视觉行为等待用户验收。

## History-5 Model 3000 Height 0.30 m / Forward 1.5 m/s Evaluation

- 以独立 custom-eval 目录运行 seed-47 单场景 8 秒固定 command：`height=0.30 m`、`vx=1.5 m/s`、yaw 0，其余 command 0；0.30 m 位于训练 `height_range=(0.20, 0.32)` 内。未修改产品源码或覆盖其他 eval。
- MP4 为 H.264 1280×720@50 FPS、399 frames、7.98 s、1,171,954 bytes，SHA256 `1150ff91140d28e7a8bbd92da97fa7f2ad676768ef392192bb6f1d395eed3d62`。本地产物为 `artifacts/recovery_history5/model_3000-h030-vx15-{step-0.mp4,metrics.json,telemetry.json}`。
- 400 steps、0 termination/non-finite。后 4 秒 vx mean/RMSE `1.4699/0.0700 m/s`、height mean/RMSE `0.3049/0.0056 m`；后 2 秒数值基本相同，yaw RMS `0.1358 rad/s`。视觉行为等待用户验收。

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

- Recovery observation 已从 flat 单帧接口拆为当前 8D command + 五帧 proprioception/privileged history，actor/critic 为 138D/168D；Flat 仍为 34D/40D。旧 Recovery checkpoint 不兼容，只能 fresh train。
- Recovery 默认 wheel action-rate weight 为 `-0.02`；无 upright gate。对照档用 Hydra 设置为 `-0.05/-0.1`，不新增 Gym task 或 CLI 参数。
- 仓库只注册 `SerialLeg-Recovery-v0`，使用 `RecoveryPPORunnerCfg`；flat task 仍使用 `PPORunnerCfg`。`SerialLeg-Recovery-Loco-v0`、dense tracking rewards 与专用速度范围已删除。
- Recovery 保持 feed-forward MLP、24-step rollout 和现有 PPO 结构；用户最新指定 `init_std=1.0`，其余 Recovery 参数保持 `entropy_coef=0.00516`、`learning_rate=3e-4`、`desired_kl=0.008`。
- Recovery yaw tracking 已启用参考 flat reward 的大误差梯度语义：`sigma_cmd_scale=0.4`、`ratio_blend=0.2`；保留 Recovery 权重 `1.5` 与直立门控。参考 Recovery-Discovery 在 `93f6ba2` 实际配置为 `0/0`，因此这是用户明确要求的语义迁移，不是逐参数照抄 Discovery。
- 旧 `recovery_motor_tn_fresh_5k` 在 iteration 约 907 停止；其 std 从 1.01 增至约 2.96，并在 iteration 727–733 出现巨额负 reward，不再继续使用。
- Recovery 已完整启用 height-conditioned default：command height 通过参考四连杆 LUT 生成 4D policy 默认腿型；command 重采样同步 per-env cache；非-cache reset、action 零点、`stand_still`/`joint_pos_penalty`/`joint_mirror` reward 与固定命令 eval 共用该 cache。cache reset 仍保留 settled-state 完整关节状态。

## Motor And Action Contract

- Policy 输出仍为 6D：4 个腿位置目标 + 2 个轮速度目标；腿/轮 action scale 为 `0.25 rad / 10 rad/s`。`diff_drive_max_wheel_speed=45 rad/s` 保留为 command feasibility 上限，不是 action clip。
- 腿使用 `DCMotorCfg` 四象限 T-N 包络；轮使用 `TorqueSpeedCurveActuator` 的 M3508+C620 14:1 实测曲线；仿真 actuator 全速域 gate 已通过。
- Recovery reset 保留完整 policy/passive/wheel/tendon-root 写入与 dataset cache 混合，不含 rollout settle。

## Validation

- 新合同本机聚焦 pytest `18 passed`；远端包含 observation history 的聚焦 pytest `23 passed`；相关 Ruff check/format 与 `git diff --check` 通过。
- YAML 变更后旧 USD 的 contract SHA gate 按预期失败；在 RTX 4090 重建后 `convert_serialleg_urdf_to_usd.py --check` 通过，13 links/12 tree joints/2 loops/2 tendons、54 meshes/7102 faces、质量 `12.72874553 kg`。本机/远端 USD SHA256 同为 `6567f649...fa56ec`。
- 新合同 4096-env/1-update gate：actor/critic 138D/168D，98,304 steps、31,027 steps/s、mean reward `-0.88`、mean action std `1.00`、catastrophic `0`，保存 `model_0.pt`；runtime YAML 为 wheel scale `10.0`、`init_std=1.0`、`resume=false`。
- 正式 run initial gate：iteration 84 约 47,985 steps/s、std `1.22`、catastrophic `0`，无 NaN/OOM/Traceback；reward `-758.39` 尚处未收敛早期。

## Next Actions / Risks

1. 用已拉回的 `model_4500.pt` 做同 seed 站立 telemetry、4–5 Hz/pitch-rate/wheel-action/saturation、recovery success 和移动 tracking 评估；不得把它称为完整 5k final checkpoint。
2. 若必须补齐至 iteration 4999，先由用户决定 resume `model_4500.pt` 还是 fresh 重跑；退出原因仍为 `UNKNOWN`，恢复前应保留现有 run/log。
3. 若五帧模型仍抖，再比较更长 frame stack 或 normalized GRU。
4. 若增加 JIT/ONNX 或 sim2sim 导出，严格复用 term-major、oldest→newest 和 reset 首帧填充合同。

## Active Files

- `source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/agents/rsl_rl_ppo_cfg.py`
- `source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg/{robot_config.yaml,usd/serialleg_closed_chain_complex_collision.usd}`
- `source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/{recovery_env_cfg.py,mdp/observations.py}`
- `source/se3_rl_lab/se3_rl_lab/isaac_eval/{schedule,worker}.py`
- `source/se3_rl_lab/se3_rl_lab/tools/runs.py`
- `scripts/{smoke_recovery_reset.py,test_experiment_tools.py,test_recovery_contract.py,test_serialleg_observations.py}`
- `scripts/rsl_rl/play.py`
- `README.md` / `docs/experiment_tooling.md`
- `/tmp/recovery_history5_wscale10_std1_fresh_5k.log`
- `logs/rsl_rl/serialleg_flat_closed_chain/2026-07-13_19-43-59_recovery_history5_wscale10_std1_fresh_5k/`
- `artifacts/recovery_checkpoints/history5_wscale10_std1_fresh_5k/model_4500.pt`
- `/tmp/recovery_wscale10_std1_model4500_local_play.log`
- `artifacts/recovery_eval/wheel-rate-m00{2,5}-model4999-{recovery-eval.mp4,metrics.json}`
- `artifacts/recovery_eval/model_500-history5-{recovery-eval.mp4,metrics.json}`
- `artifacts/recovery_checkpoints/wheel_action_rate_sweep/{README.md,SHA256SUMS,baseline_m0001_height_default,m002,m005,m010_partial}`
- `/home/am345/se3_rl/src/se3_train/tasks/recovery_discovery/rl_cfg.py`
- `/home/am345/se3_rl/assets/base_model/README.md`
- `.agent-handoff/{snapshot,work-log,validation,decisions,backlog,risks}.md`
