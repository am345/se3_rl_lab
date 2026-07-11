# Risks, Blockers, And Unknowns

## Current Blockers

- 双 virtual-root URDF、schema-v3 contract、fixed-tendon USD 与 task runtime 已统一，无本轮 CPU/runtime blocker。
- `SerialLeg-Flat-ClosedChain-v0` 的 CPU 与 compact-buffer CUDA 单环境 `gym.make/reset/step` gate 均已通过，无已知 task 逻辑 blocker。
- 默认 CUDA PhysX capacity 在当前 GPU 上同时运行的 Kyber 4096-env 训练占用 `5300 MiB` 时仍会 OOM；失败为 `mGpuContactPairsDev` 预分配 `671088640 bytes`，发生于 rollout 前。`--compact-gpu-buffers` 单环境通过，但这些 capacity 不可未经定标直接用于大规模训练。

## Current Risks

- `WIN-46S653M0DI0` 的默认运行依赖本机 SSH alias `se3_rl_lab_gpufree`。仓库不保存实际 endpoint、密码、私钥或 TURN 凭据；若 alias 缺失，先检查本机 `%USERPROFILE%\.ssh\config`，不要把凭据补进 tracked 文档。
- 远端 GitHub 代理依赖至少一条活跃 SSH reverse forward：本机 `127.0.0.1:7897` → 远端 `127.0.0.1:7890`。旧 VS Code/SSH 连接可能已经占用 7890；这通常不是异常。若所有 SSH 连接断开，远端 `.bashrc` 仍会保留 proxy 变量但端口无 listener，GitHub 请求会超时。
- 不要让 PyTorch/NVIDIA/PyPI 大包走上述 reverse proxy。首次 `uv sync` 曾因 `download-r2.pytorch.org` 未命中 `NO_PROXY` 而极慢；重试时保留 `/root/gpufree-data/.cache/uv`，并直连 `.pytorch.org`、`.nvidia.com`、`pypi.org`、`.pythonhosted.org`。
- 服务器系统内 `reboot` 后曾出现 PCI 可见 RTX 4090、但 `/dev/nvidia*` 缺失且 `torch.cuda.is_available()==False`；需要在 GPUFree 控制台重新分配 GPU。Python 环境和 19GB 依赖无需重装。
- GUI 依赖 GPUFree 自动启动的 `Xorg :20`/Selkies/nginx 和 SSH `LocalForward 3000`。端口 3000 被占用通常表示已有 tunnel；远端重启后需重新连接 SSH并重新启动 GUI 脚本。训练应默认 `--headless`，避免无意长期占用 GUI/Vulkan 资源。
- 远端 49GB 数据盘当前同时放置 `.venv`、约 20GB 级 uv cache、仓库和训练输出，空间不是无限。清 cache 前确认 `.venv` 已完成同步；重要 checkpoints/logs 应在释放实例前备份到独立持久位置。
- VS Code Remote-SSH 曾因多连接、远端安装大型 `openai.chatgpt` extension 和打开过大的目录而明显卡顿。保持 Codex/ChatGPT extension 在本地 UI 侧、`remote.SSH.useExecServer=false`，只打开远端项目根；如再次变慢，先用 `diagnose` 采集进程/extension host/SSH 日志，不要直接重装服务器环境。
- Isaac Sim 5.1 已接受 `PhysxTendonAxisRootAPI` 的 `gearing=0`、`forceCoefficient=0` root；CPU 64-step 最大 virtual-root 漂移 `8.453e-07 rad`。CUDA 接触、多环境和长训练下仍需验收 drift/solver 压力。
- 两个 mount 各 `1e-4 kg` / `1e-7 kg·m²`，base 已按刚体合成公式精确补偿，zero-pose aggregate mass/COM/inertia 静态守恒；但 virtual joint 发生非零旋转时，下游腿机构会产生原模型没有的微小共同转动。
- 本地与 GitHub 历史均已重写为新 root `72a2cd8`；旧历史与新历史不相关，已有协作者必须重新 clone 或显式 fetch 后 hard reset。恢复 bundle 暂存于 `/tmp/se3_rl_lab_pre_rewrite_87e145a.bundle`，可能随系统临时目录清理而消失，如需长期保留应移到持久备份位置。
- 当前 `pyproject.toml` 是完整锁 Isaac Sim 的方案，包含 `isaacsim[all,extscache]==5.1.0` 和 `starlette==0.49.1` override；真实 `uv sync --locked` 已通过，但方案仍较重。五个 IsaacLab package 使用 `../IsaacLab/source/...` sibling editable paths：跨机不依赖用户名，但要求两个仓库保持同一父目录且 IsaacLab 手工 checkout 到已验证 commit `b4c3210`。Git subdirectory wheel 已实测会丢失运行时所需的相邻 `config/extension.toml`，不可作为替代。
- 用户已确认接受 NVIDIA Omniverse EULA；当前验证使用单次命令级 `OMNI_KIT_ACCEPT_EULA=YES`，未写入 `.venv/lib/python3.11/site-packages/isaacsim/kit/EULA_ACCEPTED`。
- 直接 `uv run python -c "import se3_rl_lab"` 在未通过 AppLauncher/Kit bootstrap 的上下文仍可能报 `ModuleNotFoundError: No module named 'pxr'`；IsaacLab/IsaacSim 脚本应先通过 `AppLauncher` / `SimulationApp` 启动运行时。
- IsaacSim 启动时大量 `Failed to create change watch ... errno=28/No space left on device`，当前 `/proc/sys/fs/inotify/max_user_watches=65536`、`max_user_instances=128`，疑似 inotify watch 不足；目前未阻止 task 注册或 CPU/headless 环境创建。
- `OMNI_KIT_ACCEPT_EULA=YES uv run python -u scripts/zero_agent.py --task Template-Se3-Rl-Lab-v0 --num_envs 1 --headless` 在 CUDA 路径报 `omni.physx.tensors` CUDA OOM，随后 `Failed to get DOF velocities from backend`。
- SerialLeg task 已完成 USD、delayed 6D action、34D/40D observations、非跳跃 command/events/terminations/curriculum、官方 locomotion rewards 与 feed-forward MLP/PPO，并通过 CPU/compact-CUDA 最多 4 环境短 gate、4-env 最小 PPO update 和 checkpoint round-trip；长 rollout、目标规模 CUDA capacity/训练与 finetune 自定义奖励仍未完成，不要误报为整个 RL 迁移完成。
- 新 policy 明确为无 history 的 feed-forward MLP，旧 GRU checkpoint 与当前模型结构不兼容，不能直接 resume；若需要复用旧策略，只能另做权重迁移/蒸馏或重新训练，当前基础路径按重新训练处理。
- `velocity_height` 现为强制 8D term，缺失或 shape 错误会硬失败；当前 pitch/roll 与末 3D jump slots 恒为零。内部 `base_velocity=[vx,0,yaw]` 只是官方 reward 适配视图，不得暴露给 policy 或替换 legacy 8D checkpoint 合同。
- 启用官方 `bad_orientation`/`base_contact` termination 后，1-env CPU 64+64 零/小动作旧 smoke 会在长零动作阶段按设计终止；默认 gate 已收敛为 8+8，只验证 wiring 与短时物理稳定性。长时稳定性必须用训练策略控制的 rollout 验收，不能把短 gate 解释为长训练通过。
- legacy command observation scale `(2.0, 0.25, 5.0, 5.0, 5.0)` 与当前最终课程范围不完全匹配：`vx=±2.4 m/s` 会成为 actor `±4.8`，height 也未中心化。用户决定低优先级推迟到 finetune；在此之前为兼容旧 policy 接口保持不变，不应在单一训练路径中私自修改。
- 原始 closed-chain MJCF 直接经 IsaacSim importer 失败：`<equality><connect site1/site2>` 触发 `basic_string::_M_construct null not valid`；fixed/spatial tendon 变体触发 `Used null prim`。
- MJCF→URDF 的 joint axis/origin、body inertia、visual/collision transform、site-pair local pose、初始构型、左右镜像、virtual-root topology、窄限位和 aggregate inertia 均由强不变量覆盖。USD 已承载 fixed tendon coupled ranges，但仍不表达 spatial tendon、MJCF contact/solver 或 keyframe 的全部语义。
- loop joint armature `0.005` 来自 Kyber 已验证约定，不是 MJCF `<connect>` 的直接语义；solver/contact/多环境负载下仍需调参与长期验证。
- collision-only USD 的完整命名迁移已通过 PR #1 合并到 `main`；本地与远端均使用新命名。
- ground-contact smoke 的 `base_link=2976.983 N` 是零 actuator、2 秒自由塌落过程中的单帧撞地峰值，不是稳态支撑力；self-collision 在 contract、USD gate 和 smoke spawn 三层均已关闭。后续若需要力学验收，应记录峰值 step/速度并增加受控站立和稳态平均力口径。
- `robot_config.yaml` 变更会使现有 USD 的 config path/SHA gate 失败，这是有意的 stale-artifact 防护；修改 YAML 后必须重建 USD 并重跑静态/PhysX gate。YAML 已进入 wheel package data，但完整 sdist→wheel 仍受既存 `config/extension.toml` 缺包问题影响。
- 54 个 mesh collider 的物理 API 已迁移到实际 `Mesh` leaves（0 wrapper collider）；因 PhysX collider geometry 在 overlay 关闭时不作普通 render，viewer 创建 54 个 exact collision-mesh copies 和 2 个 wheel-cylinder copies。preview 不含原始高模 visual/贴图，headless gate 不代替最新 Cylinder 修正的 GUI 人工目视确认。asset-level ground smoke 已证明两轮与 mesh-backed `base_link` 能产生接触力，但未逐一激活 54 个 mesh shape。
- Isaac Sim 5.1 当前 `/physics/collisionApproximateCylinders=False`，wheel 使用高精度 custom cylinder geometry，而非 convex mesh approximation。单环境 CUDA ground smoke 已实测 `ContactSensor.net_forces_w` 在 `cuda:0` 对左右 wheel 返回非零力；但 NVIDIA 文档记载的更完整 GPU contact data/GPU feature 限制仍未被此 net-force gate 排除，多环境和 task 传感器路径仍需验证。
- ground-contact smoke 在无主动控制下会继续跌落，以 `base_link` mesh 冲击验收 mesh contact；它是冲击/数据路径 gate，不是站立稳定性测试。CPU/CUDA 峰值 residual 分别为 `9.380e-05/1.175e-04 m`，使用 `2e-04 m` contact 专用 gate；长 rollout/受控动作仍需调参。
- dynamic closed-chain A/B 已在 CPU/CUDA 上证明两条 external spherical constraints 将 5 N 周期外力下的 residual 维持在 `<=5.765e-06 m`，禁用后为 `0.08859–0.2584 m`。但该 gate 无重力、无地面且只有单环境/240 步；主动 actuator 动作、接触叠加、长 rollout 和多环境仍未验收。
- 交互 viewer 的 fixed base、leg position-offset/wheel velocity 命令和运动 preview 是资产目视验收辅助，不是 task action 合同。四连杆每侧可能存在过驱动/目标不一致；应小幅、逐个拖动 leg sliders，以实时 residual 为验收依据，超阈值时使用 `Reset standing pose`。
- Isaac importer/USDC crate 的二进制编码在连续重建间会有十余字节差异，即使磁盘语义 gate 完全相同；不要把逐次 binary SHA 稳定性当作合同。converter 已清除语义可见的随机 `/tmp` provenance，合同是 metadata/topology/physics/geometry/size gate。
- canonical URDF SHA 只覆盖 XML，不覆盖外部 collision STL bytes；当前 USD gate 锁 54 meshes、7102 faces、21306 points/indices、API/path 分类和 runtime smoke，但未锁每个 vertex coordinate 或逐 mesh local xform fingerprint。原地改 STL 顶点且保持 topology 理论上可能漏过，后续可添加聚合 mesh SHA/fingerprint。
- `uv build --package se3-rl-lab` 从 sdist 构建 wheel 时因既有 packaging 未把 `source/se3_rl_lab/config/extension.toml` 纳入 sdist 而失败；本轮直接 wheel 构建通过且确认包含新 URDF。该 sdist 缺项与 URDF 转换无关，后续发布前需单独修复。
- PhysX external loop constraints 比纯树形 articulation 更难求解；64-step CPU/free-space smoke 最大 residual `3.388e-07 m` 已通过，但地面冲击、主动控制、长 rollout 和多环境仍可能需要更小 dt、更多 solver iterations 或参数调整。
- `AGENTS.md` 和 `.claude/CLAUDE.md` 当前主要是 handoff 协议，还没有 SerialLeg/IsaacLab 迁移专属开发规则。

## Unknowns / Confirmations Needed

- UNKNOWN: 是否需要在本仓库 `.venv` 的 IsaacSim Kit 路径下持久记录 EULA 接受；当前仅对单次命令使用 `OMNI_KIT_ACCEPT_EULA=YES`。
- UNKNOWN: 后续是否保留完整 lock，还是回退到更轻量的 uv workspace 方案。
- UNKNOWN: 两条 external spherical constraints 与 fixed tendons 在地面接触、主动 delayed 6D 控制、长 rollout 和多环境并行下的稳定性；当前只证明 CPU/compact-CUDA 单环境短 rollout。

## Risk Guidelines

- 风险描述要具体。
- 不确定内容标为 `UNKNOWN`。
- 尽量写明解决未知项所需的来源。
