# Risks, Blockers, And Unknowns

## 2026-07-14 WebSim submodule 风险

- V2 已将 ORT WASM `26.8→13.48 MB`、dist `37→24 MB`，并加入 HTTP/1.1/cache/prewarm；但 visual scene 仍为 78 files/15.3 MB，真实浏览器 cold/warm load 与 sustained FPS 仍为 `UNKNOWN`，不能只凭 Node canary 宣称加载问题完全解决。

- `am345/websim_se3` 为独立 private、`isFork=false`；V2 已发布到 `main@416b534`，父仓库必须锁定该 gitlink，不得回退到旧基线。
- 用户要求 submodule 文件不得出现参考仓库字样；每轮 closeout 必须运行全仓禁用词搜索，包含文档、源码、lockfile 和生成配置。
- 当前 `artifacts/recovery_checkpoints/history5_wscale10_std1_fresh_5k/exported/policy.onnx` 已补 `se3_rl_lab.websim.deployment.v1` 与最新视觉资产 fingerprint，可建立正式 session；其他旧 artifact 仍可能缺 metadata，不能假设全部兼容。
- height default/motor envelope/history/delay 已有跨端 golden，fallen/finite/residual 已有 0.5 s HTTP canary；但 control noise/encoder bias、较长 recovery 和图形浏览器交互仍未验收，暂不能称为生产 sim2sim 对齐。
- 对齐 body-frame/periodic-PD/implicitfast/floor-clearance 后，fallen 0.5 s rollout 的 soft closure residual 峰值为 `5.381 mm`，当前 canary 门槛为 `<6 mm`。若要收紧必须调整 equality/constraint 合同并同时验证行为稳定性，不能只改断言。
- 动态分包后初始 JS 已降至约 149.6 kB，但 MuJoCo/renderer chunks 仍约 523.1/513.2 kB，WASM 仍约 10.1/26.8 MB，视觉 asset manifest 另为 15.3 MB。Node 首次 visual canary 约 32.7 s，热缓存约 6.8 s；真实浏览器首次加载与帧率仍等待用户目视验收。
- 主仓库已有大量未提交 Recovery 改动与 `artifacts/`；本轮不得回滚、归因或一并提交。新增 `.gitmodules`/gitlink 与 WebSim 适配必须保持可单独审阅。
- 当前 scale45 页面使用独立 artifact run-root 和手工校正后的 deployment metadata，不修改源码默认 scale10；服务重启后必须继续显式传入 `artifacts/websim_runs`，否则模型发现会回到其他 run-root。该 artifact 对应旧 `model_4000.pt` 原生合同，不应用来给当前 `model_4500.pt` 强行套 scale45。
- 已证实的 free-joint angular velocity、continuous front-joint PD 和 integrator 三项 gap 均已修复，fallen reset 也加入 floor-aware clearance。剩余差异主要是训练 recovery 的 joint/root 随机分布、control noise/encoder bias 和长时 telemetry；修复后的网页仍不能单独替代 Isaac 策略质量验收。
- 两份闭链模型的核心 dynamics/contact/equality/tendon 数组已证明一致，因此“浏览器用了错误质量/惯量/摩擦资产”风险已降级；但 fallen reset 的 floor clearance、joint randomization 与 closure velocity 仍不等价，恢复场景的初态分布 gap 继续存在。

## 2026-07-14 wheel-scale-10/std-1 run 未完成风险

- run `2026-07-13_19-43-59_recovery_history5_wscale10_std1_fresh_5k` 的进程已退出，日志最后为 iteration 4760/5000，未生成 `model_4999.pt`；日志没有 Traceback/OOM/NaN，精确退出原因为 `UNKNOWN`。不得将 `model_4500.pt` 表述为完整 5k final checkpoint。
- `model_4500.pt` 已完成远端/本地 SHA 一致性与 72 tensors finite audit，可作为最后可用评估候选；但若 resume，optimizer、curriculum 和总 transition 连续性必须单独核对，不能默认等价于不间断 fresh 5k。
- model4500 已在服务器 RTX 4090 完成正式媒体录制：Isaac 中也明显侧倒/失稳，不能把 WebSim 抖动归为纯 sim2sim。当前 eval 只有 base velocity/yaw/height/loop telemetry，尚缺 pitch-rate、raw action、wheel target/velocity/torque saturation，4–5 Hz 根因定量仍需专用 probe。
- 同合同媒体 A/B 中，旧 `model_4000/scale45` 的 vx/yaw RMSE `0.25281/0.26064` 优于当前 `model_4500/scale10` 的 `0.28795/0.52612`，视觉也更稳；但两者来自不同 fresh run，训练 wheel scale 与 init std 同时变化。该结果只能证明当前策略在 Isaac 中已退化，不能把退化单独归因于 scale 10、std 1 或 WebSim runtime。

