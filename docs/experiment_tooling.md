# SerialLeg 实验工具链

本工具链围绕一个原则设计：训练、评估、视频、诊断和报告都以同一个 run 目录为事实来源。它不替换 IsaacLab 或 RSL-RL，只为现有入口提供稳定的生命周期管理。

## 能力范围

当前包含前两个阶段：

1. 统一 `se3rl` CLI、run/checkpoint 解析、manifest/status、Isaac Eval、collision-only MP4 和固定评估套件。
2. 统一 telemetry、Rerun `.rrd`、best checkpoint 选择与 Markdown 报告/对比。

当前不包含 Viser、MuJoCo sim2sim 和真机部署。`SerialLeg-Recovery-v0` 保持 flat 的 action 接口，但采用
当前 8D command + 五帧 proprioception 历史：actor/critic 输入分别为 138D/168D。它还迁移
Recovery-Discovery reward、全姿态 reset，以及 `time_out + catastrophic_state` termination。由于输入层
形状改变，Recovery 必须创建新 run，不能直接恢复 34D/40D flat checkpoint。

Recovery 的 yaw tracking 保留 25-term 合同中的权重与直立门控，但启用参考 flat reward 的大误差梯度语义：
`sigma_eff = sigma * (1 + 0.4 * |cmd_yaw|)`，并将 80% 指数精度项与 20% 比例方向项混合。参考
Recovery-Discovery 配置原本将这两个参数设为零；这里是为了避免高 yaw 命令下纯指数核梯度消失而做的显式偏离。

Recovery reset 使用随仓库交付的 `serialleg_closedchain_stair_v3_40k.npz`（20k train/20k eval）与标准
五姿态混合课程。完整 joint reset 会同步写入 policy、passive、wheel 和 virtual tendon-root position/velocity；
cache 比例在 iteration `1500/2000/2600/3400/4200` 提升到 `10%/25%/45%/60%/70%`。

## 安装与入口

同步锁定环境后，`se3rl` 会作为 package entry point 安装：

```bash
uv sync --locked
uv run se3rl --help
```

Isaac Sim 命令仍需接受 EULA：

```bash
export OMNI_KIT_ACCEPT_EULA=YES
```

## 一键训练与恢复

启动默认 4096-env/500-iteration 平地训练：

```bash
uv run se3rl train --envs 4096 --iterations 500 --run-name flat_baseline
```

启动新的 Recovery 历史观测训练：

```bash
uv run se3rl train --task SerialLeg-Recovery-v0 --envs 4096 --iterations 500 \
  --run-name recovery_history5
```

run manifest 会把该任务记录为 `reward_profile=recovery_discovery` 和 138D/168D observation；flat 任务仍记录
为 `official_base` 和 34D/40D observation。

恢复指定 run：

```bash
uv run se3rl resume 2026-07-11_14-06-42_cuda4096_500iter_flat \
  --checkpoint latest --envs 4096 --iterations 500 --run-name flat_continue
```

CLI 将调用仓库现有 `scripts/rsl_rl/train.py`。训练结束后写入：

- `manifest.json`：task、原始命令、Git SHA/状态、动作/观测合同、reward profile。
- `status.json`：训练状态、退出码、latest/best checkpoint 和最后一次评估。

额外的底层训练参数可以放在命令末尾；它们会原样传给训练脚本。

## Run 与 checkpoint 选择

列出 run：

```bash
uv run se3rl runs
```

run 可以使用完整路径、完整目录名或唯一子串。checkpoint selector 支持：

- `latest`：iteration 最大的 `model_*.pt`。
- `best`：`status.json` 中评分最高的 checkpoint；尚无评估时回退到 latest。
- 数字，例如 `499`。
- checkpoint 的完整文件路径。

播放 best checkpoint：

```bash
DISPLAY=:20 uv run se3rl play <run> --checkpoint best
```

`play` 默认启用 PhysX collider overlay，适配 collision-only runtime USD。

## Isaac Eval 与 MP4

运行默认 `flat-basic` suite：

```bash
uv run se3rl eval <run> --checkpoint latest
```

缩短单个 scenario 以做 smoke：

```bash
uv run se3rl eval <run> --checkpoint 499 --scenario-duration 0.5
```

`record` 是 `eval` 的别名。默认 suite 包含：

- `stand`
- `forward_slow`
- `reverse`
- `yaw_left`
- `yaw_right`
- `forward_turn`

评估使用独立 Isaac Sim worker，固定为 1 个 environment 和 seed 47。worker 直接写入严格 8D `velocity_height` command，不修改训练环境合同。worker 会在创建环境前把 episode timeout 与 command resampling 推迟到整套场景结束之后；每次切换场景时，先写入新命令并刷新 policy observation，再执行第一次推理。因此默认 6×4 秒录制不会在第 20 秒触发 reset，也不会被训练用的 5 秒命令重采样污染。

