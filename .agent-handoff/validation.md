# Validation History

| Date | Command/Check | Result | Notes |
| --- | --- | --- | --- |
| 2026-07-12 | branch/commit/push/PR merge | passed | PR [#9](https://github.com/am345/se3_rl_lab/pull/9) 已由 Draft 转 Ready 并 squash merge；merge commit `46edeee`，远端功能分支删除，本地 `main` 与 `origin/main` 一致。 |
| 2026-07-12 | formal run post-merge health | passed through iteration 705 | std 0.58、mean reward 189.30、catastrophic 0、NaN/Traceback 0；已跨过 iteration 650。 |
| 2026-07-12 | delete Recovery-Loco + recovery/actuator/observation pytest + Ruff | passed | `17 passed`；Gym 注册、两个 loco cfg、`_LOCO_*` 范围和两个 dense tracking 函数均删除；负向契约锁定其不存在。 |
| 2026-07-12 | stop `recovery_motor_tn_fresh_5k` and verify process/GPU | passed | PID 22920 及其进程组已退出；GPU 训练占用释放。 |
| 2026-07-12 | recovery PPO contract pytest + Ruff | passed | 远端 `17 passed`；flat 注册保持 `PPORunnerCfg`，当前唯一 recovery task 使用 `RecoveryPPORunnerCfg`；Recovery-Loco 已由后续删除验证锁定不存在。 |
| 2026-07-12 | `SerialLeg-Recovery-v0`, 4096 env, 1 PPO update, `recovery_ref_std_gate` | passed | iteration 0 mean std 0.50、mean reward -4.09、无 NaN/OOM；运行时 YAML 为 24 steps、0.5/0.00516/3e-4/0.008。 |
| 2026-07-12 | formal `recovery_ref_std_fresh_5k` health before PR | running/passed through iteration 427 | PID 28338；std 0.83（从 iteration 314 的 0.89 回落）、mean reward 87.22、catastrophic 0、无 NaN/Traceback/OOM。 |
| 2026-07-12 | `recovery_motor_tn_fresh_5k` std/log/checkpoint diagnosis | issue confirmed | std 1.01@iter0 → 1.80@100 → 2.20@500 → 2.85@808；model500 六维 `[0.960,2.842,0.890,2.993,2.487,3.006]`；iter727–733 mean reward 出现 `-10^6~-10^9`。 |
| 2026-07-12 | current/reference recovery PPO config and installed RSL-RL source inspection | mismatch confirmed | current `init_std=1.0, entropy=0.01, lr=1e-3, KL=0.01`；reference `0.5, 0.00516, 3e-4, 0.008`。RSL loss 为 `... - entropy_coef * entropy.mean()`，scalar std 无上限 clamp。 |
| 2026-07-12 | fresh motor-model `SerialLeg-Recovery-v0`, 4096 env, 1 PPO update | passed | 98,304 steps、30,674 steps/s、catastrophic 0、无 NaN/OOM；证明正式规模 capacity 与 PPO 链路通过。 |
| 2026-07-12 | formal `recovery_motor_tn_fresh_5k` initial health | running/passed initial gate | seed 42、resume false、5000 iterations；PID 22920，iteration 0–31 健康，首轮约 29.9k steps/s，无 NaN/Traceback/OOM。 |
| 2026-07-12 | YAML/action contract pytest + Ruff/format | passed | `16 passed`；YAML 锁 `0.25/45.0`，action cfg 锁为从 `SERIALLEG_CONTRACT` 读取；相关 Python lint/format 通过。 |
| 2026-07-12 | `convert_serialleg_urdf_to_usd.py` + `--check` | passed | YAML SHA 变化后重建 USD；13/12/2 loops/2 tendons、54 meshes/7102 faces、2 cylinders、0 visuals、`536348 bytes`、质量 `12.72874553 kg`。 |
| 2026-07-12 | IsaacLab runtime action-scale probe | passed | `yaml 0.25 45.0` 与 `runtime 0.25 45.0` 完全一致。 |
| 2026-07-12 | `smoke_recovery_reset.py --num-envs 64 --iteration 2000 --steps 16 --action-std 1.0 --device cuda:0`（YAML/USD rebuild 后） | passed | cache ratio 0.297、passive/tendon error 0、max abs reward 1.624、wheel clearance 0.0010 m，reward/obs finite。 |
| 2026-07-12 | `smoke_serialleg_motor_envelopes.py --samples 801 --headless --device cuda:0` | passed | 实际 runtime `DCMotor`/`TorqueSpeedCurveActuator` 全速域对照共享 `MotorSpec`；leg max error `5.836e-06 N·m`、wheel max error `7.366e-06 N·m`，`velocity_limit_sim=none`。 |
| 2026-07-12 | actuator/recovery/observation pytest after dense-envelope test | passed | `16 passed`；新增轮曲线 2001 点 finite/symmetric/non-increasing 检查。 |
| 2026-07-12 | `.venv/bin/python -m pytest -q scripts/test_serialleg_actuators.py scripts/test_serialleg_observations.py scripts/test_recovery_contract.py`（远端） | passed | `15 passed`；覆盖轮实测曲线/插值/裁剪、腿四象限包络、actuator wiring、policy scale、34D/40D observation 与 recovery 静态合同。 |
| 2026-07-12 | Ruff check/format + `git diff --check`（相关 actuator 文件） | passed | 4 个 Python 文件 lint/format 通过，tracked diff 无 whitespace error。 |
| 2026-07-12 | IsaacLab config/runtime actuator probe（1 env CUDA） | passed | 配置为 `DCMotorCfg`/`TorqueSpeedCurveActuatorCfg`，runtime 为 `DCMotor`/`TorqueSpeedCurveActuator`；无 `velocity_limit_sim`。轮 `[67.43,70.90]` 得 `[2.95,-1.47] N·m`，腿 no-load 四象限裁剪与参考一致。 |
| 2026-07-12 | `smoke_recovery_reset.py --num-envs 64 --iteration 2000 --steps 16 --action-std 1.0 --device cuda:0` | passed | cache ratio 0.250、passive/tendon error 0、max abs reward 1.435、wheel clearance 0.0010 m，reward/obs finite。 |
| 2026-07-12 | 本机 `uv run pytest ...` | not run | 本机缺少 editable sibling `D:\RoboMaster\IsaacLab`，uv metadata 解析在测试前失败；改在已锁定远端环境验证。 |
| 2026-07-12 | recovery-loco static contract/Ruff（历史，后续已删除） | passed at the time | `6 passed`；该 task/reward/注册随后按用户要求删除，以本文件顶部的删除验证为当前状态。 |
| 2026-07-12 | 4096-env resume gate from recovery `model_1999.pt` | passed | 27 reward terms、单 velocity stage、1 PPO update；无 NaN，catastrophic 0。 |

| Date | Command/Check | Result | Notes |
| --- | --- | --- | --- |
| 2026-07-12 | `se3rl eval ... --checkpoint 1999 --task SerialLeg-Recovery-v0 --scenario-duration 4.0 --no-rerun` | passed | 1200 finite samples；MP4 23.98s、H.264、1280×720、50 FPS、4,516,102 bytes。 |
| 2026-07-12 | MP4 frame extraction/visual inspection | passed | 2 秒抽帧可见机器人 collision preview、地面和速度箭头。 |

| Date | Command/Check | Result | Notes |
| --- | --- | --- | --- |
| 2026-07-12 | `recovery_nan_probe_v2` | reproduced | iteration 210 / step 5066 / env 2821；articulation 全 NaN，raw action max 627.8，contact finite。 |
| 2026-07-12 | `recovery_catastrophic_ab`, 4096 env × 400 iterations | passed | 同 seed 无 NaN；termination 峰值约 1.4% 后归零；最终 reward 92.29、episode length 1000、action std 1.98。 |
| 2026-07-12 | cleanup/static gates | passed | contract `5 passed`、Ruff、`git diff --check`；源码无 `[DEBUG-recovery-nan-v2]`。 |

| Date | Command/Check | Result | Notes |
| --- | --- | --- | --- |
| 2026-07-12 | 旧 `/tmp/recovery_full_2k.log` 定位 | failed as expected | iteration 835 后 RSL-RL 检出 reward NaN；dataset 1500 阶段尚未启用。 |
| 2026-07-12 | stage-650 random-action soak | passed | 1024 env、1200 steps、action std 1.0/9.1 均 finite；std 9.1 最大绝对 reward 135.874。 |
| 2026-07-12 | recovery contract + Ruff | passed | 远端 `5 passed`；相关两个文件 `All checks passed!`。 |
| 2026-07-12 | 4096 env stage-650 reset gate | passed | 16 steps finite，passive error 0，tendon pos/vel 0，最小 wheel clearance 0.0010 m。 |
| 2026-07-12 | 本地 uv pytest/Ruff | not run | 本机缺少 sibling `../IsaacLab/source/isaaclab`；使用已同步远端环境验证。 |

| Date | Command/Check | Result | Notes |
| --- | --- | --- | --- |
| 2026-07-11 | `smoke_recovery_reset.py --num-envs 4096 --iteration 2000` | passed | cache ratio 0.253、passive error 0、tendon-root pos/vel 0，16步max abs reward 94.921，所有reward/observation有限。 |
| 2026-07-11 | 4096-env `recovery_full_reset_soak`, 100 iterations | passed | 9830400 steps、training time 179.74s；跨过旧NaN窗口，无NaN/异常退出。 |
| 2026-07-11 | fresh `recovery_full_2k`, 4096 env/2000 iterations | running | `/tmp/recovery_full_2k.log`；第4轮约58k steps/s、显存4.9 GiB，无NaN，ETA约1小时。 |
| 2026-07-11 | recovery cache/schema/fourbar/reset static tests; Ruff; `git diff --check` | passed | `5 passed`；40k cache为20k train/20k eval，10-joint顺序含4 passive；默认policy pose派生passive pose误差 `<2e-5 rad`；settle覆盖已从源码移除。 |
| 2026-07-11 | remote sync/read-only status after complete reset migration | blocked | SSH连接建立后在 `kex_exchange_identification` 被远端关闭；未停止/重启训练，远端同步结果和训练状态均为 `UNKNOWN`。 |
| 2026-07-11 | remote SHA verification + `pytest scripts/test_recovery_contract.py -q` | passed | actions/fourbar/reset/config/40k NPZ本地与远端SHA逐一一致；远端`5 passed in 3.60s`，无训练进程，未启动Isaac环境。 |
| 2026-07-11 | clean 4096-env `recovery_settle_clean_soak`, 100 iterations | passed | 9830400 steps、training time 144.87s；跨过原 52/58 轮故障点，无诊断代码、无 NaN，最终 mean reward 147.12。 |
| 2026-07-11 | instrumented 4096-env recovery NaN reproduction | reproduced/fixed | 定位到 reset 后 PhysX state 爆炸；包络 clearance 单独仍复现，加入 40 physics-step action settle 后 100 iterations 通过，临时 debug 前缀已清理。 |
| 2026-07-11 | fresh `recovery_2k_settle`, 4096 env/2000 iterations | running | run `2026-07-11_17-42-49_recovery_2k_settle`；第 18 轮约 66k steps/s、显存 4.9 GiB、无 NaN。 |
| 2026-07-11 | background `se3rl train --task SerialLeg-Recovery-v0 --envs 4096 --iterations 2000 --run-name recovery_2k --device cuda:0` | failed | 第 58 轮后 `ValueError: rewards ... contain NaN values`；进程退出、GPU 释放，只保存 `model_0.pt`。第 58 轮 mean reward 144.30、episode length 1000；需定位具体 reward/state 后重训。 |
| 2026-07-11 | remote `train.py --task SerialLeg-Recovery-v0 --num_envs 1 --device cuda:0 --max_iterations 1` | passed | 完成 24 steps/1 PPO update；Reward Manager 25 terms、Termination Manager timeout-only、action 6D、actor/critic 34D/40D 全部执行，无异常退出。 |
| 2026-07-11 | `pytest scripts/test_recovery_contract.py -q`; Ruff check/format; `git diff --check` | passed | recovery reward 名称/权重、只覆盖 reward/termination/reset、Gym 注册静态合同 `3 passed`；新增 Python 文件格式与 lint 通过。 |
| 2026-07-11 | recovery task legacy `smoke_serialleg_task.py` | expected mismatch | 环境已完整创建；旧 smoke 随后因硬编码只接受 flat 官方 reward 列表而退出，改用真实 1-update PPO gate 完成运行时验证。 |
| 2026-07-11 | yaw-relative follow camera; remote Ruff; 1.0s short eval; ffmpeg 1.10s/1.90s frame comparison; full 4.0s eval | passed | 相机逐步跟随 root 平移和 yaw，保持侧后方 `2.4m`/上方 `0.57m`；短测首尾机器人保持居中，完整 eval 退出 0并生成 MP4/RRD。 |
| 2026-07-11 | enlarged debug arrows; remote Ruff; 0.5s short eval; full 4.0s eval; ffmpeg frame inspection | passed | scale `(1.0,0.18,0.18)`、velocity multiplier `3.0`、height `0.35m`；完整 eval 退出 0，抽帧确认绿/蓝箭头尺寸明显且机器人仍正常移动。 |
| 2026-07-11 | preview world-space sync fix; remote Ruff; 0.5s eval; ffmpeg 0.55s/0.95s frame comparison; full 4.0s eval | passed | telemetry/world-position 先证明物理机器人移动；短测抽帧进一步确认可视 collision 外壳随机器人平移和变姿。完整录制退出 0，复制到本地的 MP4/RRD 分别为 977902/340527 bytes。 |
| 2026-07-11 | full debug-vis `se3rl eval model_499 --scenario-duration 4.0`; ffmpeg frame inspection | passed | `VelocityHeightCommand` 新增目标/实际平面速度 marker；eval-only 固定 reset yaw、侧视相机并关闭 Fabric。最终 23.98s/1199-frame/1280×720 MP4 抽帧确认绿色目标与蓝色实际箭头可见；RRD 330807 bytes。 |
| 2026-07-11 | full `se3rl eval model_499 --scenario-duration 4.0`; `ffprobe`; copy artifacts to local exchange | passed | 完整 six-scenario rollout 生成 1199-frame、1280×720、23.98s MP4（1.10MB）和 334KB Rerun；metrics/report 同步生成，并复制到 `D:\RoboMaster\se3_checkpoint_exchange\model_499_flat_basic_24s`。 |
| 2026-07-11 | remote Ruff format/check; `pytest -q scripts/test_experiment_tools.py`; `uv lock --check`; `se3rl --help/runs/compare`; `git diff --check` | passed | 9 个工具相关 Python targets formatted/lint 通过，纯工具 `3 passed`（run/status、报告排序、Rerun `.rrd`）；uv 解析 253 packages，CLI 七类入口和 compare 产物通过。 |
| 2026-07-11 | `se3rl train --envs 64 --iterations 1 --run-name cli_smoke --device cuda:0` | passed | 完成 1 PPO update/1536 steps并生成 `model_0.pt`、`manifest.json`、`status.json`；退出 0，证明一键训练编排和元数据闭环。 |
| 2026-07-11 | `se3rl eval ...model_499 --scenario-duration 0.5`; ffmpeg frame extraction + visual inspection | passed | 150 steps/六 scenarios；生成 171KB MP4、metrics/telemetry、59KB `.rrd`、Markdown、latest result/status best。preview 54 meshes/2 cylinders，non-finite=0，max loop residual `3.813e-4 m`、virtual-root drift `6.297e-4 rad`；1280x720 抽帧确认 collision robot 可见。 |
| 2026-07-11 | remote Ruff check/format for `scripts/rsl_rl/play.py`; GUI play with `--show_colliders --checkpoint .../model_499.pt` | passed | `play.py` 新增显式 collider overlay 开关；远端日志确认 environment setup、`SETTING_DISPLAY_COLLIDERS=2` 和 `model_499.pt` 加载，`wmctrl` 确认 Isaac Sim 5.1.0 窗口，常驻 PID `6622`。 |
| 2026-07-11 | remote `train.py --task SerialLeg-Flat-ClosedChain-v0 --num_envs 4096 --device cuda:0 --headless --max_iterations 500 --run_name cuda4096_500iter_flat` | passed | 完成 49,152,000 simulation steps/500 PPO updates，训练时间 `470.93s`，最终吞吐约 `110,765 steps/s`；mean reward `26.30`、episode length `985.91/1000`，termination 为 time-out `0.9981`、bad orientation `0.0016`、base contact `0.0005`，生成 `model_499.pt`。最终 velocity curriculum stage 为 1、push stage 为 0；说明当前课程范围内已学到稳定平地跟踪，但尚未覆盖更高速度阶段或 push robustness。 |
| 2026-07-11 | remote `train.py --task SerialLeg-Flat-ClosedChain-v0 --num_envs 4096 --device cuda:0 --headless --max_iterations 1 --run_name cuda4096_startup_gate` | passed | GPU 空闲、默认 PhysX capacity 下创建 4096 environments，采样 98,304 steps 并完成 1 PPO update，退出 0；collection `2.492s`、learning `0.249s`、约 `35,871 steps/s`，生成 `model_0.pt`。未观测到 OOM/Traceback；这是启动/短训练 gate，不代表长 rollout 稳定性或峰值显存已定标。 |
| 2026-07-11 | remote Ruff check/format, `git diff --check`; `train.py --task SerialLeg-Flat-ClosedChain-v0 --num_envs 4 --device cpu --headless --max_iterations 1 --run_name mlp_24step_smoke` | passed | `num_steps_per_env=24` 与 curriculum `steps_per_policy_iteration=24` 同步；实际采样 96 steps、完成 1 PPO update并退出 0，actor/critic 保持 34D/40D。最初本机 `python -m py_compile` 因 Windows 无 `python` 命令退出 9009，改由项目指定远端 `.venv` 完成真实运行时验证。 |
| 2026-07-11 | local/remote `git hash-object` for MLP config, README and 7 handoff docs; local/remote `git status --short` | passed | 9 个目标文件哈希逐项一致，远端改动集合与本地一致。首次把远端 bash loop 嵌入 PowerShell 的组合命令因引号错误退出 1，改为直接列路径后通过；未修改文件或影响 runtime。 |
| 2026-07-11 | local `py_compile`; remote Ruff format/check; `git diff --check` for MLP config/docs | passed | `rsl_rl_ppo_cfg.py` 语法、固定环境格式/lint 与 workspace whitespace 均通过。 |
| 2026-07-11 | `train.py --task SerialLeg-Flat-ClosedChain-v0 --num_envs 4 --device cpu --headless --max_iterations 1 --run_name mlp_smoke` | passed | 实际解析 actor `34→512→256→128→6` + Identity、critic `40→512→256→128→1` + EmpiricalNormalization；采样 256 steps，完成 1 PPO update，mean value loss `0.0147`、surrogate loss `-0.0033`，生成 `model_0.pt`。 |
| 2026-07-11 | same train command with `--resume --load_run 2026-07-11_10-59-15_mlp_smoke --checkpoint model_0.pt` | passed | 明确日志 `Loading model checkpoint from .../model_0.pt`，随后再次采样 256 steps 并完成 1 PPO update；save/load round-trip 通过。 |
| 2026-07-11 | remote Ruff check/format, `pytest -q scripts/test_serialleg_observations.py`, `git diff --check` | passed | 9 个相关 Python 文件 Ruff 通过且已格式化；observation contract `4 passed`，缺失 `velocity_height` 现硬失败；本地/远端任务 diff 均无 whitespace error。 |
| 2026-07-11 | `smoke_serialleg_task.py --device cpu --num-envs 1/4 --zero-steps 8 --controlled-steps 8` | passed | 两种 env count 均通过 strict 8D/jump-zero/差速预算、官方 reward/termination identity、课程终态、固定状态 tracking reward=1、actor/critic `(34)/(40)` 与短 rollout；1-env loop `3.857e-4/2.114e-4 m`，4-env `4.624e-4/2.397e-4 m`，passive effort 0。 |
| 2026-07-11 | `smoke_serialleg_task.py --device cuda:0 --compact-gpu-buffers --num-envs 1/4 --zero-steps 4 --controlled-steps 4` | passed | compact-CUDA 1-env loop `4.181e-4/2.361e-4 m`，4-env `4.056e-4/2.548e-4 m`；manager/fixed-state gates、有限状态、接触与 passive effort 0 均通过。 |
| 2026-07-11 | CPU 1-env legacy default 64+64 zero/controlled smoke after official terminations | expected termination | zero-action 长阶段触发 `bad_orientation` 或 `base_contact` termination；这证明旧默认不再适合作 wiring gate。脚本默认改为 8+8；长 rollout 必须用训练策略控制并单独验收。 |
| 2026-07-11 | handoff UTF-8 readback, `git diff --check`, machine/SSH/GUI key-term audit, credential-pattern scan | passed | 8 个 handoff 文件按现有 multi-document layout 更新；中文回读正常、无 whitespace error，diff 未发现密码、private key、token 或 TURN credential。仅文档变化，未运行代码测试。 |
| 2026-07-11 | `hostname`; `ssh -G se3_rl_lab_gpufree`; local/remote repo SHA/status probe | passed | 本机为 `WIN-46S653M0DI0`；SSH alias 含 `LocalForward 3000`、`RemoteForward 7890`、key auth/keepalive；本地与远端项目均为 clean `main@01e1c1a`，远端 IsaacLab clean `b4c3210`。未把 endpoint、密码或私钥内容写入 handoff。 |
| 2026-07-11 | remote package metadata + PyTorch CUDA matrix + `nvidia-smi` | passed | Isaac Sim `5.1.0.0`、IsaacLab `0.54.4`、torch `2.7.0+cu128`、torchvision `0.22.0+cu128`、RSL-RL `5.0.1`；RTX 4090 24GB/driver `580.126.09`，`cuda_available=True`，CUDA 矩阵计算通过。 |
| 2026-07-11 | `scripts/smoke_serialleg_task.py --headless --device cuda:0 --compact-gpu-buffers` | passed | Isaac Sim 5.1 headless 启动、`SerialLeg-Flat-ClosedChain-v0` create/reset/zero+controlled rollout 均成功；environment device 为 `cuda:0`。 |
| 2026-07-11 | Selkies/Xorg/SSH GUI path: remote `:3000`, `DISPLAY=:20`, OpenGL renderer, local HTTP tunnel, Isaac GUI window | passed | 远端桌面 2560×1440，direct rendering/NVIDIA RTX 4090；本机 `http://127.0.0.1:3000` 返回 200；`wmctrl` 识别 `Isaac Sim 5.1.0` 窗口。 |
| 2026-07-10 | handoff unignore + publish preflight: `git check-ignore`, `git diff --check`, `uv lock --check`, observation pytest, credential scan | passed | 三个 handoff targets 均不再 ignored；`scripts/test_serialleg_observations.py` 为 `4 passed`；whitespace、lock 与敏感信息检查通过。 |
| 2026-07-10 | fixed Git subdirectory sources: `uv lock`, `uv sync --locked`, then AppLauncher import | failed/design rejected | 五个 Git SHA package 可构建安装，但 `isaaclab.app` 导入报 `FileNotFoundError: .venv/lib/python3.11/site-packages/config/extension.toml`；普通 wheel 破坏 IsaacLab extension 的 sibling config layout，已改回 source checkout 方案。 |
| 2026-07-10 | sibling relative IsaacLab sources: `uv lock`, `uv sync --locked`, `uv lock --check`, `git diff --check` | passed | `pyproject.toml` / `uv.lock` 只记录 `../IsaacLab/source/...`，真实环境从失败的 Git wheels 恢复为五个 editable source packages；运行配置 `pyproject.toml`、`uv.lock` 与 README 不再写死 `/home/am345`。 |
| 2026-07-10 | handoff pre-publication sensitive-data scan | passed | 对 `AGENT_HANDOFF.md`、`AGENT_SESSION_PROMPTS.md`、`.agent-handoff/` 扫描 GitHub/OpenAI token、private key、API key 与 access token 模式，未发现凭据；历史本机路径和 `/tmp` 验证路径保留为事实证据。 |
| 2026-07-10 | `OMNI_KIT_ACCEPT_EULA=YES uv run python -u scripts/list_envs.py --keyword SerialLeg` | passed | AppLauncher 正常启动并列出 `SerialLeg-Flat-ClosedChain-v0`；仍有既存 inotify `errno=28` 日志噪声。 |
| 2026-07-10 | 文档范围更新回读、`rg` 关键措辞审计、`git diff --check` | passed | README 与 handoff 已一致记录：基础阶段只用官方 locomotion rewards，自定义奖励推迟到 finetune，jump command 默认关闭且不迁移跳跃逻辑。仅文档变化，按用户要求未修改代码、未运行 runtime 测试。 |
| 2026-07-10 | ready + squash merge PR #4; post-merge sync | passed | merge 前 head `554af978...`、`MERGEABLE/CLEAN`、无 checks；PR #4 squash merge 为 `c9233d5`，远端分支已删除，本地/远端 `main` 一致且 tracked status clean。GitHub App 403 后使用 `gh` fallback。 |
| 2026-07-10 | commit/push + draft PR #4 verification | passed | commit `554af97` 已推送到 `origin/agent/migrate-delayed-action-observations`；draft PR #4 为 `OPEN/MERGEABLE`，base=`main`、head SHA `554af978...`，本地/远端一致且 tracked status clean。GitHub App 403 后使用已认证 `gh` fallback。 |
| 2026-07-10 | `uv run pytest -q scripts/test_serialleg_observations.py` | passed | `4 passed`；覆盖 34D/40D 布局与数值、policy joint 隔离、无 command 的零 fallback、已有 command 非 8D 硬失败。 |
| 2026-07-10 | Ruff format/check + `git diff --check` for delayed-action/observations migration | passed | 新 action/observation、env cfg、smoke 和聚焦测试均通过格式、lint 与 whitespace 检查。 |
| 2026-07-10 | `smoke_serialleg_task.py --device cpu --num-envs 1 --zero-steps 8 --controlled-steps 8` | passed | actor/critic `(34)/(40)`；action FIFO/tendon/clamp/reset probe 通过；zero/controlled loop `3.529e-04/2.154e-04 m`，contact `76.574/62.200 N`，passive effort `0`。 |
| 2026-07-10 | `smoke_serialleg_task.py --device cuda:0 --compact-gpu-buffers --num-envs 1 --zero-steps 2 --controlled-steps 2` | passed | 并行 Kyber 占用约 `5302 MiB` 时 compact gate 仍通过；actor/critic `(34)/(40)`；loop `3.487e-04/2.059e-04 m`，contact `74.981/63.867 N`，passive effort `0`。 |
| 2026-07-10 | commit/push + PR #3 merge + post-merge sync | passed | branch commit `0409fe3`；PR #3 merge 前 `MERGEABLE/CLEAN`、无 checks；squash merge commit `f4e1121`；本地/远端 `main` SHA 相同，tracked status clean，远端 head branch 已删除。 |
| 2026-07-10 | `view_serialleg_collisions.py --headless --device cpu --frames 240 --demo-motion --view-mode render` after coupled-limit UI | passed | 13/12、54 mesh + 2 Cylinder；max loop residual `1.300e-04 m < 2e-04 m`；active/passive motion `0.205/0.204 rad`。 |
| 2026-07-10 | `view_serialleg_collisions.py --device cpu --frames 5 --view-mode render` GUI path | passed | 非 headless UI 成功创建 absolute rod sliders、coupled-limit labels 和 callbacks；报告 `rod_target_span=6.283185 rad`、左右 range `[0,1.509535] rad`，退出 0。 |
| 2026-07-10 | Ruff format/check、`py_compile`、`git diff --check` for viewer update | passed | 格式、lint、语法和 whitespace 通过。 |
| 2026-07-10 | fixed-tendon USD rebuild + `convert_serialleg_urdf_to_usd.py --check` | passed | `536323 bytes`；13 rigid bodies、12 tree joints、2 external loops、2 fixed tendons、54 collision meshes/7102 faces、2 cylinders、0 visuals、mass `12.72874553 kg`。 |
| 2026-07-10 | `smoke_serialleg_usd.py --headless --device cpu --steps 64` | passed | 13 bodies/12 DOFs/2 fixed tendons；standing coordinates 约 `1.316677 rad`，root drift `8.453e-07 rad`，loop residual `3.111e-07 m`。 |
| 2026-07-10 | `smoke_serialleg_task.py --headless --device cpu` | passed | `gym.make/reset/rollout=true`；13/12；6 policy + 4 passive source joints，roots unactuated；zero/controlled loop peaks `6.037e-04/8.132e-05 m`。 |
| 2026-07-10 | `smoke_serialleg_closed_chain.py --headless --device cpu` | passed | 240 步、5 N；left/right closed peaks `3.845e-06/1.018e-05 m`，open `7.290e-03/4.196e-03 m`，ratio `1895.9x/412.2x`。 |
| 2026-07-10 | Ruff format/check、`py_compile`、`git diff --check` for changed Python files | passed | 格式、lint、语法和 whitespace 均通过。 |
| 2026-07-10 | URDF-only virtual-root build: Ruff, `py_compile`, generator, `--check`, `git diff --check` | passed | candidate 为 13 links/12 tree joints（10 source + 2 virtual）/2 spherical loops/54 collision meshes；source fixed-tendon axes/range/solref/solimp、virtual `±1e-4 rad` limits、rooted topology、质量/COM/inertia、FK/geometry 均通过；总质量 `12.72874558 kg`，zero/standing residual `0/2.197e-07 m`。USD/PhysX intentionally not run，等待用户检查。 |
| 2026-07-10 | ready + squash merge PR #2; post-merge sync | passed | 合并前 `MERGEABLE/CLEAN`、无 pending/failing checks、head 固定为 `b53d5e9`；PR #2 已 MERGED 为 `0e0f401`，远端发布分支已删除，本地/远端 `main` 一致且 status clean。 |
| 2026-07-10 | commit/push + draft PR verification | passed | 分支 `agent/migrate-serialleg-runtime` 已推送；本地/远端 HEAD 均为 `b53d5e9`；draft PR #2 OPEN，base=`main`、head 正确。GitHub App 创建因 integration 403 失败后，使用已认证 `gh` fallback 成功。 |
| 2026-07-10 | `smoke_serialleg_task.py --device cpu` final `dt=0.005/decimation=4`, solver `16/4` | passed | `gym_make/reset/rollout=true`；11 bodies/10 DOFs；6 policy/4 passive exact；zero/controlled residual `3.956e-4/5.298e-5 m < 1e-3`；contact `117.324/64.981 N`；passive effort `0`。 |
| 2026-07-10 | `smoke_serialleg_task.py --device cuda:0 --compact-gpu-buffers` final | passed | CUDA rollout 完整通过；zero/controlled residual `4.756e-4/5.399e-5 m`；contact `118.362/73.374 N`；passive effort `0`。 |
| 2026-07-10 | `smoke_serialleg_task.py --device cuda:0` with default PhysX capacities | failed/environment pressure | GPU 同时有 Kyber 4096-env 训练 PID `328771` 占用 `5300 MiB`；PhysX tensors 为 `mGpuContactPairsDev` 请求 `671088640 bytes` 后 OOM，随后 `Failed to get DOF velocities`。 |
| 2026-07-10 | task gate intermediate solver/dt sweep | mixed/expected | `8/2 @ .005/4` residual `1.099e-3`；`16/4 @ .005/4` `3.956e-4`；`32/8 @ .005/4` CPU `1.549e-4`、CUDA `2.462e-4`；`48/12 @ .005/4` CPU/CUDA `9.280e-5/1.867e-4`；`8/4 @ .0025/8` CPU/CUDA `2.791e-4/2.939e-4`。最终按用户 dt/decimation 要求选 `16/4 @ .005/4`。 |
| 2026-07-10 | task smoke Ruff/compileall/lock/diff checks | passed | 新 smoke、asset contact/solver 和 env reset/sensor 配置格式、lint、语法、lock 及 whitespace 通过。 |
| 2026-07-10 | YAML contract loader probe | passed | `robot_config.yaml` 派生 robot name、11 links、10 tree joints、2 loops、6D policy order、4 passive joints、原 standing pose 及三个 actuator groups；root quaternion 转为 IsaacLab WXYZ identity。 |
| 2026-07-10 | pre-rebuild `convert_serialleg_urdf_to_usd.py --check` | expected failure | 旧 USD metadata 仍指向 TOML，被 `USD contract path metadata does not match` stale-artifact gate 拒绝。 |
| 2026-07-10 | USD rebuild + `convert_serialleg_urdf_to_usd.py --check` | passed | 重建 USD `534403 bytes`；default prim/root、11 links、10 tree joints、2 external loops、54 meshes/7102 faces、2 cylinders、0 visuals、mass `12.72874580 kg`；metadata 锁 YAML path/SHA。 |
| 2026-07-10 | `convert_serialleg_mjcf_to_urdf.py --check` | passed | canonical URDF 仍为 11/10/2、0 visuals、54 collision meshes、mass `12.72874558 kg`，standing loop residual `2.197e-07 m`。 |
| 2026-07-10 | CPU `smoke_serialleg_usd.py` 64 steps | passed | 11 bodies/10 DOFs，max loop residual `3.388e-07 m < 1e-05 m`。首次日志 `rg` 模式写错造成 pipeline status 1；保留末尾日志重跑确认脚本实际退出 0。 |
| 2026-07-10 | CPU `smoke_serialleg_closed_chain.py` 240 steps | passed | closed peaks `9.444e-07/2.175e-06 m`，open `0.2584/0.08859 m`，ratios `273651.5x/40731.7x`，joint motion `0.8063 rad`。 |
| 2026-07-10 | Isaac Sim headless asset config import | passed | `spawn=UsdFileCfg`；policy/passive 顺序正确；init pos `(0,0,0.22)` / rot `(1,0,0,0)` 由 YAML 生成。 |
| 2026-07-10 | Ruff format/check; compileall; `uv lock --check`; old TOML reference audit; `git diff --check` | passed | 6 个 Python 消费者/loader 通过，lock 已显式记录 PyYAML，业务文件旧 `serialleg_contract.toml` 引用为 0。 |
| 2026-07-10 | direct wheel build and archive listing | passed | wheel 包含 `robot_config.yaml` 和 `534403-byte` USD，不包含旧 TOML；临时 wheel、build 和 egg-info 已清理。 |
| 2026-07-10 | USD `test -f`; `compileall`; legacy-spawner `rg`; Ruff format/check; `git diff --check` | passed | USD 存在，asset config 语法、格式、lint 和 whitespace 通过，`serialleg.py` 中无 `MjcfFileCfg` / `spawn_from_mjcf` / runtime loop-joint helper 残留。 |
| 2026-07-10 | `OMNI_KIT_ACCEPT_EULA=YES uv run python -c 'AppLauncher... import SERIALLEG_CLOSED_CHAIN_CFG ...'` | passed | Isaac Sim headless 启动后输出 `spawn=UsdFileCfg`，USD 路径正确且 `exists=True`，actuator groups 为 `legs/wheels/closed_chain_passive`。仍有既存 inotify `errno=28` 日志噪声。 |
| 2026-07-10 | task-level `gym.make/reset/step` / PhysX rollout | not run | 用户本轮只要求完成计划第 1 步；完整 task CPU/CUDA gate 保留为下一项。 |
| 2026-07-10 | merge PR #1 | passed | PR 状态 MERGED，squash commit `42b0973`；本地/远端 `main` 一致、status clean、远端发布分支已删除。 |
| 2026-07-10 | publish SerialLeg rename branch + draft PR | passed | `03c3ab6` 已推送到 `origin/agent/unify-serialleg-asset-names`；本地/远端分支 SHA 一致；draft PR #1 OPEN，base=`main`，head=`agent/unify-serialleg-asset-names`。 |
| 2026-07-10 | SerialLeg asset basename rename reference audit | passed | 工作区资产为 2 MJCF/1 URDF/1 USD 新路径；旧 `...v3_train_obb_trim.{xml,urdf,usd}` 文件路径引用为 0；新 USD Git ignore exception 与 LFS attrs 均正确。 |
| 2026-07-10 | rebuild/check and runtime gates after complete asset/internal rename | passed | 业务源码旧名称为 0；URDF SHA `280d74c4...dd3e`；USD default prim `/serialleg_closed_chain_complex_collision`、`534455 bytes`/54 meshes/2 cylinders/0 visual；CPU free residual `3.388e-07 m`，closed-chain A/B 与 viewer `both` motion/residual 均保持原结果。 |
| 2026-07-10 | Ruff/py_compile/`git diff --check` after rename | passed | 4 个相关 Python 文件格式、lint、语法和 workspace whitespace 通过；验证缓存/log 已清理。 |
| 2026-07-10 | exact `git push --force-with-lease` to GitHub main | passed | 预检远端 `87e145a` 后强制更新为 `72a2cd8`；未覆盖并发提交，随后恢复 upstream。 |
| 2026-07-10 | fresh GitHub single-branch clone after rewrite | passed | remote/local/clone HEAD 均为 `72a2cd8`；clone `.git=516778 bytes`、worktree `1595755 bytes`、total `2112533 bytes`、pack `461.36 KiB`。 |
| 2026-07-10 | local root-history rewrite + aggressive GC | passed | 新 HEAD `72a2cd8`，1 commit、0 parents、status clean、local refs=1；最终 `.git=1110734 bytes`，pack objects `461.35 KiB`，unreachable=0。rewrite 前 `.git=70987926 bytes`。 |
| 2026-07-10 | recovery bundle create/verify | passed | `/tmp/se3_rl_lab_pre_rewrite_87e145a.bundle` 为完整 bundle，`61899823 bytes`。 |
| 2026-07-10 | post-rewrite size/remote probe | passed | committed snapshot `1595755 bytes`；workspace excluding `.git/.venv` `1692600 bytes`；full directory `19358001643 bytes`；远端 main 仍为 `87e145a`，未 force-push。 |
| 2026-07-10 | post-cleanup exact mesh closure + MJCF→URDF `--check` | passed | canonical/import MJCF/URDF/磁盘集合完全相等：54 files、`359636 bytes`、missing=0、extra=0；11 links/10 tree joints/2 loops、0 visual、56 collisions、standing residual `2.197e-07 m`。 |
| 2026-07-10 | collision-only USD rebuild + `--check` | passed | `534446 bytes`；11 links、10 tree joints、2 external loops、54 meshes/7102 faces、2 cylinders、0 visual geometry、total mass `12.72874580 kg`。 |
| 2026-07-10 | post-mesh-cleanup CPU/CUDA runtime regressions | passed | CPU free residual `3.388e-07 m`；CPU/CUDA ground residual `9.380e-05/1.175e-04 m`，wheel/contact peaks 与清理前一致；CPU/CUDA closed-chain A/B peaks/ratios 与清理前一致。 |
| 2026-07-10 | post-mesh-cleanup viewer demo 240 frames | passed | 54 mesh + 2 cylinder previews；residual `1.122e-04 m`，leg/wheel/passive motion `1.768/2.734/1.841 rad`。 |
| 2026-07-10 | direct wheel build after mesh cleanup | passed | wheel `309906 bytes`，精确包含 54 STL/`359636 bytes`、2 MJCF、URDF `21631 bytes`、USD `534446 bytes`、contract；构建产物随后清理。 |
| 2026-07-10 | Ruff format/check, py_compile, `git diff --check`, deleted-reference search | passed | 3 个修改 Python 文件格式/lint/语法通过；源码与 README 无已删除 visual/旧模型路径残留；最终临时 build/cache/log 已清理。 |
| 2026-07-10 | XML/URDF resolved mesh-reference closure audit | passed | 5 个 MJCF 与 canonical URDF 的所有 mesh 引用均存在；mesh 树 307 文件/`241378057 bytes`，all-doc closure 94/`235315996 bytes`，全局无引用 213/`6062061 bytes`；canonical collision/visual 分别为 54/`359636 bytes` 和 23/`117449982 bytes`。未删除 mesh。 |
| 2026-07-10 | safe intermediate artifact cleanup verification | passed | 清理前目标合计约 `299 MB`；删除后 `source/se3_rl_lab/build`、`dist`、`.ruff_cache` 均不存在，仓库内（排除 `.venv`）`__pycache__=0`，`/tmp/serialleg*=0`；`git status` 仍只包含原有 7 个修改文件和 9 个新增交付文件。 |
| 2026-07-10 | `... view_serialleg_collisions.py --headless --device cpu --frames 240 --view-mode render --demo-motion` | passed | 54 mesh + 2 cylinder moving-body previews；fixed base；max loop residual `1.122e-04 m < 2e-04 m`；max leg/wheel/passive motion `1.768/2.734/1.841 rad`。 |
| 2026-07-10 | `... view_serialleg_collisions.py --headless --device cpu --frames 30 --view-mode both --demo-motion` | passed | 实体 preview + PhysX overlay + active/passive motion 同时初始化；max residual `1.122e-04 m`。 |
| 2026-07-10 | interactive `view_serialleg_collisions.py --device cpu --view-mode render` after joint UI | passed | Isaac Sim 5.1 GUI 成功创建 `SerialLeg Collision + Closed Chain` 面板和 6 个控件，报告 54 mesh/2 cylinders/11 bodies/10 DOFs；实际交互后正常退出，`max_loop_residual=1.069e-04 m < 2e-04 m`，leg/wheel/passive motion `1.592/0.6732/1.401 rad`。 |
| 2026-07-10 | Ruff format/check, `py_compile`, `git diff --check` for interactive viewer | passed | contract-driven joint UI、moving preview 和 headless demo gate 的格式、lint、语法和 whitespace 通过。 |
| 2026-07-10 | `... smoke_serialleg_closed_chain.py --headless --device cpu` | passed | 240 步/5 N A/B；closed joint motion `8.063e-01 rad`；left/right closed peaks `9.444e-07/2.175e-06 m`，open `2.584e-01/8.859e-02 m`，ratios `273651.5x/40731.7x`。 |
| 2026-07-10 | `... smoke_serialleg_closed_chain.py --headless --device cuda:0` | passed | 240 步/5 N A/B；closed joint motion `8.064e-01 rad`；left/right closed peaks `2.104e-06/5.765e-06 m`，open `2.584e-01/8.859e-02 m`，ratios `122810.0x/15366.8x`。 |
| 2026-07-10 | Ruff format/check, `py_compile`, `git diff --check` for closed-chain smoke/README | passed | 新 A/B smoke 的格式、lint、语法和 workspace whitespace 通过。 |
| 2026-07-10 | `... smoke_serialleg_usd.py --headless --device cpu --ground-contact` | passed | 400 步；11 bodies/10 DOFs；custom Cylinder mode；wheel peaks `128.573/125.795 N`，mesh-backed `base_link=2976.983 N`；max residual `9.380e-05 m < 2e-04 m`。 |
| 2026-07-10 | `... smoke_serialleg_usd.py --headless --device cuda:0 --ground-contact` | passed | 400 步；contact tensor device `cuda:0`；wheel peaks `129.882/125.926 N`，`base_link=2960.022 N`；max residual `1.175e-04 m < 2e-04 m`；未出现 OOM。 |
| 2026-07-10 | `... smoke_serialleg_usd.py --headless --device cpu` free-space regression | passed | 默认 64 步；max residual `3.388e-07 m < 1e-05 m`，新增 contact mode 未改变原 gate。 |
| 2026-07-10 | Ruff format/check, `py_compile`, `git diff --check` for ground-contact smoke/README | passed | 最新 smoke 实现的格式、lint、语法和 workspace whitespace 通过。 |
| 2026-07-10 | Isaac Sim 5.1 carb setting probe for `SETTING_COLLISION_APPROXIMATE_CYLINDERS` | passed | 路径 `/physics/collisionApproximateCylinders`，当前值 `False`；wheel 物理 collider 不是 convex-mesh approximation，GUI 中的有棱外观来自 `UsdGeom.Cylinder` 的 viewport tessellation。 |
| 2026-07-10 | `ruff format/check`, `py_compile`, `git diff --check` after Cylinder preview support | passed | viewer 和 README 最新改动的格式、lint、语法和 whitespace 通过。 |
| 2026-07-10 | `OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/view_serialleg_collisions.py --headless --device cpu --frames 5 --view-mode render` | passed | 退出码 0；报告 11 bodies/10 DOFs、`preview_meshes=54 preview_cylinders=2`，证明两个 wheel Cylinder 已创建 render-only preview prim。仍有既存 inotify `errno=28` 日志噪声。 |
| 2026-07-10 | `OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/view_serialleg_collisions.py --device cpu --view-mode render` after Cylinder support | running/interactive | GUI 启动成功，报告 `preview_meshes=54 preview_cylinders=2`；等待用户目视确认左右 wheel 实体。 |
| 2026-07-10 | pure-Python `serialleg_contract.py` load probe | passed | schema v1；11 links、10 tree joints、2 loops；policy order 为 6 joints，passive partition 为 4 joints。 |
| 2026-07-10 | AppLauncher asset/task contract probe | passed | `SERIALLEG_CLOSED_CHAIN_CFG` 三组 actuator 的 joints/effort/velocity/stiffness/damping 与迁移前逐值一致；6D action scale 为 legs `40.0`、wheels `3.71`。 |
| 2026-07-10 | `OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/convert_serialleg_urdf_to_usd.py` after contract integration | passed | 重建 `534788-byte` USD；metadata 写入 canonical contract path/SHA；11 bodies、10 tree joints、2 loops、54 collision meshes/7102 faces、2 cylinders、0 visual geometry。 |
| 2026-07-10 | `... convert_serialleg_urdf_to_usd.py --check` after contract integration | passed | 磁盘 gate 验证 contract SHA、importer settings、loop armature，以及既有 topology/physics/geometry/size/dependency 合同。 |
| 2026-07-10 | `... smoke_serialleg_usd.py --headless --device cpu --steps 64` after contract integration | passed | 11 bodies/10 DOFs，最大 loop residual 保持 `3.388e-07 m < 1e-05 m`。 |
| 2026-07-10 | direct wheel build + `unzip -l` | passed | 最终 wheel 包含 `16605-byte` `serialleg_contract.py`、`3759-byte` TOML 和 `534788-byte` USD。构建仍输出既存 setuptools dynamic metadata warnings。 |
| 2026-07-10 | Ruff format/check, `py_compile`, `git diff --check` for contract/converter/asset/task/package files | passed | 最新 contract 接入代码格式、lint、语法和 tracked whitespace 通过。 |
| 2026-07-10 | 用户 Isaac Sim GUI visual acceptance | passed | 用户确认 collision-only SerialLeg USD 的实体 preview 与 collision 视觉效果验收通过。 |
| 2026-07-10 | `ruff format/check`, `py_compile` for `scripts/view_serialleg_collisions.py` | passed | 新增 render/collision/both viewer modes 的格式、lint 和语法通过。 |
| 2026-07-10 | `... view_serialleg_collisions.py --headless --device cpu --frames 5 --view-mode render` | passed | 默认实体预览创建 light/material 和 54 个 render-only collision-mesh copies，报告 11 bodies/10 DOFs、`preview_meshes=54`。 |
| 2026-07-10 | `... view_serialleg_collisions.py --headless --device cpu --frames 5 --view-mode both` | passed | 54 个实体 preview copies 与 PhysX collider overlay 可同时初始化，报告 11 bodies/10 DOFs、`preview_meshes=54`。 |
| 2026-07-10 | `ruff format --check`, `ruff check`, `py_compile`, `git diff --check` for `scripts/convert_serialleg_urdf_to_usd.py` | passed | mesh collision schema normalization 的格式、lint、语法和 tracked 工作树 whitespace 均通过。 |
| 2026-07-10 | `OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/convert_serialleg_urdf_to_usd.py` | passed | 重建 USD 并在 flatten 后将 54 个 collision schema 从 importer `Xform` wrapper 迁移到实际 `Mesh` leaves；最终 `534493 bytes`，0 visual geometry、54 meshes/7102 faces、2 cylinders、11 bodies、10 tree joints、2 external loops。 |
| 2026-07-10 | `... convert_serialleg_urdf_to_usd.py --check` | passed | 强制检查 54 个 direct `Mesh` CollisionAPI/MeshCollisionAPI、0 non-geometry wrapper collider、API enabled、全部 `convexHull`，以及既有 articulation/loop/mass/topology/dependency 合同。 |
| 2026-07-10 | Kit USD direct-schema inspection | passed | `direct_mesh_colliders=54`、`wrapper_colliders=0`、mesh approximations=`['convexHull']`。 |
| 2026-07-10 | `... smoke_serialleg_usd.py --headless --device cpu --steps 64` | passed | 11 bodies/10 DOFs；最大 loop residual `3.388e-07 m < 1e-05 m`，schema normalization 未破坏闭环 free-space runtime。 |
| 2026-07-10 | `... view_serialleg_collisions.py --headless --device cpu --frames 5` | passed | viewer 加载新 USD，报告 11 bodies/10 DOFs；headless 模式不构成屏幕 overlay 的人工目视证据。 |
| 2026-07-10 | `OMNI_KIT_ACCEPT_EULA=YES uv run python - <<'PY' ... Usd.Stage.Open(...); inspect CollisionAPI/MeshCollisionAPI ...` | passed with issue found | USD 中 2 个 direct `Cylinder` collider；54 个 mesh collision 的 `CollisionAPI`/`MeshCollisionAPI` 挂在父 `Xform`，`physics:approximation=convexHull`，子 `Mesh` active 且有点面但自身没有 `CollisionAPI`。解释了 GUI 只显示两个 wheel ring，当前 viewer 不能目视验收 mesh collision。 |
| 2026-07-10 | `rg -n -i "collision|collider|convex|meshcollision|triangle|cooking|unsupported|invalid" ...kit logs...` | passed | 未发现直接的 unsupported mesh collision/cooking 报错；日志主要是既有 inotify watch `errno=28` 噪声。仍需补接触 gate 证明 mesh colliders 进入 PhysX。 |
| 2026-07-10 | `OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/view_serialleg_collisions.py --headless --device cpu --frames 5` | passed | 退出码 0；viewer 报告 `colliders=All gravity=disabled root_height=0.220m bodies=11 dofs=10`。直接 process exit 避免当前 inotify exhaustion 导致 Kit teardown 卡住。 |
| 2026-07-10 | `OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/view_serialleg_collisions.py --device cpu` | running/interactive | GUI 进程成功启动并保持运行；自动设置 Physics Colliders=All，等待用户目视检查，关闭窗口后退出。 |
| 2026-07-10 | `ruff format/check`, `py_compile`, `git diff --check` for `scripts/view_serialleg_collisions.py` | passed | viewer 格式、lint、语法和 whitespace 通过。 |
| 2026-07-10 | `OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/convert_serialleg_urdf_to_usd.py` (final collision-only converter) | passed | 最新脚本完成 transient dummy visual workaround、屏蔽 visuals、atomic flatten、canonical layer documentation 和磁盘 gate；最终产物 `534237 bytes`，0 visual geometry、54 collision meshes/7102 faces、2 cylinders、11 bodies、10 tree joints、2 external loops、mass `12.72874580 kg`。 |
| 2026-07-10 | `OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/convert_serialleg_urdf_to_usd.py --check` | passed | 最终磁盘 gate 退出 0；额外验证 11 collision scopes、56 CollisionAPI、54 MeshCollisionAPI、0 active visual scope/Gprim、0 orphan non-collision authored geometry、无语义可见 `/tmp` path、大小 `<5 MiB`。 |
| 2026-07-10 | `OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/smoke_serialleg_usd.py --headless --device cpu --steps 64` | passed | 11 bodies/10 DOFs；最大 loop attachment residual `3.388e-07 m < 1e-05 m`，全部状态 finite，无 closed-articulation error。 |
| 2026-07-10 | collision-only storage/size checks (`stat`, `sha256sum`, `strings`, `git check-attr`) | passed | 最终 USD mode 644、`534237 bytes`、SHA256 `1f60ac375785e14ffbb83f460742c29144dcdab1637b15f57ded87deea729523`，无 `/tmp`/import temp string；比旧 `169667446-byte` USD 小 `99.6851%`，Kyber `lens.usd` 是其 `26.58x`。精确 exception 使 filter/diff/merge/text 均 unset。 |
| 2026-07-10 | 连续两次 collision-only regeneration | passed with note | 两次语义 gate 均完全相同且临时 provenance 已消除；USDC crate binary encoding 分别为 `534250` / `534237 bytes`，binary SHA 不保证每次重建相同，因此 README 只记录约 `522 KiB` 和语义/大小 gate。 |
| 2026-07-10 | `uv build --wheel --out-dir /tmp/se3_rl_lab_wheel_collision_only_final_20260710 source/se3_rl_lab` + `unzip -l` | passed | wheel `63284796 bytes`；明确包含 `27399-byte` canonical URDF 与最终 `534237-byte` USD。wheel 仍约 61M 是因为 package-data 包含完整 source mesh tree。 |
| 2026-07-10 | `ruff format --check` / `ruff check` on three SerialLeg scripts, `py_compile`, `git diff --check` | passed | 三个 scripts 已格式化，Ruff/语法/whitespace 均通过。 |
| 2026-07-10 | `OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/convert_serialleg_urdf_to_usd.py` | passed | Isaac Sim 5.1 importer 2.4.30 生成并原子替换自包含 USD；磁盘重开 gate 报告 default prim 正确、articulation root=`.../base_link`、11 links、10 tree joints、2 external loops、2 cylinders、mass `12.72874580 kg`。 |
| 2026-07-10 | `OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/convert_serialleg_urdf_to_usd.py --check` | passed | 最终新版 validator 严格检查全部 rigid bodies/joints（含重复/额外 prim）、tree graph/body rel、loop local poses/identity rotations/authored exclude、joint/axis armature、source damping、neutral drives、无 finite limits、units/up axis/no scene、mass、2 cylinders/0 capsules和无 unresolved dependencies。退出码 0。 |
| 2026-07-10 | `OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/smoke_serialleg_usd.py` | passed | 默认 CPU/headless，standing state 运行 64 physics steps；`bodies=11 dofs=10 device=cpu max_loop_residual=3.388e-07m threshold=1.000e-05m`，退出码 0；筛选日志无 `closed articulation`/traceback。 |
| 2026-07-10 | `... smoke_serialleg_usd.py --steps 1 --max-loop-residual 1e-9` | expected failure | 实测 residual `2.403e-07 m` 超过人为严格阈值，抛 `RuntimeError` 并退出码 1，证明 threshold/failure path 生效且命令 bounded。 |
| 2026-07-10 | `uv run ruff format/check` + `python -m py_compile` on three SerialLeg scripts; `git diff --check`; `uv lock --check`; MJCF→URDF `--check` | passed | 最新代码格式、lint、语法、whitespace、lock 和 canonical URDF byte gate 全部通过；URDF gate仍报告 11/10/2/77 和 standing residual `2.197e-07 m`。 |
| 2026-07-10 | `uv run python scripts/convert_serialleg_mjcf_to_urdf.py` and `... --check` | passed | 两次均报告 `links=11 tree_joints=10 loop_joints=2 meshes=77 total_mass=12.72874558kg`；`zero_loop_residual=0.000e+00m standing_loop_residual=2.197e-07m`；`--check` 确认磁盘产物与确定性重生成逐字节一致。 |
| 2026-07-10 | `uv run ruff format scripts/convert_serialleg_mjcf_to_urdf.py`; `uv run ruff check ...`; `uv run python -m py_compile ...`; `git diff --check`; `uv lock --check` | passed | 转换脚本格式、lint、语法、工作树 whitespace 和 lock 一致性均通过。 |
| 2026-07-10 | 独立 URDF topology/geometry/inertia audit | passed | 11 links、10 tree joints、2 loops、23 visual、56 collision、77 mesh refs；总质量 `12.728745580000002 kg`；所有 inertia tensors 为 SPD，最小 eigenvalue `2.465e-06`，最小 principal-triangle margin `3.416e-07`。 |
| 2026-07-10 | Isaac Sim 5.1 `URDFParseFile` on generated URDF | passed with caveat | 返回 `parse_status=True`，robot name 正确，11 links/10 joints；日志明确出现两条 `Parsing Loop Joint ...`、`Joint Type 6` 和 `Found base link called base_link`。仅解析，未生成或保存 USD。启动仍有既存 inotify `errno=28` 噪声。 |
| 2026-07-10 | `uv build --wheel --out-dir /tmp/se3_rl_lab_wheel source/se3_rl_lab` and wheel zip inspection | passed | 直接 wheel 构建成功，归档中包含生成的 URDF。 |
| 2026-07-10 | `uv build --package se3-rl-lab` | failed | sdist 创建后，从 sdist 构建 wheel 时既有 packaging 未包含 `source/se3_rl_lab/config/extension.toml`，`setup.py` 读取该文件失败；与新增 URDF 无关，直接 wheel 构建通过。 |
| 2026-07-10 | Earlier URDF→USD generation / SerialLeg PhysX runtime smoke status | superseded | 先前第一阶段有意未运行；本轮已完成 USD 生成、静态 gate 和独立 CPU asset smoke。训练 task 仍未切换。 |
| 2026-07-10 | Read-only inspection of `/home/am345/bioinnov_ws/kyber_rl_lab/kyber_assets/{K1,lens,K2-v0}` URDF/USD and `convert_usd.py` | passed | Canonical URDF uses four spherical `loop_joint` entries per robot；`Usd.Stage.Open(..., Usd.Stage.LoadNone)` 静态检查确认 12 个代表性 USD loop prim 均为 `PhysicsSphericalJoint`，authored `physics:excludeFromArticulation=True`，body/local frames 有值，且 `physxJoint:armature=0.005`。未保存或导出 stage。 |
| 2026-07-10 | Read-only inspection of Kyber training/reset/MuJoCo paths and local Lens run artifacts | passed | Isaac training uses standard pre-generated `UsdFileCfg`/`ArticulationCfg` and active-joint policy interface；Isaac reset 仅 zero close joints。MuJoCo uses `<equality><connect>` and its numerical reset projection is not part of PhysX rollout。Lens logs contain completed `model_1999.pt`/ONNX artifacts。 |
| 2026-07-10 | `rg`/`sed` inspection of `source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg.py` | passed | Current `_add_serialleg_loop_joints()` creates `UsdPhysics.SphericalJoint` body/local position attributes but does not author `CreateExcludeFromArticulationAttr(True)`。 |
| 2026-07-10 | SerialLeg URDF generation / IsaacSim runtime smoke | not run | 用户明确要求本轮只记录方案、先不改；未生成资产、未修改实现、未启动仿真。 |
| 2026-07-10 | `git status --short --branch` in `se3_rl_lab`, Kyber root, and `kyber_assets` | passed | 检查前三个工作树均无未提交内容；本轮随后只更新 `.gitignore` 已忽略的 `.agent-handoff/` 本地记忆。 |
| 2026-07-09 | `git push -u origin main` | passed | 第二次 push 成功，`main -> main`，并设置 `branch 'main' set up to track 'origin/main'`。 |
| 2026-07-09 | `git push -u origin main` | failed | 首次 push 被 GitHub 拒绝：`This repository exceeded its LFS budget`；随后移除 `*.obj` LFS 规则并 amend 提交。 |
| 2026-07-09 | `git lfs ls-files` after amend | passed | 无输出，当前提交不再包含 LFS tracked 文件。 |
| 2026-07-09 | `git diff --check HEAD` after amend | passed | 无输出，提交内容 whitespace 检查通过。 |
| 2026-07-09 | `git commit --amend --no-edit` after removing `*.obj` LFS rule | passed | 最新提交为 `87e145a Initialize IsaacLab SerialLeg migration`。 |
| 2026-07-09 | `git commit -m "Initialize IsaacLab SerialLeg migration"` | passed | 初始本地提交为 `ce4f8d8`；后因 GitHub LFS 配额失败并 amend 为 `87e145a`。 |
| 2026-07-09 | `git diff --cached --check` before initial commit | passed | 曾发现并清理一个 copied XML 的 trailing whitespace，重跑后通过。 |
| 2026-07-09 | `git remote -v` before/after `git remote add origin https://github.com/am345/se3_rl_lab.git` | passed | 初始无 remote；添加后 fetch/push 均为 `https://github.com/am345/se3_rl_lab.git`。 |
| 2026-07-09 | `git status --short --branch` | passed | 当前输出 `## No commits yet on master`，有大量已添加/修改/未跟踪文件；未执行 commit/push。 |
| 2026-07-09 | `uv run python -m compileall scripts source/se3_rl_lab/se3_rl_lab source/se3_rl_lab/setup.py` | passed | 本地包重建/安装成功，新增资产配置、task 配置和 packaging 语法通过。 |
| 2026-07-09 | Direct MJCF import of original `serialleg_closed_chain_v3_train_obb_trim.xml` with `MJCFCreateAsset` | failed | IsaacSim importer 报 `basic_string::_M_construct null not valid`；subagent 盘点确认 mesh 缺失数为 0，问题来自 importer 对 XML 结构支持。 |
| 2026-07-09 | Direct MJCF import variants under `source/.../mjcf/` | mixed | 带 `<equality><connect>` 的变体立刻 `basic_string::_M_construct null not valid`；去 equality 但保留 tendons 报 `Used null prim`；去 equality/tendon 后导入成功并生成 10 个 revolute joints。 |
| 2026-07-09 | Direct USD postprocess test adding two `UsdPhysics.SphericalJoint` loop joints | passed | 在无 equality/tendon 导入模型上成功定义 `/Robot/loop_joints/l_coupler_to_lf_calf` 和 `/Robot/loop_joints/r_coupler_to_rf_calf`，body targets/local positions 正确写入 stage。 |
| 2026-07-09 | `OMNI_KIT_ACCEPT_EULA=YES uv run python -u - <<'PY' ... gym.make("SerialLeg-Flat-ClosedChain-v0") ...` | failed | MJCF 转换和自定义 loop joints 进入 PhysX，但 runtime 报 `closed articulation, which is not supported`；PhysX 排除部分 joints 后 `l_drive_bar_Joint` / `r_drive_bar_Joint` 不在 DOF 列表中，actuator 配置匹配失败。完整筛选日志在 `/tmp/serialleg_closedchain_smoke.log`。 |
| 2026-07-09 | `OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/list_envs.py` | passed with caveat | 退出码 0，IsaacSim 启动成功；stdout 未出现预期环境表格，仅有 Kit/GPU 日志，原因未深挖。 |
| 2026-07-09 | `OMNI_KIT_ACCEPT_EULA=YES uv run python -u - <<'PY' ... AppLauncher(headless=True) ... import se3_rl_lab.tasks ... gym.registry ...` | passed | AppLauncher 启动后 registry probe 输出 `MARK registered True`，`EnvSpec(id='Template-Se3-Rl-Lab-v0', entry_point='isaaclab.envs:ManagerBasedRLEnv', ...)`。 |
| 2026-07-09 | `cat /proc/sys/fs/inotify/max_user_watches /proc/sys/fs/inotify/max_user_instances` | passed | 输出 `65536` 和 `128`；IsaacSim 日志持续报 change watch `errno=28`。 |
| 2026-07-09 | `timeout 60s env OMNI_KIT_ACCEPT_EULA=YES uv run python -u scripts/zero_agent.py --task Template-Se3-Rl-Lab-v0 --num_envs 1 --headless` | failed | CUDA 路径报 `omni.physx.tensors` CUDA OOM，随后 `Exception: Failed to get DOF velocities from backend`。 |
| 2026-07-09 | `timeout 60s env OMNI_KIT_ACCEPT_EULA=YES uv run python -u scripts/zero_agent.py --task Template-Se3-Rl-Lab-v0 --num_envs 1 --headless --device cpu` | passed with timeout | 环境创建完成并进入 simulation loop；打印 Gym observation/action space；外层 `timeout` 后手动终止遗留进程组，最终状态 `124` 属预期控制。 |
| 2026-07-09 | `uv sync` | passed | 创建 `.venv`，使用 CPython 3.11.15；构建 `se3-rl-lab`；prepared 26 packages，installed 247 packages。 |
| 2026-07-09 | `uv run python --version` | passed | 输出 `Python 3.11.15`。 |
| 2026-07-09 | `uv run python -c "import sys, se3_rl_lab; print(sys.executable); print(se3_rl_lab.__file__)"` | failed | 未接受 NVIDIA Omniverse EULA 时 `isaacsim` bootstrap 非交互失败；随后项目 import 走到 IsaacLab USD import，报 `ModuleNotFoundError: No module named 'pxr'`。 |
| 2026-07-09 | `uv run python -c "import isaacsim, sys; print(isaacsim.__file__)"` | failed | `isaacsim` 询问 NVIDIA Omniverse EULA，非交互命令 EOF。 |
| 2026-07-09 | `rg -n "OMNI_KIT_ACCEPT_EULA" .venv/lib/python3.11/site-packages/isaacsim/kit/kit_app.py` / `sed -n '1,260p' .../kit_app.py` | passed | 本地 Kit 入口支持 `OMNI_KIT_ACCEPT_EULA` 为 `y/yes/1`；Agent 未替用户接受 EULA。 |
| 2026-07-09 | `git check-ignore -v AGENT_HANDOFF.md AGENT_SESSION_PROMPTS.md .agent-handoff/snapshot.md` | passed | 三个 handoff 本地记忆路径均命中 `.gitignore`。 |
| 2026-07-09 | `git status --short` | passed | `AGENT_HANDOFF.md`、`AGENT_SESSION_PROMPTS.md`、`.agent-handoff/` 不再显示为未跟踪文件；`AGENTS.md` 和 `.claude/` 仍显示。 |
| 2026-07-09 | `sed -n '1,260p' README.md` | passed | 复读 README，确认已改为中文项目说明。 |
| 2026-07-09 | `rg -n "Template for Isaac|Overview|Installation|Troubleshooting|Key Features|This project|We provide|If you encounter|To setup" README.md` | passed | 无输出，未发现官方英文模板段落残留。 |
| 2026-07-09 | 环境级验证 | not run | 本次只改 README 和 handoff 文档，未运行 `uv sync` 或 IsaacLab 任务。 |
| 2026-07-09 | `/home/am345/IsaacLab/isaaclab.sh --new` via activated `/home/am345/IsaacLab/env_isaaclab` | passed | 生成 external / manager-based / `rsl_rl` 模板到 `/home/am345/se3_rl_lab`。 |
| 2026-07-09 | `uv lock --dry-run` | passed | 解析出 243 packages；需要 `starlette==0.49.1` override 才能兼容当前 IsaacLab/IsaacSim 元数据。 |
| 2026-07-09 | `uv add --dev ruff pre-commit --no-sync` | passed | 写入 dev dependency group 并解析 251 packages。 |
| 2026-07-09 | `uv lock --check` | passed | lock 与当前 `pyproject.toml` 一致。 |
| 2026-07-09 | `uv sync --dry-run` | passed | 计划创建 `.venv`、安装 247 packages、下载 26 packages；未实际安装。 |
| 2026-07-09 | Bootstrap file creation | passed | 已生成初始多文档接力脚手架；仓库特定事实仍需检查。 |
| 2026-07-09 | `python3 /home/am345/.codex/skills/agent-handoff/scripts/bootstrap_handoff.py --repo /home/am345/se3_rl_lab --platform both --layout multi --session-prompts` | passed | 创建 `AGENT_HANDOFF.md`、`.agent-handoff/*.md`、`AGENTS.md`、`.claude/CLAUDE.md`、`AGENT_SESSION_PROMPTS.md`。 |
| 2026-07-09 | `rg -n "UNKNOWN|Template-Se3-Rl-Lab-v0|Current objective|Current status|Immediate next actions|Current Risks|Task Backlog" AGENT_HANDOFF.md .agent-handoff AGENTS.md .claude/CLAUDE.md AGENT_SESSION_PROMPTS.md` | passed | 仅保留有意的 `UNKNOWN` 风险项和规则说明；项目事实已写入 handoff。 |
| 2026-07-09 | `sed -n` 复读 `AGENTS.md`、`.claude/CLAUDE.md`、`AGENT_SESSION_PROMPTS.md`、核心 `.agent-handoff/*.md` | passed | 确认规则块和 session prompts 已落盘，snapshot/backlog/risks/workspace 包含当前状态。 |

## Validation Guidelines

- 记录实际运行过的命令/检查。
- 失败检查要简要写明原因和下一步。
- 有意未运行的检查记录为 `not run`，并写明原因。
- 不粘贴长日志；需要时总结并引用文件。