## 2026-07-13 wheel scale 10 / Recovery std 1 fresh 重训风险

- 用户要求 wheel action scale `45→10`，但 raw `wheel_action_rate` 与 `action_smoothness` 权重保持不变。对相同物理 wheel-target 变化，策略需要约 `4.5×` raw action 变化，二次 raw-action penalty 约放大到 `20.25×`；这可能降低高速 tracking 或改变最优平滑度，最终效果为 `UNKNOWN`，必须用相同命令 telemetry/MP4 验收。
- 当前没有有意义的 action clip（runner `clip_actions=null`，action cfg 上限 100），所以 scale 10 不会把 40 rad/s 变成不可达；策略可输出 raw mean 约 4。反面风险是 actor mean 仍可能离开常用 raw 范围，需继续监控历史 476/3195 污染窗口。
- Recovery `init_std=1.0` 相对旧正式 run 的 0.5 将腿 raw exploration 加倍；wheel 初始物理 target std 则因 scale 同时下降，约为 10 rad/s（旧合同约 22.5 rad/s）。4096-env gate 和新 run 初期 catastrophic 0，只证明启动健康，不证明长程数值稳定或最终 tracking。
- YAML action contract 变化要求重建 USD metadata；本轮已在 RTX 4090 重建并通过完整 `--check`，本机/远端 USD SHA 一致。后续再改 YAML 时仍必须重复该流程。

## 2026-07-13 Recovery 五帧历史实现后的剩余风险

- 目标 RTX 4090 的 4096-env capacity gate 已通过：98,304 steps、29,441 steps/s、峰值显存 4,818 MiB、catastrophic 0，无 OOM；正式 run 稳态约占 5.0 GiB。容量风险已降级，但并行启动其他大 GPU 任务仍可能争抢资源。
- 所有 34D/40D Recovery checkpoint 与新输入层结构不兼容，只能 fresh train；不得用 `strict=False`、补零或旧 optimizer state 伪装 resume。Flat task 仍为 34D/40D，不受此限制。
- 五帧历史是否能完全消除 4–5 Hz 极限环仍为 `UNKNOWN`；model1000 的 tracking RMSE 改善，用户目视确认相比 model500 抖动已改善，但 pitch-rate/action/wheel saturation 幅值尚未专用量化，不能提前宣称极限环已完全消失。
- 用户已目视判定 `model_500.pt` “还是抖得不行”，并确认 `model_1000.pt` 的抖动已改善，但 tracking 仍较差。model1000 的聚合 vx/yaw RMSE 虽下降，稳态 yaw-left/right/forward-turn 仍过冲约 `33%/56%/31%`，不能将“相对改善”写成“tracking 合格”。stand base-height 整段 RMS/p2p 也混入了姿态漂移/大幅运动，不应被当作否定视觉 jitter 改善的指标。后续必须同时验收 pitch-rate/接触/action/wheel saturation、recovery success 与分场景 steady-state tracking。
- runtime smoke 已锁 term-major、oldest→newest 与 reset 首帧复制；未来 JIT/ONNX、sim2sim/真机部署尚未做端到端验证，必须复用相同布局与填充合同。
- 本机 IsaacSim 仍打印既有 inotify `errno=28` change-watch 噪声，但 runtime smoke 与 PPO update 均成功；训练机含 `rerun-sdk`，同步后完整聚焦回归为 `26 passed`。

## 2026-07-12 recovery height-default fresh 5k 结果与抖动风险

