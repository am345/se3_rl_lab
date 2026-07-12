# se3_rl_lab

SerialLeg 迁移到 IsaacLab 的新训练仓库。

本仓库从 IsaacLab 官方 external project 模板生成，当前选择为：

- 工作流：Manager-based single-agent
- RL 框架：`rsl_rl`
- 基础任务：`SerialLeg-Flat-ClosedChain-v0`
- 恢复微调任务：`SerialLeg-Recovery-v0`

当前状态：uv 环境已安装，SerialLeg 闭链资产、fixed-tendon coupled limits 和任务 runtime 已接入。
闭链资产已经完成 `MJCF → 开链树形 URDF + spherical loop_joint → importer-generated USD`，并通过 USD 静态 gate、
单环境 CPU/PhysX smoke 和 task-level 单环境 CPU/CUDA smoke。RL 语义迁移已完成自定义 6D delayed action、
34D actor observation、40D critic privileged observation、非跳跃 8D `velocity_height` command、基础
events/domain randomization、terminations、curriculum、IsaacLab 官方 locomotion rewards，以及 feed-forward
RSL-RL MLP/PPO 配置；4 环境最小 PPO update 与 checkpoint save/load round-trip 已通过，目标规模容量验收仍待完成。

## 目标

本仓库只负责 IsaacLab 版 SerialLeg flat 训练迁移，不把可选的旧仓库 `../se3_rl` 作为运行时依赖。

旧仓库只作为迁移参考，用来对齐：

- 6D policy-order 动作：`[LF0, LB, RF0, RB, L_WHEEL, R_WHEEL]`
- 自定义动作延迟
- 34D actor observation
- 40D critic privileged observation
- flat 任务奖励、终止条件和 PPO/MLP 配置

当前动作合同在 raw policy action 层执行逐环境 FIFO 延迟，再按 policy order 分别写入 4 个腿部位置目标和
2 个轮速目标；reset 会清空对应环境的 FIFO，避免跨 episode 泄漏旧动作。actor/critic 观测合同为：

执行器使用显式电机模型，而不是把固定 effort/velocity 上限交给 PhysX 隐式 drive：腿部 DM-8009P 使用
四象限 DC motor 包络（`40 N·m` 峰值、`20 N·m` 持续扭矩、`16.755 rad/s` 空载速度）；轮部
M3508+C620 14:1 先执行 `kd * (target_velocity - measured_velocity)`，再按实测 12 点 T-N 曲线插值裁剪，
可用扭矩从 `32.93 rad/s` 后开始下降并在 `71.81 rad/s` 归零。policy 仍输出相同的腿位置与轮速目标，
`0.25 rad`/`45 rad/s` action scale 不变。

运行时可用下面的全速域 gate 检查实际 IsaacLab actuator 与共享电机规格逐点一致；它同时硬检查 active
joint 未启用 PhysX `velocity_limit_sim`：

```bash
OMNI_KIT_ACCEPT_EULA=YES .venv/bin/python scripts/smoke_serialleg_motor_envelopes.py \
  --samples 801 --headless --device cuda:0
```

- actor 34D：base angular velocity 3D、projected gravity 3D、commands 5D、leg phase/active-angle 6D、
  leg velocity 4D、zero wheel-position slots 2D、wheel velocity 2D、上一拍 clipped policy action 6D、
  jump-command slots 3D；
- critic 40D：完整 actor 34D，再追加 base linear velocity 3D、wheel contact-force norm 2D 和 base height 1D。

当前 `velocity_height` command term 严格输出 8D：`[vx, yaw_rate, pitch, roll, height, jump, jump_height,
jump_phase]`。基础阶段 pitch/roll 与末 3 个 jump slots 始终为零；维度不符或 term 缺失会直接报错。内部派生的
`base_velocity=[vx, 0, yaw_rate]` 只用于把同一采样指令交给 IsaacLab 官方速度跟踪 reward，不改变 policy observation 合同。