评估会启用 `VelocityHeightCommand.debug_vis`：绿色箭头表示目标平面速度，蓝色箭头表示机器人实际平面速度。默认 marker 基准 scale 为 `(1.0, 0.18, 0.18)`，速度长度倍率为 `3.0`，位于机器人上方 `0.35 m`。录制相机保持世界坐标朝向固定，只按机器人 root 位移平移，eye offset 为 `(0.0, -2.4, 0.57) m`；水平 FOV 在默认值上扩大 30%。为保证 marker 在相机录制中稳定可见，eval-only 配置固定初始 x/y/yaw 并关闭 Fabric；训练配置仍保留随机 reset 和 Fabric。

### Collision-only 渲染

SerialLeg runtime USD 不包含 visual mesh。评估 worker 会从 env_0 的 54 个 collision meshes 和 2 个 wheel cylinders 创建 render-only 副本：

- 副本挂在对应运动刚体下，随机器人运动；
- 不附加 collision/rigid-body API，不参与物理；
- 副本位于独立的 world-space preview 树中，并在每个控制步从 articulation body tensor 显式同步位姿；不能把副本直接挂在 replicated body prim 下，否则录制时可能出现“物理机器人已移动、画面外壳停在原点”的假象；
- 使用正常相机渲染，因此 MP4 不依赖 GUI debug overlay；
- runtime USD、YAML 和物理资产不会被修改。

几何数量变化会让评估硬失败，以防静默录出空视频或不完整机器人。

## 评估产物

```text
<run>/
├── manifest.json
├── status.json
├── isaac_eval/
│   ├── contexts/model_<iter>.isaac_eval.json
│   ├── videos/model_<iter>-step-0.mp4
│   ├── metrics/model_<iter>.metrics.json
│   ├── metrics/model_<iter>.telemetry.json
│   └── latest_result.json
├── rerun/model_<iter>.rrd
└── reports/model_<iter>.evaluation.md
```

metrics 包含：

- 各 scenario 的 `vx`/yaw-rate RMSE 与 termination 次数；
- 总 survival rate；
- 最大 loop residual；
- 最大 virtual-root drift；
- 非有限样本计数；
- preview geometry 数量。

telemetry 为逐步 JSON，MP4、metrics 和 Rerun 来自同一次 rollout，时间轴一致。

## Rerun

打开记录：

```bash
uv run rerun <run>/rerun/model_499.rrd
```

当前记录 command、base velocity/yaw rate、base height、termination、loop residual 和 virtual-root drift。Rerun 固定为 `0.20.3`，因为 IsaacLab 当前依赖 NumPy `<2`，而新版 Rerun 0.31 要求 NumPy 2。

## Best checkpoint 与对比报告

每次成功评估后会计算统一分数：高 survival、低 tracking RMSE、低 loop residual 和低 virtual-root drift 得分更高。若得分超过历史 best，`status.json` 会更新 `best_checkpoint` 和 `best_score`。

比较多个 metrics：

```bash
uv run se3rl compare \
  <run-a>/isaac_eval/metrics/model_499.metrics.json \
  <run-b>/isaac_eval/metrics/model_999.metrics.json \
  --output reports/baseline-vs-finetune.md
```

分数用于同一 task/suite 的 checkpoint 排序，不应跨机器人、不同 suite 或不同指标版本直接比较。

## 关闭可选产物

```bash
uv run se3rl eval <run> --no-video
uv run se3rl eval <run> --no-rerun
```

metrics、telemetry 和 Markdown 报告始终生成。

## Finetune 前 gate

进入 finetune 前至少确认：

1. baseline run 有 `manifest.json` 和 `status.json`；
2. `flat-basic` 完整评估成功；
3. MP4 中机器人可见；
4. metrics 无非有限样本；
5. loop residual 与 virtual-root drift 在可接受范围；
6. `.rrd` 可由 Rerun 打开；
7. baseline evaluation report 已保留，供 finetune A/B 对比。

## 已知边界

- 当前 eval 是显式 CLI 触发，不在训练进程内部自动启动，避免 4096-env 训练与渲染 worker 争抢 GPU。
- `flat-basic` 目前使用单一固定 seed；正式 reward A/B 应扩展为多 seed 聚合。
- survival rate 是逐 step termination 比例的补数；报告同时保留各 scenario termination 次数。
- Rerun 当前专注时序诊断，没有实现完整 3D robot viewer；交互浏览器属于后续 Viser 阶段。