- 用户已把 reward 数值从主嫌疑降级；现有证据支持这一调整：`-0.02/-0.05` 视频的站立视觉主峰均为 `4.027 Hz`，原始 wheel action-rate 只约降 9%，没有换模态。继续只加大该权重很可能继续牺牲恢复动作而不消除闭环振荡。
- “旧 se3_rl 同奖励不抖”只对 normalized GRU/64-step/full-budget 合同成立，旧仓库 MLP 仍是未训练占位；但旧 GRU 现已在当前 PhysX 单环境平滑站立，所以它不仅是 MuJoCo 视频证据。当前 unnormalized MLP/24-step 与参考在 memory、normalization、rollout/PPO 和 `5.33×` total-transition 预算上同时变化，不能把全部差异只归给 GRU 架构。
- 当前 actor 与参考一样不直接观察 base linear velocity、wheel contact 或 base height。同一 reference GRU 保留 hidden state 时 pitch-rate RMS `0.000804 rad/s`，每拍清空 hidden state 后出现 `4.8 Hz`、RMS `0.205 rad/s`；这直接证明历史状态在当前 plant 上抑制该模态。当前 MLP 的对应 RMS 为 `1.546 rad/s`，说明 normalization/训练预算等还会放大幅值。
- PhysX external spherical loop/fixed tendon/contact 不再是主因：reference GRU 在当前 PhysX 平滑，而当前 MLP 在相同 plant 上复现 `4.5 Hz`。backend 差异不能被宣称完全为零，但在 temporal policy 重新训练失败前不应优先调 friction/solver/constraint。
- 三档 fresh sweep 因用户释放服务器而停止；`-0.02/-0.05` 完整，`-0.1` 仅到 iteration 667 且只有 model500。监督器最终 `halted`/return code `-9` 来自本 Agent 有意 SIGKILL 进程组，不是训练异常；不得把 partial run 当作完整 5k 或据此选择最优权重。
- baseline、两档完整 run 与 `-0.1` partial 的全部现有 checkpoint、params、events、git diff 和关键日志已保存到本地 `artifacts/recovery_checkpoints/wheel_action_rate_sweep/`；manifest 57/57 SHA256 通过。远端 supervisor/train 与 GPU compute process 均为 0，实例可释放。
- 第一档 `-0.02` 已健康完成 5000 iterations，排除本档数值稳定性风险；但训练 reward/std 不能证明抖动改善，仍必须与 `-0.05/-0.1` 用相同 jitter/recovery probe 比较。
- 第二档 `-0.05` 已健康完成 5000 iterations 与最终 checkpoint finite audit；1780/1910/2405/3310 附近的 `catastrophic=0.0002` 孤点均自行回零，未扩散。第三档 `-0.1` 后续须从 seed 42 fresh 重跑并跨全部 cache stages、历史 3193–3204 窗口与最终 4999；resume `m010_partial/model_500.pt` 只适合技术诊断，不能恢复不间断单变量实验合同。
- `se3rl eval` 由当前源码构造环境，因此两段 Reward Manager 都显示默认 wheel rate `-0.02`；reward 不参与确定性 policy 动作或物理，画面仍分别来自各自 checkpoint。不要把 eval reward 数值用于两档比较；使用 telemetry/jitter probe 比较行为。
- model2000 旧 noisy MP4 不应直接解读为无噪部署行为；eval worker 已修复并重录无噪版本。但无噪确定性 actor 的稳态 4–5 Hz 极限环仍存在，关闭 eval noise 不能视作视觉或控制抖动已解决。
- nominal-vs-randomized A/B 已排除 startup material/base mass/COM/actuator-gain randomization 为主因：nominal model4999 仍复现 `4.67 Hz`、pitch-rate std `1.56 rad/s`。eval worker 保留 randomization 仍影响单次指标，但不再是根因未知项。
- 平均动作 hold 与分通道 A/B 已确认轮速度 policy 是主自激通道：恒定动作下振荡先快速衰减再因无反馈倾倒；固定腿目标后 wheel/root-z/pitch 仍同频 `3.67 Hz`，固定轮动作后初始抖动显著下降但失去平衡。腿动作会耦合放大 z/contact，不应误写为唯一根因。
- model4999 在站立时频繁请求超出轮电机 no-load speed 的 target，并使轮 torque 近半时间贴近上限；任何修复若只增强 action smoothness 而不约束物理 target/饱和使用，可能继续学出低频但饱和的动态平衡。
- 当前按用户要求只加强无门控 wheel action-rate；它可能降低 4–5 Hz 抖动，也可能在倒地恢复阶段抑制必要的快速轮动作。三档仅通过 1-update gate，必须用 fresh 长训练同时验收 recovery success 与稳态 jitter，不能从初始 reward 大小推断最优权重。
- 当前 feed-forward actor 不观测 base linear velocity、wheel contact force 或 base height，且 actor observation normalization 关闭；reference normalized GRU 与 hidden-reset 消融已在同一 IsaacLab plant 完成。temporal memory 是已确认关键变量，但 normalization、64-step rollout、reference PPO 与训练预算的独立贡献仍为 `UNKNOWN`。
- 用户已选择先试 Kyber-style 5-frame MLP history，但 5 帧并不等价于 GRU：50 Hz 下只有 80 ms 时间戳跨度，能覆盖 4.5 Hz 模态约 130° 相位，但是否足以在 recovery、移动和更长时延下稳定控制仍为 `UNKNOWN`。首次训练应保持其他合同不变，失败后再增大 history 或回到 GRU，不能预先宣称已解决。
- 参考语义不是简单给当前 `ActorCfg/CriticCfg` 各设 `history_length=5`：Kyber 把 command 保持单帧，只堆叠 proprioception/privileged terms。当前已按该语义拆为 actor 138D、critic 168D；若未来直接堆完整 34D/40D，会退化为 170D/200D 并向网络重复过期 command。
- IsaacLab history 是逐 term、oldest→newest、term-major flatten；reset 后第一次 append 会把当前观测复制到全部 5 个槽。训练、eval/play、JIT/ONNX metadata 和未来 sim2sim 若有任何顺序、首帧填充或 command 分组差异，checkpoint 会在形状正确时仍发生静默语义错配，必须用数值布局测试锁定。
- 新 observation groups 在 4096 env×24-step 下相对现有 actor/critic tensor 至少增加约 84 MiB raw rollout observation storage，首层另增加 118,784 个网络参数；实际峰值还含 mini-batch/optimizer/PhysX。并行负载下已有 CUDA OOM 风险，4096-env gate 必须重新测峰值显存。
- 138D/168D 输入与所有现有 34D/40D checkpoint 结构不兼容；只能 fresh train。不得用 `strict=False` 或手工补零把旧 checkpoint 伪装为有效 resume。