当前基础验收阶段采用收敛范围：奖励只配置 IsaacLab 官方 manager-based locomotion 基础项，用于先确认
SerialLeg 迁移到 Isaac Sim 后的速度跟踪、姿态、关节、动作平滑和接触等基本训练链路没有明显问题；
不在这一阶段迁移旧 flat 的自定义奖励语义。旧奖励的 command-driven 高度、分段跟踪核、轮腿专属
penalty/gating 等适配统一推迟到 finetune 阶段。跳跃不属于当前阶段范围，`velocity_height` 的 jump
command 默认保持关闭，其 3 个 jump slots 为零，不接入跳跃奖励、事件或 curriculum。

## Recovery 微调任务

`SerialLeg-Recovery-v0` 从 flat 基础任务继承 scene、6D delayed action、34D/40D observation、8D command、
curriculum 和 feed-forward PPO 合同，仅替换以下三部分：

- reward：迁移 `se3_rl` 的 `se3_wheel_leg_spring_add` 分支中 Recovery-Discovery 的完整 25-term 配置
  （其中 `diagnostics` 恒返回零，只记录合同占位），名称、权重和主要门控参数保持一致；
- reset：按 `standing/left-side/right-side/prone/supine = 8%/17%/17%/29%/29%` 混合标准姿态，
  并从 iteration 1500 起逐步混入 40k settled-state dataset；标准样本按课程随机化完整 policy/passive/wheel
  joint state，dataset 按 joint name恢复 root 与 10-joint position/velocity，IsaacLab 额外的两个 tendon-root
  显式补默认零值；完整 collision 包络用于保证 ground clearance；
- termination：倒地与 `base_link` 接触视为可恢复状态；保留 `time_out`，并用 `catastrophic_state`
  截断非有限状态或已经物理发散的极端速度/高度，避免坏状态进入 PPO。

Recovery 不启用参考仓库的 height-conditioned action default；腿动作零点、`0.25 rad` 腿 scale、`45 rad/s`
轮 scale、raw action clip 和 `4–6 ms` FIFO delay 均保持 flat checkpoint 合同，因此可从 `model_499.pt`
直接 finetune。首次训练前先确认远端数据盘余量和 checkpoint 外部备份位置。

```bash
OMNI_KIT_ACCEPT_EULA=YES uv run se3rl train --task SerialLeg-Recovery-v0 \
  --envs 4096 --iterations 500 --run-name recovery_finetune \
  --resume --load-run <flat-run> --checkpoint model_499.pt
```

训练前建议先运行单环境/少环境 recovery smoke，确认全姿态 reset、接触 body 分组和 reward 数值均为有限值。

## RSL-RL MLP/PPO 合同

训练明确使用 feed-forward MLP，不使用 GRU/LSTM。配置采用当前 IsaacLab/RSL-RL 的分离式
`RslRlMLPModelCfg`，不再使用 deprecated `RslRlPpoActorCriticCfg`：

- observation mapping：actor 读取 `actor` 34D，critic 读取 `critic` 40D；
- actor/critic hidden dims 均为 `[512, 256, 128]`，activation 为 `elu`；
- actor 使用 scalar Gaussian distribution，initial standard deviation 为 `1.0`；
- actor observation normalization 关闭，保持部署输入合同；critic normalization 开启，以处理原始 wheel contact force 与其他 privileged state 的尺度差异；
- 不堆叠 observation history；第一版保持单帧 34D/40D，不引入 recurrent hidden state 或 BPTT；
- rollout 为每环境 24 steps，与现有 command/push curriculum 的 `steps_per_policy_iteration=24` 对齐；
- PPO 使用 clipped value loss、clip `0.2`、entropy `0.01`、5 epochs、4 mini-batches、adaptive `1e-3` learning rate、`gamma=0.99`、`lam=0.95`、target KL `0.01` 和 max grad norm `1.0`；
- 默认训练上限 5000 iterations，每 500 iterations 保存 checkpoint。训练 smoke 应通过 CLI 临时覆盖 iterations，不修改基线配置。

