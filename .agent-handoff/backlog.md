# Task Backlog

- [x] 停止 `recovery_motor_tn_fresh_5k`；新增 Recovery 专用 PPO 配置，对齐参考的 `0.5/0.00516/3e-4/0.008`，保留 MLP/24-step rollout，并完成 4096-env gate。
- [ ] 监控 `recovery_ref_std_fresh_5k` 跨过 iteration 210、500、650、835、1500、2000、5000；检查 std、NaN/OOM、catastrophic 比例、dataset 混入和 checkpoints。
- [ ] 5k 完成后运行同一 flat-basic/recovery suite，比较 linear/yaw RMSE、自起成功率并录制 MP4。

- [x] 迁移腿部 DM-8009P 四象限 DC motor 与轮部 M3508+C620 14:1 实测 T-N 曲线，保持 policy/action 合同不变。
- [x] 用显式电机模型跑 4096-env/1-update gate，并从头启动 recovery 5k。
- [x] 将 `robot_config.yaml` 的 legs/wheels action scale 修正为 `0.25/45.0`，action term 改为直接读取 contract，并重建 USD/更新 contract SHA。

- [x] 为 `WIN-46S653M0DI0` 建立默认 GPUFree 执行环境：SSH key/alias、GitHub reverse proxy、Selkies GUI local forward、sibling repos、locked `.venv`、RTX 4090 CUDA 与 Isaac Sim SerialLeg smoke 均已验证。
- [ ] 开始长训练前确认数据盘剩余空间并制定 checkpoints/logs 外部备份；当前 49GB 数据盘同时承载约 19GB `.venv`、uv cache、仓库和训练产物，释放实例前不得假设数据一定保留。
- [x] 运行真实 `uv sync` 创建 `.venv` 并安装当前锁定依赖。
- [x] 用户确认接受 NVIDIA Omniverse EULA 后，用 `OMNI_KIT_ACCEPT_EULA=YES` 验证 IsaacSim 可启动，并用 registry probe 确认 `Template-Se3-Rl-Lab-v0` 注册。
- [x] 用 CPU/headless zero agent 验证官方模板环境可创建并进入 simulation loop。
- [x] 重新验证完整 SerialLeg CUDA env：默认 capacity 在并行 Kyber 训练占用 5.3 GiB 时仍因 640 MiB contact buffer 预分配 OOM；单环境 compact capacities 通过完整 rollout。
- [x] 在 GPU 空闲时复测默认 CUDA capacity：4096-env 使用默认 buffers 完成 1 PPO update；未复用单环境 compact 值。长训练峰值显存与并行负载余量继续在目标训练项验收。
- [x] 用户检查并确认 URDF-only 双 virtual-root candidate 的 topology、命名、窄限位和 inertial split。
- [x] 更新 `robot_config.yaml` / `serialleg_contract.py` 为 schema v3 的 13-link/12-joint contract，并在 USD converter author 两条 PhysX fixed tendon；root `gearing=0` / `forceCoefficient=0` 已被 Isaac Sim 5.1 接受。
- [x] fixed-tendon USD 通过静态 gate、CPU virtual-root drift/coupled range/free-space、external-loop A/B 和完整 Gym task active-control gates。
- [ ] 补充 fixed-tendon CUDA ground-contact、长 rollout、多环境与 tendon enabled/disabled 专项 A/B 定标。
- [ ] 可选：提升 Linux inotify `max_user_watches`，减少 IsaacSim `Failed to create change watch ... errno=28` 日志噪声。
- [ ] 后续再决定是否把当前完整 Isaac Sim lock 简化为轻量 uv workspace；如调整，更新 `pyproject.toml`、`source/se3_rl_lab/pyproject.toml`、`uv.lock` 和 README。
- [x] 将官方模板 task 重命名/收敛为 SerialLeg flat 初始骨架（当前名 `SerialLeg-Flat-ClosedChain-v0`，但 direct closed-chain smoke 未通过）。
- [x] 和用户确认 closed-chain 路线：采用 Kyber 风格“开链树形 URDF + importer-generated external spherical loop constraints”，surrogate 不作为当前首选。
- [x] 从 canonical closed-chain MJCF 确定性生成可审计的开链树形 URDF，保留刚体/惯量/visual/collision/树内关节语义，并把两组 equality site-pair 转成 `<loop_joint type="spherical">` 的两端局部 pose。
- [x] 对生成 URDF 完成静态 gate：源/产物拓扑与 mesh 一一对应、惯量 SPD、零/standing/确定性关节姿态 frame 等价、loop residual，以及 Isaac Sim 5.1 `URDFParseFile` 识别两条 spherical loop joints。
- [x] 用 Isaac Sim URDF importer 离线生成自包含 USD；静态校验 articulation root、10 个树内 DOF、loop body/local frames、authored `physics:excludeFromArticulation=True`、armature/中性 drive、无意外 fixed/merged joints及 wheel cylinder。
- [x] 对新 USD 运行独立单环境 CPU/headless asset smoke：11 bodies/10 DOFs，standing reset 后 64 步最大 loop residual `3.388e-07 m`，无 `closed articulation` 或非有限状态。
- [x] 提供 Isaac Sim GUI collision viewer：standing pose、gravity disabled、PhysX Colliders=All，并通过 5-frame headless gate。
- [x] 修正 collision schema：在 flatten 后将 54 个 mesh collider 规范化到实际 `Mesh` prim，移除 wrapper API；静态/direct-schema、free-space smoke 和 viewer headless gate 已通过。
- [x] 完成 GUI 目视核对：用户已验收默认 `render` 实体 preview 与 `both` collision overlay 的视觉效果。
- [x] 将 collision viewer 升级为 contract-driven 交互闭链验收工具：运动刚体子级 preview、4 leg position/2 wheel velocity controls、4 passive joint 位置和 2 loop residual 实时显示、reset/zero、fixed/floating base 与 demo-motion gate。
- [x] 参考 Kyber 建立 SerialLeg 声明式 contract，并让 converter 与 IsaacLab asset/task 共用 topology、joint dynamics、policy/passive、actuator/action scale 和 importer/gate 配置；USD metadata 锁 contract SHA。
- [x] 将人工 contract 从 TOML 迁移为 Kyber 风格 `robot_config.yaml` schema v2；YAML 只保留语义角色/参数，tree topology、URDF dynamics 和 loop frames 由 canonical URDF 派生，同时保留强类型校验与 USD SHA gate。
- [x] 增加 asset-level CPU/CUDA 地面接触力 smoke：验证两个 custom wheel Cylinder 和至少一个 direct-mesh-backed body 的 `ContactSensor.net_forces_w`，并保持闭环 residual 在 contact gate 内。
- [x] 在 task runtime 切换前完成 asset-level CPU/CUDA dynamic closed-chain-effect gate：可重复外力激励、逐 loop residual/joint motion/有限状态，并以 constraints enabled/disabled 同 stage A/B 证明 closure 由 external spherical joints 主动维持。
- [x] 将 `SerialLeg-Flat-ClosedChain-v0` 的 asset config 从旧 MJCF custom spawner 切换到 contract-driven `UsdFileCfg`，并删除 runtime loop-joint 重建路径。
- [x] 对已切换 USD 的 `SerialLeg-Flat-ClosedChain-v0` 完成 task-level CPU/compact-CUDA gate：6D policy actuator 精确匹配、4 passive DOF 零 target/effort、standing reset、零/受控动作/地面接触下 residual 与有限状态均通过。
- [x] 将 USD runtime、YAML contract 与 task gate 作为 PR #2 发布并 squash merge 到 `main`；合并提交为 `0e0f401`。
- [x] 将 runtime USD 改为 collision-only（最终约 522 KiB），通过精确 `.gitignore` / `.gitattributes` 普通 Git exception 随仓库交付，不占用 LFS quota。
- [ ] 仅在 importer-generated external-loop 路线经静态和 runtime gate 明确失败后，重新评估 fourbar surrogate/open-chain 近似或 MuJoCo/MJLab 后端。
- [x] 将 `serialleg` canonical 链改为 collision-only，删除 253 个非闭包 mesh 和 3 个旧 MJCF，只保留精确 54 个 collision STL；资产目录降至 `962770 bytes`，direct wheel 降至 `309906 bytes`。
- [x] 将本地 Git 历史重写为单一 collision-only root commit 并 aggressive GC；`.git` 最终为 `1110734 bytes`，无不可达对象。
- [x] 使用精确 lease `87e145a` force-push 新 root `72a2cd8`，并以全新 GitHub clone 验证 `.git=516778 bytes`、总目录 `2112533 bytes`。
- [ ] 改进 ground-contact smoke：区分瞬时撞击峰值与稳态支撑力，记录 peak step/base 高度/竖直速度，并增加受控 standing contact 统计。
- [x] PR #1 已 squash merge，将 `serialleg_closed_chain_complex_collision` 文件与内部合同命名迁移进入 `main`。
- [ ] 可选：为 canonical URDF 外部引用的 54 个 collision STL 增加聚合 SHA，或按 link/name 锁 points+indices+xform fingerprint；当前 gate 只锁 canonical XML hash 与 collision 聚合 topology/counts。
- [x] 按用户要求完成首个 commit 并推送到 GitHub `origin/main`。
- [x] 迁移 custom delayed 6D action：腿位置/轮速度旧 policy scale、active-tendon coordinate、逐环境 FIFO 与 partial reset。
- [x] 迁移 34D actor / 40D critic observation，并增加布局/数值/virtual-root 隔离测试和 CPU/CUDA task shape gate。
- [x] 迁移 flat `velocity_height` commands、基础 events/domain randomization、terminations 和非跳跃 curriculum；已移除 transitional fallback，严格保持 8D command，pitch/roll 与 jump 3D 当前为零。
- [x] 只配置 IsaacLab 官方 manager-based locomotion 基础 rewards，并用固定状态、CPU/CUDA 1/4 环境短 rollout 验证迁移后的基本训练链路。
- [x] 迁移 feed-forward RSL-RL MLP/PPO cfg：分离 actor/critic obs-group mapping、`[512,256,128]` ELU、actor normalization off、critic normalization on、24-step rollout；当前 4-env/96-sample 最小 PPO update 已通过，此前同结构 checkpoint save/load round-trip 已通过，不使用 GRU/BPTT。
- [x] 完成 finetune 前两阶段工具链：`se3rl` train/resume/play/eval/record/runs/compare、manifest/status、best checkpoint、collision-only MP4、flat-basic metrics/telemetry、Rerun 和 Markdown 报告，含真实 train/eval gate 与文档。
- [ ] 扩展 `flat-basic` 为多 seed 聚合，并继续训练/评估更高 velocity stages 和 push curriculum；当前 model_499 只到 velocity stage 1、push stage 0。
- [x] 新增 `SerialLeg-Recovery-v0`，迁移 Recovery-Discovery reward、完整 reset/dataset 与 hard-error termination；保持 flat action/observation 合同。
- [x] 完成 dataset 10→12 joint remap、passive/tendon-root、clearance 与 4096-env gate，并启动当前 fresh 5k。
- [ ] 低优先级/finetune：重新评估 command observation normalization。当前 legacy scale 会令最终 `vx=±2.4 m/s` 映射为 `±4.8`，且 height 未中心化；若修改，必须同步训练、play、deploy/sim2sim 与 checkpoint 兼容策略。
- [x] 按用户最新要求取消 handoff 的 `.gitignore` 规则，将 `AGENT_HANDOFF.md`、`AGENT_SESSION_PROMPTS.md` 与 `.agent-handoff/*.md` 纳入 Git，支持跨电脑恢复；原“本地私有”策略已废止。

## Backlog Guidelines

- 待办必须可执行。
- 移除已完成或过期事项。
- 有帮助时，把事项关联到风险、决策或文件。
