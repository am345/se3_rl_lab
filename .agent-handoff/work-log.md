# Current Work Log

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