- 新 run `recovery_height_default_fresh_5k` 已健康完成 5000 iterations，最终 model4999 catastrophic 0；这证明本轮没有复发 3195 级联污染，但不代表控制质量平滑。model4999 forward action/target delta RMS 比 model2000 更高，真实抖动仍未解决。
- production eval camera 当前跟随 root x/y/z；root-z 的毫米级 4–5 Hz 振荡会带动整个背景，显著放大观感。只锁 camera z 的诊断将背景垂直逐帧位移约降 81%，但它只修录像，不修真实控制。
- 稳态 A/B 只观测到左右轮接地；no-delay、Kd=6、zero-restitution 均未消除 root-z/pitch 极限环。不要再把复杂 collision mesh 误触地、随机 delay 或 restitution 表述为已确认根因。
- 本轮重要训练产物已在释放实例前完成独立本地备份和 SHA 校验；后续新长训练仍应沿用同样的退出前备份流程。

- 旧 `recovery_motor_tn_fresh_5k` 已停止，不再作为有效训练结果；它证明原 `init_std=1.0/entropy=0.01/lr=1e-3/KL=0.01` 组合会伴随 std 增长和 reward 爆点。
- `recovery_ref_std_fresh_5k` 已失败：iteration 3195 起物理极端状态产生巨额有限 reward，3204 后 catastrophic 快速扩散，最终 iteration 3606 后退出。std 在首爆时仅 0.36，不能把首因归为 std。
- 当前 catastrophic termination 阈值只决定 reset，不会 mask/cap 同一终止帧 reward；直接污染已定位为四个 active leg joints 的 `joint_acc_l2`，但用户明确要求先确认上游物理触发，不实施 cap/mask 等兜底。
- 新配置只对齐四项已确认的随机策略参数，刻意保留当前 MLP、24-step rollout、clip 0.2、5 epochs；它不是参考 GRU/64-step PPO 的整套复制，后续效果比较需保留这个边界。
- 源码中的 Recovery yaw reward 已改为 `sigma_cmd_scale=0.4/ratio_blend=0.2`，但失败 run 全程使用旧纯指数实现；本次崩溃与新 yaw reward 无因果关系。新语义需在安全修复后的新进程中验证。
- 首个严重物理事件已复现并定位：actor mean 已先在 `lf0` 达 `+17.90`，随后 `rf0` 从约 `-2.4` 外飘至 `-17.74`，生成 `rf0=-4.378 rad` 目标，继而使右闭链/rf1 接触失稳并由 `r_drive_bar_Joint` 首爆。未限制的 actor mean/action-to-target 路径是已确认的上游污染源；`last_actions` 参与放大，但最初触发早于 32-step 窗口，尚未证明其为唯一首因。
- reward cap/mask 只能阻断 PPO 二次污染，不能消除上述 actor/物理触发；termination/reset 修改也不是当前证据指向的首因。后续方案必须区分根因修复与可选的训练安全隔离。