当前 24-step 基线已在 4 个 CPU simulation environments 上完成一次 96-sample PPO update；此前的 64-step 基线也已完成 checkpoint save/load round-trip：

```bash
OMNI_KIT_ACCEPT_EULA=YES .venv/bin/python -u scripts/rsl_rl/train.py --task SerialLeg-Flat-ClosedChain-v0 --num_envs 4 --device cpu --headless --max_iterations 1 --run_name mlp_smoke
OMNI_KIT_ACCEPT_EULA=YES .venv/bin/python -u scripts/rsl_rl/train.py --task SerialLeg-Flat-ClosedChain-v0 --num_envs 4 --device cpu --headless --max_iterations 1 --run_name mlp_resume_smoke --resume --load_run <run-directory> --checkpoint model_0.pt
DISPLAY=:20 OMNI_KIT_ACCEPT_EULA=YES .venv/bin/python -u scripts/rsl_rl/play.py --task SerialLeg-Flat-ClosedChain-v0 --num_envs 1 --device cuda:0 --show_colliders --checkpoint <checkpoint-path>
```

SerialLeg runtime USD 是 collision-only；GUI 回放时使用 `--show_colliders` 将 PhysX Colliders 设置为 `All`，否则普通渲染视口中机器人不可见。

## 实验工具链

仓库提供统一的 `se3rl` CLI，用于一键训练/恢复、run 与 checkpoint 解析、Isaac Eval MP4、固定评估套件、telemetry、Rerun 和 Markdown 对比报告：

```bash
uv run se3rl runs
OMNI_KIT_ACCEPT_EULA=YES uv run se3rl train --envs 4096 --iterations 500 --run-name flat_baseline
OMNI_KIT_ACCEPT_EULA=YES uv run se3rl eval <run> --checkpoint latest
DISPLAY=:20 OMNI_KIT_ACCEPT_EULA=YES uv run se3rl play <run> --checkpoint best
uv run se3rl compare <metrics-a.json> <metrics-b.json> --output reports/comparison.md
```

Isaac Eval 会为 collision-only USD 创建不参与物理的 render preview，因此 MP4 中机器人可见；视频同时显示绿色目标速度箭头和蓝色实际速度箭头。同一次 rollout 还会生成 metrics JSON、逐步 telemetry、Rerun `.rrd` 和 Markdown 报告。完整目录合同、命令和 finetune 前 gate 见 [实验工具链文档](docs/experiment_tooling.md)。

## SerialLeg 机器人配置

`source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg/robot_config.yaml` 是 SerialLeg 资产拓扑、关节角色、
初始状态和闭链参数的人类可读配置来源，采用与 Kyber 类似的语义分层：

- `robot` 声明资产身份、root link、canonical URDF 和 runtime USD；
- `init_state` 集中声明 root pose 和 standing joint pose；
- `joints.groups` 按 legs、wheels 和 closed-chain passive linkage 表达关节角色，`joint_profiles` 集中共享的 armature、PD gain 和 solver safety 参数；
- `joints.policy_order` 锁定 6D action/observation 顺序；legs/wheels 的 `action_scale=0.25/45.0` 由
  `mdp/actions.py` 通过强类型 contract 直接读取，不再维护第二份默认值；
- `usd` 保留 importer 设置和 collision-only artifact gates。

电机物理规格与 T-N 包络集中在 `serialleg_motors.py`，IsaacLab 显式 actuator 实现在
`serialleg_actuators.py`，`serialleg.py` 将腿、轮、passive linkage 分别接到对应模型。训练、play 和 eval
都通过同一 `ArticulationCfg` 消费这套执行器合同。

11 links、10 条 tree parent/child 边、URDF damping/friction 以及 2 条 spherical loop 的 endpoint/local pose 不再在 YAML 重复，而是由 canonical URDF 派生。`serialleg_contract.py` 会强校验 YAML schema、URDF identity/rooted tree、group exact partition、policy order、loop endpoint 和 wheel/importer 不变量。USD converter 与 IsaacLab asset/task 都消费同一个强类型 contract；USD metadata 记录 YAML 路径与 SHA256。修改 YAML 后必须重建 USD 并重跑相关 smoke。

