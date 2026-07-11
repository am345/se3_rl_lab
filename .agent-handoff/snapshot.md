# Handoff Snapshot

## Current State

- Last updated: 2026-07-11
- Last agent: Codex
- Workspace root: 本机 `D:\RoboMaster\se3_rl_lab`；当 `hostname` 为 `WIN-46S653M0DI0` 时，默认运行目标为 SSH alias `se3_rl_lab_gpufree`，远端项目根为 `/root/gpufree-data/se3-workspace/se3_rl_lab`
- Current objective: 迁移 SerialLeg flat 的非跳跃基础训练链路，先用 IsaacLab 官方 locomotion rewards 验证 Isaac Sim 行为，再在 finetune 阶段适配自定义奖励。
- Current status: delayed 6D action、34D/40D observation、非跳跃 8D `velocity_height`、基础 events/domain randomization、terminations/curriculum、IsaacLab 官方 locomotion rewards 与 feed-forward MLP/PPO 已实现；CPU/compact-CUDA 单/4 环境短 rollout、4 环境最小 PPO update 和 checkpoint save/load round-trip 均通过。旧 flat 自定义奖励仍推迟到 finetune，jump command 关闭。依赖配置使用 portable sibling paths `../IsaacLab/source/...`；项目分支/SHA/clean 状态以实时 `git status -sb` / `git log -1` 为准，远端 IsaacLab 固定为 `b4c3210`。
- Delayed-action contract: action order 由 `SERIALLEG_CONTRACT.policy_joint_order` 派生；腿为 position target、scale `0.25 rad`，轮为 velocity target、scale `45 rad/s`。每侧 action 使用 `[front joint, active tendon coordinate]`，右侧 tendon coefficients 已按 policy order 重排为 `(-1,+1)`；active target clamp 为 `[lower-0.20, upper]`。
- Delay/reset contract: 默认 `4–6 ms` 在 `physics_dt=0.005 s` 下逐环境量化为 1 physics step；FIFO 在 physics step 更新，partial reset 只清目标 env 的 raw/delayed/FIFO 并重采样 delay。
- Observation contract: actor 精确 34D、critic 为 actor 34D + privileged 6D = 40D；显式只索引 4 policy leg + 2 wheel joints，passive 与 virtual-root joints 不进入 policy observation。布局和 scale 位于 `mdp/observations.py`。
- Command contract: `velocity_height` 严格为 `[vx, yaw_rate, pitch, roll, height, jump, jump_height, jump_phase]` 8D；term 缺失或 shape 错误直接失败。当前 pitch/roll 和末 3D jump slots 恒为零，height 在 `[0.20,0.32] m` 采样；派生 `base_velocity=[vx,0,yaw_rate]` 仅供 IsaacLab 官方 tracking rewards 使用。速度课程为 policy iteration `0/400/800/1200/1600/2000`，最终范围 `vx=±2.4 m/s`、yaw `±12 rad/s`，并始终施加差速轮速预算。
- Reward migration decision: 基础验收阶段只配置 IsaacLab 官方 manager-based locomotion rewards，不迁移旧 flat 自定义奖励；command-driven 高度、分段/联合跟踪、轮腿专属 penalty/gating 等统一推迟到 finetune。
- Command normalization decision: 当前继续保留旧 observation scale `(2.0, 0.25, 5.0, 5.0, 5.0)` 以维持 legacy policy/checkpoint 接口；是否按最终 command range 做中心化归一化已推迟到 finetune 阶段，列为低优先级，不阻塞当前迁移。
- Policy contract: 明确使用非循环 `RslRlMLPModelCfg`；actor/critic hidden dims 均为 `[512,256,128]`、ELU，actor 读取 34D 且不做 normalization，critic 读取 40D 并使用 empirical normalization；actor scalar Gaussian 初始 std `1.0`。不堆叠 history、不使用 GRU/LSTM/BPTT；每环境 rollout 为 64 steps，与 curriculum policy-iteration 语义对齐。
- Environment/reward contract: startup 随机化 material、base mass/COM、policy actuator gains；reset 随机 xy/yaw 并恢复 standing joints；5–6 s interval push 由非跳跃课程渐增。termination 为官方 `time_out`、`bad_orientation`、`illegal_contact(base_link)`。9 个 reward 全部直接引用 IsaacLab 官方函数：linear/yaw tracking、vertical/roll-pitch velocity、policy torque/acceleration、action rate、flat orientation、base undesired contact；没有配置旧自定义 reward。
- Validation: 远端 Ruff/format/diff check 通过，observation pytest `4 passed`；manager/command/reward/termination/curriculum identity、课程终态和固定状态 tracking reward 检查通过。CPU 1/4-env 8+8 与 compact-CUDA 1/4-env 4+4 短 rollout 均退出 0，actor/critic 保持 `(34)/(40)`，passive effort 为 0。4-env CPU simulation 完成 256 steps/1 PPO update，生成 `model_0.pt`；恢复命令成功加载该 checkpoint 并继续完成 1 update。
- Runtime peaks: CPU 1-env zero/controlled loop `3.857e-04/2.114e-04 m`，CPU 4-env `4.624e-04/2.397e-04 m`；compact-CUDA 1-env `4.181e-04/2.361e-04 m`，4-env `4.056e-04/2.548e-04 m`，均低于 task `1e-3 m` gate。
- Active files: `README.md`、`scripts/{smoke_serialleg_task,test_serialleg_observations}.py`、`source/.../se3_rl_lab_env_cfg.py`、`source/.../agents/rsl_rl_ppo_cfg.py`、`source/.../mdp/{__init__,commands,curriculums,observations}.py` 与 `.agent-handoff/{snapshot,workspace,decisions,work-log,validation,backlog,risks}.md`。资产/YAML/USD 未改。
- Blockers: 无当前环境 blocker。GPUFree 已分配单张 RTX 4090 24GB，PyTorch CUDA 与 Isaac Sim task smoke 通过；目标多环境训练的 PhysX capacity 仍需按 backlog 定标。
- Immediate next actions:
  - 用有策略控制的短训练/长 rollout 验收 termination、push curriculum 和 fixed-tendon/external-loop 稳定性；不要用长零动作 rollout 代替。
  - GPU 空闲后做默认 capacity、多环境与长 rollout 定标。
