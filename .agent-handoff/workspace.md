# Workspace Map

## Machine-Specific Execution Target: `WIN-46S653M0DI0`

- 先用 `hostname` 或 PowerShell `[System.Environment]::MachineName` 识别电脑。结果为 `WIN-46S653M0DI0` 时，默认在 GPUFree 服务器运行依赖安装、Isaac Sim、CUDA smoke 和训练；本机仓库用于编辑、Codex 和 Git 检查。
- 本机仓库：`D:\RoboMaster\se3_rl_lab`。默认 SSH alias：`se3_rl_lab_gpufree`。实际 `HostName`、`Port`、用户和 key path 由本机 `%USERPROFILE%\.ssh\config` 管理，仓库文档不得复制密码、私钥或平台 TURN 凭据。
- 远端 workspace：`/root/gpufree-data/se3-workspace/`；项目为 `se3_rl_lab/`，IsaacLab sibling 为 `IsaacLab/`。项目分支/SHA/clean 状态以实时 Git 查询为准；IsaacLab 固定并验证于 `b4c321024792976150ca55fddb26fa34480d974e`。
- 远端 Python 环境：`/root/gpufree-data/se3-workspace/se3_rl_lab/.venv`；uv cache：`/root/gpufree-data/.cache/uv`。已验证 Isaac Sim `5.1.0.0`、IsaacLab package `0.54.4`/project `2.3.2`、Python 3.11、PyTorch `2.7.0+cu128`、torchvision `0.22.0+cu128`、RSL-RL `5.0.1`。
- 当前 GPU：RTX 4090 24GB，driver `580.126.09`，PyTorch CUDA 12.8。开始任务前用 `ssh se3_rl_lab_gpufree nvidia-smi` 做最小检查；平台重启/重新分配可能使 GPU 设备节点暂时消失。
- 数据盘挂载点 `/root/gpufree-data` 当前约 49GB；`.venv` 与 uv cache 都较大。不要把仓库或环境放回约 30GB 的系统盘。普通重启会保留数据盘；释放实例/平台回收的持久性应按控制台规则确认，重要 checkpoints 需要另行备份。

### SSH Contract And Connection Tips

- 使用 `ssh se3_rl_lab_gpufree` 或 VS Code Remote-SSH 的同名主机；已配置 key auth，不应每次输入密码。
- 有效转发合同：`RemoteForward 7890 127.0.0.1:7897` 把本机代理送到远端 `127.0.0.1:7890`；`LocalForward 3000 127.0.0.1:3000` 把 GPUFree Selkies 桌面送到本机 `http://127.0.0.1:3000`。
- 已配置 keepalive、compression 和 `ExitOnForwardFailure no`。多条 VS Code/SSH 连接可能争用远端 7890 或本机 3000；看到“端口被占用”通常表示已有连接正在持有转发。优先复用/关闭旧连接，不要删除代理配置或重建 key。
- 本机 Clash HTTP/SOCKS mixed proxy 实际监听 `127.0.0.1:7897`；远端 shell 的 `HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY` 指向 `127.0.0.1:7890`。只有至少一条带 `RemoteForward` 的 SSH 连接存活时，远端 GitHub 代理才可用。
- GitHub clone/fetch 走远端 `127.0.0.1:7890`；PyPI、NVIDIA PyPI 与 PyTorch CDN 大包应直连。运行 `uv sync` 时把 `download-r2.pytorch.org`、`.pytorch.org`、`.nvidia.com`、`pypi.org`、`.pythonhosted.org` 加入 `NO_PROXY/no_proxy`，避免大文件绕回本机代理导致数小时慢速下载。
- VS Code 卡顿时只打开远端项目目录，不要打开 `/root` 或 `/root/gpufree-data`；不要让 Remote-SSH 索引 `.venv`/uv cache。当前本机设置使用 `remote.SSH.useExecServer=false`，并强制 `openai.chatgpt` 与 `GitHub.copilot-chat` 作为本地 UI extension，避免在服务器重复安装约数百 MB 的 Codex/ChatGPT extension。

### GUI And Headless Usage

- GPUFree 镜像已自带 `Xorg :20`、XFCE、Selkies WebRTC 与 nginx `:3000`；远端 OpenGL renderer 已验证为 RTX 4090。SSH 连通后在本机浏览器打开 `http://127.0.0.1:3000`。
- GUI 脚本设置 `DISPLAY=:20` 并且不要传 `--headless`，例如：`DISPLAY=:20 OMNI_KIT_ACCEPT_EULA=YES .venv/bin/python scripts/random_agent.py --task SerialLeg-Flat-ClosedChain-v0 --num_envs 1 --device cuda:0`。
- 训练默认继续使用 headless，例如在训练命令中显式传 `--headless`；GUI 只用于少环境调试、碰撞目视和回放。Isaac Sim 自带公网 livestream 需要额外 TCP/UDP 端口，本机方案优先复用 GPUFree 已配置 TURN 的 Selkies 桌面。
- 远程桌面和 Isaac GUI 进程在服务器重启后不会保留；SSH 转发会在下一次连接时按 config 恢复，GUI 脚本需重新启动。

### Quick Verification

- SSH/代理：`ssh se3_rl_lab_gpufree "curl -I --max-time 10 https://github.com"`。
- GPU：`ssh se3_rl_lab_gpufree nvidia-smi`。
- 环境：`ssh se3_rl_lab_gpufree "cd /root/gpufree-data/se3-workspace/se3_rl_lab && .venv/bin/python -c 'import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))'"`。
- 完整 task smoke：`OMNI_KIT_ACCEPT_EULA=YES .venv/bin/python scripts/smoke_serialleg_task.py --headless --device cuda:0 --compact-gpu-buffers`。

## Suggested Skills For The Next Agent

- `diagnose`: VS Code/SSH、代理、下载速度、GPU 设备或 Isaac Sim 性能出现回归时使用，要求先复现和采集证据再改配置。
- `handoff`: 完成新的服务器配置、训练里程碑或重要故障处理后，继续压缩更新本多文档 handoff；始终去除密码、私钥、token 和 TURN 凭据。

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
- SerialLeg asset 已搬迁，Kyber 风格 URDF→USD external-loop/fixed-tendon 资产管线已通过；delayed action、34D/40D observations、非跳跃 commands/events/terminations/curriculum、IsaacLab 官方基础 rewards 与 feed-forward MLP/PPO 已迁移，4-env 最小训练和 checkpoint round-trip 已通过。
- 当前 task id 为 `SerialLeg-Flat-ClosedChain-v0`，已切到预生成 13-body/12-DOF USD；CPU/compact-CUDA 单环境 task gate 已通过。
- 自包含 runtime USD 是约 524 KiB 的 collision-only 普通 Git asset；canonical URDF 同样是 collision-only，当前 runtime/canonical 均为 13-link/12-joint 双 virtual-root + fixed-tendon topology。

## Project Conventions

- 默认用中文维护 handoff 文档。
- 当前用户偏好“更纯正的 uv 方案”，不希望依赖 `uv pip install -e` 作为常规工作流。
- 当前根 `pyproject.toml` 是较完整的 uv lock 方案，包含 `isaacsim[all,extscache]==5.1.0`、sibling relative IsaacLab editable sources、PyTorch cu128 index 和 `starlette==0.49.1` override。
- IsaacLab source checkout 必须为 `../IsaacLab`，建议 checkout `b4c321024792976150ca55fddb26fa34480d974e`；Git subdirectory wheel 会破坏 `config/extension.toml` runtime layout。