## 环境准备

本仓库使用 uv 管理环境。

IsaacLab 的五个 Python package 通过 `pyproject.toml` 的相对路径 `../IsaacLab/source/...` 以 editable
方式安装，不依赖用户名或 `/home/<user>` 绝对路径。请把 `se3_rl_lab` 与 `IsaacLab` clone 到同一父目录，
并将 IsaacLab checkout 到已验证 commit `b4c321024792976150ca55fddb26fa34480d974e`：

```bash
git clone https://github.com/isaac-sim/IsaacLab.git
git -C IsaacLab checkout b4c321024792976150ca55fddb26fa34480d974e
git clone https://github.com/am345/se3_rl_lab.git
cd se3_rl_lab
uv sync --locked
```

必须保留 IsaacLab source checkout：当前包的 `config/extension.toml` 位于 Python package 的相邻目录，
直接从 Git subdirectory 构建普通 wheel 会破坏这个运行时目录合同。

安装锁定环境：

```bash
uv sync
```

当前 `pyproject.toml` 中已经包含 IsaacLab / Isaac Sim / PyTorch cu128 相关依赖配置，真实 `uv sync` 已验证通过。

## 生成 SerialLeg 闭链 USD

先从 canonical MJCF 确定性生成并检查开链 URDF：

```bash
uv run python scripts/convert_serialleg_mjcf_to_urdf.py
uv run python scripts/convert_serialleg_mjcf_to_urdf.py --check
```

接受 NVIDIA Omniverse EULA 后，通过 Isaac Sim 5.1 importer 生成并检查自包含 USD。canonical MJCF、URDF 和
最终 USD 均为 collision-only，不再携带原始高模 visual。URDF/USD 采用左右各一个 geometry-free virtual mount：
共 13 个刚体、12 个 tree DOF；两个窄限位 virtual revolute joint 作为 PhysX fixed tendon root，原 10 个 source DOF
和两条 external spherical loop joints 保持不变：

```bash
OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/convert_serialleg_urdf_to_usd.py
OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/convert_serialleg_urdf_to_usd.py --check
```

运行 bounded CPU/PhysX gate：

```bash
OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/smoke_serialleg_usd.py --headless --device cpu --steps 64
```

运行 400 步地面接触力 gate；该模式强制确认左右 wheel 仍是 direct `Cylinder` collider、
`/physics/collisionApproximateCylinders=False`，并通过 IsaacLab `ContactSensor.net_forces_w` 验收两个轮子和至少一个
mesh-backed link 的有限非零接触力：

```bash
OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/smoke_serialleg_usd.py --headless --device cpu --ground-contact
OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/smoke_serialleg_usd.py --headless --device cuda:0 --ground-contact
```

free-space 闭环 residual gate 保持 `1e-5 m`；ground-contact 包含落地与后续 mesh 冲击，单独使用
`2e-4 m` gate。render-only collision preview 无 Physics API，不参与该测试。

在切换 task runtime 前，用独立 A/B smoke 验证两条 external spherical constraints 确实主动维持闭链：

```bash
OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/smoke_serialleg_closed_chain.py --headless --device cpu
OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/smoke_serialleg_closed_chain.py --headless --device cuda:0
```

该 gate 在同一 stage 中生成两个相同机器人：`Closed` 保持 loop joints 启用，`OpenControl` 只在运行时
关闭这两条 joints。两者承受相同的成对反向周期外力；验收要求 closed 逐侧 residual `<2e-5 m`、
open control residual `>1e-3 m`、逐侧 A/B 差异 `>400x`，且 closed 关节实际运动 `>1e-3 rad`。

对完整 Gym task 运行单环境 bounded gate：

```bash
OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/smoke_serialleg_task.py --headless --device cpu
OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/smoke_serialleg_task.py --headless --device cuda:0 --compact-gpu-buffers
OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/smoke_serialleg_task.py --headless --device cpu --num-envs 4
OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/smoke_serialleg_task.py --headless --device cuda:0 --num-envs 4 --compact-gpu-buffers
```

