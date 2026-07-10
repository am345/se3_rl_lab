# Workspace Map

## Repository Structure

- `.`: 仓库根目录。
- `AGENT_HANDOFF.md`: 接力索引和恢复路线。
- `.agent-handoff/`: 持久接力状态文件。
- `pyproject.toml`: 根 uv project 配置、workspace、IsaacLab/IsaacSim 依赖来源和 dev 依赖。
- `uv.lock`: 当前 uv 锁文件。
- `README.md`: 中文项目说明，记录当前迁移状态、闭链资产生成/smoke 命令、uv 命令和 Agent 接力入口。
- `scripts/convert_serialleg_mjcf_to_urdf.py`: canonical MJCF→双 virtual tendon-root tree URDF + loop_joint 确定性转换和 byte/topology/mass/inertia gate。
- `scripts/convert_serialleg_urdf_to_usd.py`: Isaac importer→自包含 external-loop USD 生成、postprocess 和静态 gate。
- `scripts/smoke_serialleg_usd.py`: 默认 CPU/headless 的 bounded articulation/loop residual smoke。
- `scripts/view_serialleg_collisions.py`: 默认 GUI/CPU 的 standing collision viewer，自动启用 PhysX Colliders=All。
- `scripts/`: 其余官方模板脚本入口。
- `scripts/rsl_rl/`: RSL-RL train/play 脚本入口。
- `source/se3_rl_lab/`: IsaacLab external extension package。
- `source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg/`: SerialLeg MJCF/canonical URDF/small tracked collision-only USD/meshes 和 asset cfg。
- `source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/`: 当前 SerialLeg task；已通过 contract-driven `UsdFileCfg` 加载已验收 runtime USD。

## Main Entry Points

- `scripts/list_envs.py`: 列出已注册环境。
- `scripts/convert_serialleg_mjcf_to_urdf.py`: 第一阶段资产转换入口。
- `scripts/convert_serialleg_urdf_to_usd.py`: 第二阶段资产转换入口；需要 Isaac Sim runtime 和 EULA 环境变量。
- `scripts/smoke_serialleg_usd.py`: 第二阶段 CPU/PhysX gate。
- `scripts/view_serialleg_collisions.py`: collision-only USD 的交互目视检查入口；关闭 Isaac Sim 窗口退出。
- `scripts/zero_agent.py`: zero-action dummy agent 验证入口。
- `scripts/random_agent.py`: random-action dummy agent 验证入口。
- `scripts/rsl_rl/train.py`: RSL-RL 训练入口。
- `scripts/rsl_rl/play.py`: RSL-RL 回放入口。
- `source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/__init__.py`: 当前 gym task 注册入口，task id 为 `SerialLeg-Flat-ClosedChain-v0`。
- `source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/se3_rl_lab_env_cfg.py`: 当前 ManagerBasedRLEnvCfg，使用预生成 USD；单环境 CPU/compact-CUDA task gate 已通过。
- `source/se3_rl_lab/se3_rl_lab/tasks/manager_based/se3_rl_lab/agents/rsl_rl_ppo_cfg.py`: 当前 RSL-RL PPO 配置。

## Test Entry Points

- `uv lock --check`: 验证 `pyproject.toml` 与 `uv.lock` 一致。
- `uv sync --dry-run`: 验证完整 uv 同步计划；不会实际创建 `.venv`。
- `uv sync --locked`: 创建/同步本仓库 `.venv` 并严格使用 lock；要求 sibling `../IsaacLab` source checkout，已实际通过。
- `uv run python scripts/convert_serialleg_mjcf_to_urdf.py --check`: canonical URDF byte/topology/frame gate。
- `OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/convert_serialleg_urdf_to_usd.py --check`: generated USD schema/physics gate。
- `OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/smoke_serialleg_usd.py`: 默认 CPU/headless 64-step external-loop gate。
- `OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/view_serialleg_collisions.py --device cpu`: GUI standing collider viewer。
- `OMNI_KIT_ACCEPT_EULA=YES uv run python -u scripts/list_envs.py --keyword SerialLeg`: 真实同步后验证 task 注册；`-u` 避免 Kit close 前吞掉 pipe 中的 Python stdout。
- `OMNI_KIT_ACCEPT_EULA=YES uv run python scripts/smoke_serialleg_task.py --headless --device cpu`: 当前 11/10 runtime task 的 CPU reset/step gate；candidate URDF 未转 USD 前不用于验证 13/12 topology。

## Docs And Specs

- `README.md`: 中文项目启动说明和迁移路线。
- `AGENT_HANDOFF.md` 和 `.agent-handoff/*.md`: Agent 接力状态。
- `AGENT_SESSION_PROMPTS.md`: 新会话、继续任务、收尾和质量审查提示。
- `source/se3_rl_lab/docs/CHANGELOG.rst`: 官方模板 changelog 占位。

## Durable Project Context

- 当前 checkout 位于 `/home/am345/se3_rl_lab`，但 tracked 配置不得依赖该用户目录；portable layout 要求 `se3_rl_lab/` 与 `IsaacLab/` 是同一父目录下的 sibling。
- 用户目标是新开 IsaacLab 仓库，只迁移 SerialLeg 的 flat 训练；可选旧仓库 `../se3_rl` 仅作参考，不是运行时依赖。
- 官方模板生成选择为 external / manager-based single-agent / `rsl_rl`。
- 旧训练参考仓库可放在 sibling `../se3_rl`；Kyber 参考仓库仅为本机历史参考，不是依赖。
- SerialLeg asset 已搬迁，Kyber 风格 URDF→USD external-loop/fixed-tendon 资产管线已通过；delayed action 与 34D/40D observations 已迁移，commands/基础 rewards/terminations/curriculum/PPO 尚未完整迁移。
- 当前 task id 为 `SerialLeg-Flat-ClosedChain-v0`，已切到预生成 13-body/12-DOF USD；CPU/compact-CUDA 单环境 task gate 已通过。
- 自包含 runtime USD 是约 524 KiB 的 collision-only 普通 Git asset；canonical URDF 同样是 collision-only，当前 runtime/canonical 均为 13-link/12-joint 双 virtual-root + fixed-tendon topology。

## Project Conventions

- 默认用中文维护 handoff 文档。
- 当前用户偏好“更纯正的 uv 方案”，不希望依赖 `uv pip install -e` 作为常规工作流。
- 当前根 `pyproject.toml` 是较完整的 uv lock 方案，包含 `isaacsim[all,extscache]==5.1.0`、sibling relative IsaacLab editable sources、PyTorch cu128 index 和 `starlette==0.49.1` override。
- IsaacLab source checkout 必须为 `../IsaacLab`，建议 checkout `b4c321024792976150ca55fddb26fa34480d974e`；Git subdirectory wheel 会破坏 `config/extension.toml` runtime layout。