- Open questions:
  - UNKNOWN: fixed tendon + external loops 在主动 delayed control、CUDA 大规模多环境和长训练下的稳定性；当前只完成 CPU/compact-CUDA 最多 4 环境短 gate。
  - LOW: finetune 时是否将 command observation 改为按最终范围归一化，并制定旧 checkpoint 的适配/重训策略。

## Recovery Summary

- fixed-tendon USD/YAML 未改，本轮不会触发 USD SHA stale gate。
- IsaacLab 必须作为 sibling source checkout 存在于 `../IsaacLab`，并 checkout 已验证 commit `b4c321024792976150ca55fddb26fa34480d974e`；不要改回用户目录绝对路径，也不要用 Git subdirectory wheel 代替。
- 在 `WIN-46S653M0DI0` 不要重新安装本地 Isaac Sim：通过 `ssh se3_rl_lab_gpufree` 使用已配置远端环境。SSH endpoint、私钥和凭据只保存在本机 `~/.ssh/config`/密钥文件中，不写入仓库。
- 服务器重启或重新分配后先跑 `nvidia-smi`；若 PCI 可见但 `/dev/nvidia*` 缺失或 `torch.cuda.is_available()` 为 False，需要在 GPUFree 控制台重新分配 GPU，而不是重装 Python 包。
- 基础环境语义、官方 reward 与 feed-forward MLP/PPO 已不再是模板占位；后续从目标规模训练、策略控制长 rollout 与 capacity gate 继续，自定义奖励留到 finetune。