该 gate 验证 `gym.make/reset/step`、13 bodies/12 DOFs/2 fixed tendons、两个 virtual root 无 actuator、6D policy action 顺序与 scale、4 个 passive source DOF 零 target/effort、standing reset、严格 8D command/差速轮速预算/非跳跃零槽位、官方 reward 与 termination 接线、课程终态、固定状态速度跟踪 reward、零/小幅动作有限状态、地面接触和 loop residual。默认使用 8+8 个环境步的短 gate；更长的零动作 rollout 在启用摔倒/底盘接触 termination 后可能按设计提前结束。task 使用 `16/4` solver iterations：velocity iterations 与 Kyber 高冲击闭链任务一致，position iterations 针对 SerialLeg 闭合误差加倍。物理步长为 `dt=0.005`、`decimation=4`。task pose residual gate 为 `1e-3 m`，对齐 Kyber MuJoCo 闭链 pose projection 的警告阈值；asset free-space/contact gates 仍分别保持 `1e-5/2e-4 m`。

`--compact-gpu-buffers` 只缩小该单环境 gate 的 PhysX GPU 预分配，不改动训练环境默认 capacity。当 GPU 上同时运行大规模训练时，默认 `2**23` rigid-contact buffer 可能因显存不足而在 rollout 前 OOM。

在 Isaac Sim GUI 中以 standing 姿态交互查看实体 collision geometry：

```bash
OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/view_serialleg_collisions.py --device cpu
```

默认 `--view-mode render` 会关闭 PhysX 绿色线框，在 viewer stage 内从同一份 collision geometry 创建蓝灰色、无物理 API 的
render-only preview 并添加灯光；预览包括 54 个 mesh 和 2 个 wheel cylinder，每个副本挂在对应的运动刚体下，
因此会跟随关节动作；不向训练 USD 写入 visual 或增加其磁盘体积。GUI 会同时打开 `SerialLeg Collision + Closed Chain`
控制面板：

- 4 个主动杆关节使用绝对角度滑块；每根杆以 standing angle 为中心覆盖完整 `2π` 行程，不设虚假的单关节机械限位；
- 每侧两根杆的组合按 fixed-tendon coordinate 实时约束在 `[0, 1.509535] rad`，拖动一根杆越界时会截断该杆目标；面板同时显示 target/actual 夹角；
- 2 个 wheel joint 使用 velocity-target 滑块；
- 4 个 passive closed-chain joints 不直接下命令，面板实时显示它们的实际位置；
- 两条 loop attachment residual 实时显示，默认阈值为 `2e-4 m`；
- `Reset standing pose` 硬重置关节状态，`Standing + zero wheels` 将杆目标恢复为 standing 并清零轮速。

viewer 默认固定 base 以方便观察机构；需要查看 floating-base 反作用时使用 `--floating-base`。需要无手动滑块的
自动闭链动画或 bounded headless gate 时使用：

```bash
OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/view_serialleg_collisions.py --device cpu --demo-motion
OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/view_serialleg_collisions.py --headless --device cpu --frames 240 --demo-motion
```

需要物理调试时可用：

```bash
OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/view_serialleg_collisions.py --device cpu --view-mode both
OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/view_serialleg_collisions.py --device cpu --view-mode collision
```

`both` 表示实体渲染加 PhysX 线框，`collision` 只显示线框。绿色表示 dynamic collider，洋红色表示 static collider，
深红色表示 PhysX 使用了 fallback geometry；也可在 Eye 菜单中手动切换。

canonical URDF 本身没有 visual。为规避 Isaac importer 的无 visual 悬挂引用，转换器临时给 13 个 link
各放一个透明 `1e-6 m` sphere；导入后立即屏蔽这些 `visuals` scope，再 flatten。最终 USD 只有 54 个 collision mesh
和 2 个 wheel cylinder，visual geometry 为 0；viewer 的实体模式显示的正是这些 collision geometry，而不是原始高模 visual。