## 2026-07-12 电机模型迁移后风险

- 新显式 actuator 已通过 4096-env gate 与完整 5k，catastrophic/NaN 风险跨历史窗口验收通过；剩余主要风险是策略以高频动作维持动态平衡，而非数值发散。
- 旧 `model_1999.pt`/loco finetune checkpoint 来自 implicit/static-limit dynamics。网络结构仍兼容，但其行为不能代表新电机模型的训练结果，正式比较应从头训练。
- 轮曲线在 `|speed| <= 32.93 rad/s` 仍允许 `3.71 N·m`，因此缺失曲线不是低速 tracking error 的充分解释；腿 DC motor、控制动态、reward/command 等仍可能影响结果。

## 2026-07-12 10:30 活跃风险

- wheel clearance 是应保留的参考 reset 行为，但已证实不是本次 NaN 根因；旧 handoff 中的因果表述已被本节取代。
- 400 轮确定性 repro 与最终 5k 均已完成；旧“仍需跨过 2000/5000”状态已关闭。
- 当前 PPO 与参考 recovery PPO 不同（用户此前限定只迁移 reward/reset/termination）；本轮未修改 PPO。训练质量需与崩溃修复分开评估。

## 2026-07-12 活跃风险

- 新 fresh run 已完成到 4999，无 NaN/catastrophic；更高 cache ratio 与长期数值稳定性已验收，控制平滑度仍单独待修。
- 当前 IsaacLab 修复采用“保守 full-angle bbox + post-joint wheel lift”。若更高随机化阶段仍异常，应实现逐 collision-shape 最低点测量，不应添加 settle 或 `nan_to_num`。
- dataset 从 iteration 1500 才混入，仍需独立验收该阶段。

## Current Blockers

- 双 virtual-root URDF、schema-v3 contract、fixed-tendon USD 与 task runtime 已统一，无本轮 CPU/runtime blocker。
- `SerialLeg-Flat-ClosedChain-v0` 的 CPU 与 compact-buffer CUDA 单环境 `gym.make/reset/step` gate 均已通过，无已知 task 逻辑 blocker。
- 默认 CUDA PhysX capacity 曾在同卡并行 Kyber 4096-env 训练占用 `5300 MiB` 时因 `mGpuContactPairsDev` 预分配 `671088640 bytes` 于 rollout 前 OOM；GPU 空闲后已实测 SerialLeg 4096-env 默认 capacity 完成 1 PPO update。并行负载下仍有 OOM 风险，运行中峰值显存与长训练余量尚未定标。

## Current Risks

- Rerun 固定为 `0.20.3`：新版 `0.31.4` 要求 NumPy 2，与 IsaacLab 0.54.4 的 NumPy `<2` 冲突。升级前必须重新验证 uv dependency split 和 `.rrd` API，不能单独抬版本。
- 当前 `flat-basic` eval 使用 1 env/固定 seed 47，默认六个 scenario；适合 checkpoint 回归和 finetune A/B baseline，但不能替代多 seed 统计。worker 已保证 timeout/command resampling 位于完整 suite 之后，并在每个场景首步前刷新 command observation。eval 是显式 CLI worker，不会训练期自动并发，以避免与 4096-env 训练争抢 GPU。
- MP4 依赖评估时创建 54 mesh + 2 cylinder render-only copies；资产 collision topology 改变会硬失败并要求同步更新 gate。副本不参与物理，runtime USD 未改。评估副本必须保持在独立 world-space preview 树并从 body tensor 逐步同步；不要重新挂到 replicated articulation body prim 下，否则录制画面可能与物理状态脱节。
- eval debug markers 在 Fabric 下会触发 point-instancer prototype mismatch 并错位，因此 worker 明确 `use_fabric=False`；该设置只影响 1-env 录制，不得复制到 4096-env 训练配置。

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
- 完整dataset/passive reset已通过4096-env cache gate和100-iteration PPO soak，旧NaN窗口未复现；但正式2k尚未跨过iteration 1500后的长期cache混合阶段。训练完成前仍需监控更高joint randomization/cache比例下的闭链接触稳定性。
- Recovery policy 现为五帧 history 的 feed-forward MLP；旧 34D MLP/GRU checkpoint 均与 138D actor 输入不兼容，不能直接 resume。Flat policy 仍是无 history 的 34D MLP。
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