源 mesh 树也已收敛到这 54 个 collision STL：32 个 base collision、6 个 `sw_collision_v3` 腿部 collision 和
16 个 `leg_coacd_v1` 四连杆 collision，合计 `359636 bytes`。canonical MJCF、import MJCF 与 URDF 的引用闭包完全一致，
不再打包旧 surrogate/fidelity 模型、OBJ、高模 visual 或未引用的 collision 分解；直接构建的 wheel 约 `303 KiB`。

当前 USD 约 `522 KiB`，整个 `serialleg/` 资产目录约 `940 KiB`，并由 gate 限制 USD 不超过 `5 MiB`。它通过精确 `.gitignore` / `.gitattributes` 例外作为
普通 Git 文件随仓库交付，不占用当前不可用的 Git LFS 配额；其他 USD 仍保持原有忽略/LFS 策略。

## 验证任务注册

列出已注册环境：

```bash
uv run python scripts/list_envs.py
```

`SerialLeg-Flat-ClosedChain-v0` 已切换到预生成 USD，并接入 delayed 6D action、34D actor observation 和
40D critic privileged observation、非跳跃 command/events/terminations/curriculum 与官方基础 locomotion
rewards，以及 feed-forward MLP/PPO 配置。可用上述 task smoke 进行 CPU/CUDA 单环境和多环境回归；4 环境最小训练与 checkpoint round-trip 已验收，目标规模训练尚未验收，自定义奖励适配推迟到 finetune。

## 主要目录

```text
.
├── pyproject.toml
├── uv.lock
├── scripts/
│   ├── list_envs.py
│   ├── zero_agent.py
│   ├── random_agent.py
│   └── rsl_rl/
│       ├── train.py
│       └── play.py
└── source/
    └── se3_rl_lab/
        ├── pyproject.toml
        └── se3_rl_lab/
            └── tasks/
                └── manager_based/
                    └── se3_rl_lab/
```

当前官方模板 task 的关键文件：

- `source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/__init__.py`
- `source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/se3_rl_lab_env_cfg.py`
- `source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/agents/rsl_rl_ppo_cfg.py`
- `source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/mdp/rewards.py`

## 下一步迁移顺序

建议按小步推进：

1. 运行有策略控制的长 rollout 和 fixed-tendon enabled/disabled 专项 A/B，检查有限状态、闭环 residual、virtual-root drift 与接触稳定性。
2. GPU 空闲时按目标环境数定标 PhysX contact/pair buffers，再启动目标规模短训练验收。
3. 仅在上述基础链路稳定后进入 finetune，届时再适配旧 flat 自定义奖励与 command normalization；跳跃保持关闭，除非后续明确重新纳入范围。

## 代码质量

格式化和检查：

```bash
uv run ruff format .
uv run ruff check .
uv run pre-commit run --all-files
```

## Agent 接力

本仓库启用了多文档 Agent handoff：

- `AGENT_HANDOFF.md`：接力索引
- `.agent-handoff/snapshot.md`：当前状态
- `.agent-handoff/workspace.md`：仓库地图
- `.agent-handoff/backlog.md`：后续任务
- `.agent-handoff/risks.md`：风险和未知项

新 Agent 接手时，先读 `AGENT_HANDOFF.md`，再按其中的 Recovery Reading Order 读取相关状态文件。

## IDE 设置

如果 VSCode / Pylance 找不到 IsaacLab 或 Omniverse 模块，可以在 `.vscode/settings.json` 中加入额外搜索路径，例如：

```json
{
  "python.analysis.extraPaths": [
    "${workspaceFolder}/source/se3_rl_lab"
  ]
}
```

同时将 VSCode Python interpreter 设为 `${workspaceFolder}/.venv/bin/python`；editable 安装的 IsaacLab
packages 会由该环境直接提供，无需在编辑器配置中写入用户目录绝对路径。

如果 Pylance 因索引 Omniverse 包过多而崩溃，可以排除暂时不需要的 extscache 路径。
