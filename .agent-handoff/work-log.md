# Current Work Log

## 2026-07-14 WebSim 产品体验 V2

- 加载链路：ORT 改用纯 WASM 入口，WASM `26.8→13.48 MB`、前端 dist `37→24 MB`；MuJoCo idle 预热，asset/ONNX 分阶段字节进度，server HTTP/1.1 + ETag/cache + 流式文件响应。
- 交互：WASD/方向键、Space/R/F、运动 presets、0.25–2×、跟随/侧面/正面视角、鼠标旋转/缩放、运行中 reset 和 6D action monitor。
- 视觉：重构为以 viewport 为中心的暗色工业控制台，增加 session/command/runtime panels、loading overlay、toolbar、telemetry strip 和 responsive layout；无外部字体请求。
- 验证：submodule backend 8 tests、frontend 8 unit、typecheck/build、真实 scale45 HTTP 25-cycle canary、HTTP cache header 与 diff check 通过。功能 `3303df8` 与发布记录 `416b534` 已推送到 submodule `main`；父仓库同步 gitlink 后转回训练端问题。

## 2026-07-14 WebSim sim2sim runtime 修复

- `websim_se3/frontend/src/runtime/observation.ts` 将 MuJoCo free-joint `qvel[3:6]` 直接作为 body angular velocity缩放，只对世界重力做 quaternion inverse rotation；非单位姿态测试锁定该 frame 语义。
- `control.ts` 仅对连续 LF0/RF0 使用 shortest-angle PD error；共享 JSON fixture 同时由 native Python 与 browser Vitest 验证跨 ±π 和多圈输入。
- `scripts/build_websim_scene.py` 与生成 `scene.xml` 显式锁 `implicitfast`、Newton、100 iterations。fallen reset 依据 compiled mesh/primitive collision geom 最低点整体上抬到 10 mm，HTTP canary 直接断言 clearance。
- scale10 与 scale45 ONNX metadata 已刷新到新 asset fingerprint `2e07880b...d5dbb`；scale45 保持 wheel scale 45，SHA256 更新为 `011b41f2...e2ce6`。真实 HTTP 25 cycles/0.5 s 全 finite，最大 closure residual `5.381 mm < 6 mm`；服务仍位于 `http://127.0.0.1:2705/websim/`。
- submodule 功能/发布记录已推送到 `origin/codex/bootstrap-websim`（`be0fb2e`、`80a1153`）；父仓库 Recovery history + WebSim 集成提交 `d9afe2a` 已推送到 `origin/codex/height-conditioned-recovery`。`artifacts/` 未纳入提交。
- submodule `main` 已 fast-forward 到 `80a1153`，随后以接力记录提交更新到 `be736cf` 并推送；父仓库 gitlink 同步到该 main HEAD。
- 父仓库 `main` 已由 `25251c1` fast-forward 到 `994f1c7` 并推送，无冲突；包含完整 Recovery history、WebSim 集成与 submodule main gitlink。

## 2026-07-14 对照 se3_rl 正常 sim2sim

- 只读检查 sibling `/home/am345/se3_rl` 的 `se3_sim2sim`、`se3_shared`、Recovery 配置与默认 closed-chain MJCF。该项目训练使用 MJLab/MuJoCo-Warp，sim2sim 使用 native MuJoCo，并由 `se3_shared` 直接共享 action/observation/motor/timing；Recovery wheel scale 固定 45。
- 默认正常 sim2sim 使用 `serialleg_closed_chain_v3_train_obb_trim.xml`。与当前 browser `scene.xml` 用 native MuJoCo 编译后比较：两边 `17/16` q/v、12 bodies、80 geoms、2 equality、4 tendons；body mass/inertia/ipos/iquat、joint pos/axis、dof armature/damping、geom friction/solref/solimp、equality solref/solimp 和 tendon range 全部 max diff 0。浏览器另有 6 个 direct-torque actuators和减面 visual，但 collision/dynamics 数组一致。
- 明确 observation bug：MuJoCo free-joint `qvel[3:6]` 是 body-frame angular velocity，正常 sim2sim 直接作为 `base_ang_vel_body`；当前 WebSim `proprioception()` 又按 root quaternion 执行 `rotateInverse`，大姿态/fallen 时会把角速度轴和值错误旋转，且错误进入五帧 history。
- 明确控制 bug：正常 sim2sim 对连续 LF0/RF0 使用 `policy_leg_position_error_np()` shortest-angle periodic error；WebSim `MixedController.torques()` 直接做 `target-position`。front joint 跨 ±π 或多圈时，浏览器可能沿错误长路径输出饱和腿力矩。
- 明确 solver 差异：正常 sim2sim 构建后强制 timestep 0.005、integrator `implicitfast`、Newton、100 iterations；browser generator 只改 timestep，scene 实际仍为 Euler/ Newton/100。质量与接触数组一致时，该 integrator 差异应优先 A/B，不应先调摩擦。
- reset 仍不等价：WebSim fallen 只旋转 root、固定 z=0.36、保留 standing joints；正常 sim2sim/训练有闭链 position/velocity closure、最低碰撞点 floor lift，以及 recovery joint/root 随机化。当前 0.5 s finite/residual canary 不能证明 reset 分布或闭环轨迹对齐。
- 结论更新：model4500/scale10 在 Isaac 中已差，训练问题成立；但 model4000/scale45 browser 明显差不能再主要归咎策略，当前 runtime 至少有上述三项可证实的 sim2sim 实现缺口。本轮未修改任何源码或运行服务。

## 2026-07-14 WebSim MuJoCo 风格棋盘地面

- 用户反馈纯色深蓝地面观感不适。renderer 现用 2×2 RGBA `DataTexture` 生成浅灰双色棋盘，repeat 200 次铺满 200×200 m 平面，对应约 0.5 m 方格；近处使用 nearest 放大，远处使用 mipmap 线性融合。
- scene background 改为浅蓝灰，半球光 ground color 与 directional light 强度同步收敛；未修改 MuJoCo scene 中的碰撞、摩擦、接触或任何策略合同。新增 floor texture/geometry/material dispose，避免运行/暂停反复创建 renderer 时泄漏 GPU 资源。
- 完整 Vitest `6 passed`、typecheck 和 Vite production build 通过，仅保留既有 >500 kB chunk warning。服务页面确认引用新 `index-DIpEXaKJ.js`，并通过 `http://127.0.0.1:2705/websim/?camera=wide-follow-v1&floor=mujoco-checker-v1` 重新打开。

## 2026-07-14 WebSim 广角水平跟随相机

- 用户反馈原页面 FOV 太小且机器人容易跑出屏幕。源码确认 renderer 使用固定 `42°` PerspectiveCamera，eye/target 从不读取机器人 root；这是移动出屏的直接原因。
- 新增纯函数 camera contract：vertical FOV `62°`，目标点读取 MuJoCo root x/y 并转换到 three.js x/z，target y 固定 `0.24 m`；每帧以 `alpha=0.2` 平滑水平跟随，距离超过 2 m 的 reset/teleport 直接 snap。camera eye 保持固定世界方向和高度偏移，不随 root yaw/z 改变，避免背景旋转或竖直抖动。
- renderer 地面从 20×20 m 扩为 200×200 m。新增两项 camera tests，完整 Vitest 为 `6 passed`、HTTP canary 1 skipped；`npm run typecheck` 和 Vite production build 通过，initial JS 仍 149.61 kB，renderer chunk 513.72 kB，仅保留既有 >500 kB warning。
- scale45 服务无需重启即可读取新 dist；页面 GET 已确认引用新 `index-DkytZVb8.js`，并通过 `http://127.0.0.1:2705/websim/?camera=wide-follow-v1` 重新发送打开请求。本轮未改策略、物理或 deployment metadata。

## 2026-07-14 WebSim model4000 / wheel scale45 运行

- 用户要求直接查看 wheel action scale 45 的浏览器仿真。服务器当前无 GPU，但纯 actor 导出不依赖 Isaac/GPU；已从旧 run 拉回 `model_4000.pt`，SHA256 `8bc4c47067fd4da7076c2d3dd15188efda32a01b15bcb2768e1e5bb4ba938c45`，放入独立 run-root `artifacts/websim_runs/serialleg_flat_closed_chain/2026-07-13_17-24-18_recovery_history5_scale45/`。
- checkpoint actor 为无 normalization 的 ELU MLP `138→512→256→128→6`。导出 `exported/policy.onnx` 后附加 `se3_rl_lab.websim.deployment.v1`，仅将 wheel action group scale 从当前源码默认 10 改为该 checkpoint 的原生合同 45；ONNX 为 949,022 bytes，SHA256 `0ca6a471b4c014dbe1d308b058fc394faa21a4ccd826906ced315d18489b8dc8`。8×138 随机输入的 ONNX ReferenceEvaluator 与 PyTorch max abs error `1.1920929e-6`，输出全 finite。
- 旧 scale10 WebSim 服务 PID `85111` 已停止；scale45 专用服务运行于 PTY session `27940`，URL `http://127.0.0.1:2705/websim/`。models API 只返回该 scale45 run，session descriptor 明确为 `SerialLeg-Recovery-v0`、wheel scale `45.0`，HTTP 下载 ONNX SHA 与本地一致。
- 前端真实 HTTP BrowserSimulation canary 对该 session 执行 fallen reset + 25 policy cycles/0.5 s，Vitest `1 passed`；页面 GET 成功并已通过 `xdg-open` 发送浏览器打开请求。本轮未修改策略、仿真或 WebSim 源码，未 commit/push。

## 2026-07-14 model4000 scale45 / model4500 scale10 同合同 Isaac A/B

- 为复核“之前有段时间不抖”，在服务器 RTX 4090 对旧 run `model_4000.pt` 执行与当前 `model_4500.pt` 相同的 seed-47、6 scenarios × 2 s Recovery eval。旧 checkpoint 必须匹配其训练时 wheel action scale `45.0`；为避免修改仓库源码，仅在远端 `/tmp/model4000_scale45_eval_worker.py` 与独立 context 中注入 scale override，运行日志明确打印 `[eval-contract] wheel_action_scale=45.0`，actor/critic 为 138D/168D。
- 旧 MP4 已拉回 `artifacts/recovery_eval/model_4000-server-scale45/model_4000-scale45-isaac-eval.mp4`：H.264 1280×720@50 FPS、599 frames、11.98 s、1,377,231 bytes，SHA256 `11861dff76fcb6a0e5d128201dc3f244694e34dee8608322397cc134cbc4b8b3`。600 steps、0 termination/non-finite、survival 1.0、vx/yaw RMSE `0.2528121/0.2606376`、max loop residual `0.0009936 m`。
- 已生成并打开标注同屏视频 `artifacts/recovery_eval/model4000-scale45-vs-model4500-scale10-side-by-side.mp4`：H.264 1280×360@50 FPS、599 frames、11.98 s、1,850,776 bytes，SHA256 `dedb56ada079b64ece6a5d2c35de2593fd5ef6003cef4669b2747a6c5e9fd2aa`。左侧旧 model4000/scale45，右侧当前 model4500/scale10；抽帧与指标均显示当前策略姿态波动更明显，尤其 yaw RMSE 约为旧策略 `2.02×`。
- 结论边界：Isaac 中已复现当前策略更抖，因此不能归因于纯 WebSim sim2sim。该 A/B 同时改变 checkpoint lineage、训练 wheel action scale 与训练 init std（确定性 inference 不直接采样 std，但训练结果受其影响），所以不能单独断言 scale 10 是根因；下一步若要做因果定位，应补 pitch-rate/raw action/wheel target/velocity/torque saturation probe，或做同一训练合同的 checkpoint 时间序列比较。

## 2026-07-14 Isaac Play MP4 请求

- 用户恢复训练服务器后，在空闲 RTX 4090 上用远端 `model_4500.pt` 重录。首次 `se3rl eval` 因旧 run manifest 把任务错误解析为 Flat 34D，checkpoint 138D load mismatch；随后将 eval context 明确设为 `SerialLeg-Recovery-v0` 并直接调用 worker，正确解析 actor/critic `138D/168D` 后成功完成 6×2 s 固定场景。
- 远端生成 `model_4500-step-0.mp4`、metrics 和 telemetry，已拉回 `artifacts/recovery_eval/model_4500-server/`。MP4 为 H.264 1280×720@50 FPS、599 frames、11.98 s、1,511,057 bytes，SHA256 `4b43e3b0edc0c86554996ac27107013dc4c0572c650f0592b3f99ff3b6ff4384`；接触图抽帧确认机器人持续可见，但多场景明显侧倒/失稳，已通过 `xdg-open` 打开。
- model4500 summary：600 steps、0 termination/non-finite、survival 1.0、vx/yaw RMSE `0.2879477/0.5261201`、max loop residual `0.0007378 m`。termination-based survival 仍不能解释为稳定站立；Isaac 本身已复现明显不稳，因此 WebSim 抖动不能归为纯 sim2sim。
- 用户停止其他 Isaac Play 后，本机 RTX 5060 显存恢复至约 174 MiB 使用；尝试以 `model_4500.pt` 录制 500-step Play，进程 exit 0，但默认 headless 相机只录到地面，该 MP4 已删除。
- 随后用固定世界朝向跟随相机运行 6×2 秒 Isaac Eval；仿真与渲染运行约 6.5 分钟并正常关闭，但 Isaac 录制封装未留下 MP4/metrics，临时 context/目录已清理，未把失败结果交付用户。
- 曾临时打开同一系列 `model_1000` 有效视频作为 fallback，但用户指出 checkpoint 不一致；现已由真正的 model4500 服务器录像取代，后续不得再用 model1000 代表当前 WebSim ONNX。

## 2026-07-14 WebSim submodule 启动

- 视觉阶段完成：采用闭链视觉 MJCF 的 23 个 visual geoms，并新增 `scripts/build_websim_visual_meshes.py` 生成浏览器专用 STL。原始视觉约 234.9 万面/117.4 MB，减面后约 29.8 万面；完整 scene manifest 为 78 files/15.3 MB。
- 原始视觉资产直接进入官方 WASM 时触发 2 GiB 内存上限；减面资产经 MuJoCo 3.10.0 成功编译为 77 meshes/80 geoms、153,934 vertices/305,099 faces，mesh face index 和 standing finite gate 通过。
- three.js renderer 改为读取 MuJoCo compiled `mesh_vert`/`mesh_face`，只显示 group 1 visual geoms；不再把 mesh 退化为 `geom_rbound` 球体。正式 ONNX 已补当前 asset fingerprint metadata，真实 HTTP fallen 25-cycle rollout 再次通过。
- Vite 页面已重建并在 `http://127.0.0.1:2705/websim/` 启动，浏览器打开请求已发送；等待用户目视验收。服务会话仍在当前 Agent 终端中运行，功能未 commit/push。
- 第三阶段完成：新增主仓库 native + submodule Vitest 共享 golden fixture，三档高度默认位姿与 DM/M3508 包络双向对拍；前端另锁 138D term-major oldest→newest history 和 1 physics-step FIFO。
- Browser runtime 新增可复现 fallen reset、左右 closure-site 最大残差、qpos/qvel/ctrl finite gate；页面提供 Stand/Fall 按钮及 loop residual/finite telemetry，运行中禁用 load/reset 避免异步 inference 生命周期竞争。
- 真实 HTTP canary 使用临时附加正式 metadata 的 138→6 ONNX，经服务端加载 55 assets 后执行 fallen reset + 25 policy cycles/0.5 s，finite 且 closure residual 保持 `<5 mm`；首次失败记录峰值约 `2.190 mm`，因此 gate 采用 5 mm 而非无证据的 1 mm。
- `main.tsx` 对 MuJoCo runtime 与 renderer 使用动态 import；Vite 初始 JS `1,190.47→149.61 kB`，另生成约 523.10/512.50 kB 的按需 chunks。功能仍未 commit/push。
- 第二阶段完成：新增确定性 `scripts/build_websim_scene.py`，从 canonical MJCF 生成 5 ms `scene.xml`、6 路 direct-torque actuator 和只包含 entrypoint + 54 STL 的 `websim_manifest.json`；服务端 session 返回逐文件 URL/size 并执行路径与存在性校验。
- Submodule 锁定官方 `@mujoco/mujoco@3.10.0`、`onnxruntime-web@1.27.0`、`three@0.185.1`；浏览器已串联 VFS asset load、ONNX policy、term-major 5-frame history、height-conditioned leg targets、1-step FIFO、DM/M3508 torque-speed clipping、decimation stepping、three.js viewport、命令滑杆与 telemetry。
- 官方 MuJoCo WASM 真加载报告 `nq=17 nv=16 nu=6 ngeom=57 neq=2 ntendon=4`，standing height `0.22`，单步时间 `0.005`；现有 Recovery ONNX 经 ONNX Runtime Web 真推理得到 6 个 finite actions。功能未 commit/push。

- 用户确定采用 submodule，名称固定为 `websim_se3`；随后要求删除最初导入历史的仓库、从零建立独立仓库，且 submodule 文件不得出现参考仓库字样。
- 目标架构：Python server 负责 run/ONNX 发现、metadata/scene contract 校验与静态资源；浏览器内运行 MuJoCo single-thread WASM、ONNX Runtime Web 和 three.js。runtime 顺序为 observation→ONNX inference→action→decimated `mj_step`→event/telemetry→published render frame。
- 现有 WebSim 功能包括自动跟随最新 ONNX、standing/random-fall reset、键盘速度命令、电机开关、仿真速度、root follow、visual/collision/contact/contact-force overlay、joint monitor 和拖拽外力。
- SE3 readiness：已有 canonical closed-chain MJCF、528 KiB meshes 和 924 KiB Recovery ONNX（input `obs[1,138]`、output `actions[1,6]`）；ONNX `metadata_count=0`。主要实施缺口是 deployment schema、浏览器 scene bundle、4+2 mixed control、delay FIFO 与 T-N curve。
- Git/submodule 状态：`am345/websim_se3` 已重建为 private、`isFork=false`、仅有独立 `Initial commit`，并以根目录 submodule 接入；当前功能位于未提交分支 `codex/bootstrap-websim`。本轮不会提交或推送主仓库现有 Recovery 改动。
- Submodule bootstrap 已实现独立 Python package/CLI、safe local run discovery、strict metadata parser、session/static service、React/Vite shell、8 项 backend tests 和 frontend build；全仓禁用词搜索保持 0 命中。
- 主仓库新增 `serialleg_policy_contract.py` 与 `websim/deployment.py`，Recovery `play.py` 在 ONNX 导出后附加项目 schema；Flat 导出保持不变。为避免纯合同读取拉起 Kit，`assets.robots` 改为惰性导入，`mdp/observations.py` 从轻量合同显式 re-export 原有常量。
- 真实 `policy.onnx` 临时副本完成 metadata round-trip 和 submodule parser cross-contract canary：138D input、6D output、130D proprio、`joint_position/joint_velocity` mixed action、1-step delay、asset fingerprint 均通过；未修改原 artifact。

## 2026-07-14 本机 Isaac Sim play model4500

- 用户要求启动 Isaac Sim play。远端容器仍可 SSH，但 GPU 设备、Xorg :20 和 Selkies :3000 均已被平台释放，无法在远端显示；未尝试在无 `/dev/nvidia*` 的容器强启 Vulkan。
- 本机 `DISPLAY=:0`、RTX 5060 8 GiB、Isaac Sim 5.1 环境可用，因此用已拉回的 `model_4500.pt` 启动 `SerialLeg-Recovery-v0` 单环境 GUI play，启用 collider visualization。PID/SID `888603`，日志 `/tmp/recovery_wscale10_std1_model4500_local_play.log`。
- runtime 成功加载 checkpoint，actor/critic 为 138D/168D；X11 窗口 `0x320000b` 标题 `Isaac Sim 5.1.0`、1440×975、Map State `IsViewable`，GPU compute 显存约 4,542 MiB。fatal scan 无 Traceback/OOM/assertion；inotify errno 28 为既有 watch-limit 噪声。

## 2026-07-14 wheel scale 10 / std 1 最后 checkpoint 拉回

- 用户称训练已完成并要求拉回最后 checkpoint；复核远端发现 PID 28576 已退出，但日志只到 iteration 4760/5000，run 中不存在 `model_4999.pt`。fatal scan 无 Traceback/OOM/assertion/NaN，退出原因 `UNKNOWN`；没有擅自 resume 或重开训练。
- 最后实际落盘 checkpoint 为 `model_4500.pt`，5,868,725 bytes，SHA256 `168bd10af72c603586bcea760c6608c6ad5f731d48ab804be376d995fc2ed8c4`。已拉回 `artifacts/recovery_checkpoints/history5_wscale10_std1_fresh_5k/model_4500.pt`，远端/本地 SHA 一致。
- 本地 `torch.load` 审计 72 tensors、1,461,681 tensor values，non-finite tensors 为 0。该文件是最后可用 checkpoint，不得称为完整 5k final checkpoint。

## 2026-07-13 wheel scale 10 / std 1 model1000 MP4

- 用户要求用当前最新 checkpoint 录制 MP4；查询时 active run 到 iteration 1031，最新落盘为 `model_1000.pt`。未暂停 4096-env 训练，按既有 fixed seed-47、6 scenarios × 4 秒 standard suite、`--no-rerun` 执行，eval exit 0，actor/critic 输入确认 138D/168D。
- 远端/本地 MP4 均为 H.264 1280×720@50 FPS、1199 frames、23.98 秒、2,774,720 bytes，SHA256 `067276bd6aaeea009175f4213cc7015c236d6d4a8f2dfb0026c6d242ad889ab9`；本地路径 `artifacts/recovery_eval/wscale10-std1-model1000-recovery-eval.mp4`。
- Metrics 为 1200 steps、0 termination/non-finite、vx/yaw RMSE `0.16569/0.32235`；eval fatal scan 为空。录制与 scp 后正式训练 PID 28576 继续到 iteration 1133，显存约 5.0 GiB，训练 fatal scan 为空。

## 2026-07-13 wheel scale 10 / Recovery std 1 重建与 fresh 5k 启动

- 用户明确要求只把 wheel `action_scale` 改为 `10.0`、Recovery `init_std` 改为 `1.0`，停止当前训练并 fresh 重开；没有授权联动修改 raw action-rate/smoothness。已将 `robot_config.yaml` 的 wheel scale `45→10`，将 `RecoveryPPORunnerCfg` 的 Gaussian std `0.5→1.0`，同步更新 actuator/recovery/runtime smoke 断言与 README；`diff_drive_max_wheel_speed=45` 保持不变。
- 旧正式 PID 2577 在 iteration 4154/5000、reward 251.63、std 0.31、catastrophic 0 时收到 SIGTERM，约 1 秒退出；run/log/checkpoint 全保留。最后已落盘 `model_4000.pt` 为 5,868,725 bytes，SHA256 `8bc4c47067fd4da7076c2d3dd15188efda32a01b15bcb2768e1e5bb4ba938c45`，不得误写为异常失败或 resume 候选。
- YAML SHA 改动后，本机 `convert_serialleg_urdf_to_usd.py --check` 如预期报告旧 USD contract hash mismatch；本机 Isaac Sim 同时打印既有 inotify errno 28 和 8 GiB Vulkan OOM 噪声。改在空闲 RTX 4090 上重建，随后远端 `--check` exit 0；本机/远端生成 USD SHA256 同为 `6567f64953b2a7130a4223cf3bb5a0f06d8f552a868de245dc1f109918fa56ec`。
- 本机新合同聚焦 pytest `18 passed`，远端含 history 测试为 `23 passed`，相关 Ruff check/format 与 `git diff --check` 通过。4096-env/1-update gate `2026-07-13_19-42-46_recovery_history5_wscale10_std1_4096_gate` 实际构建 actor/critic 138D/168D；98,304 steps、31,027 steps/s、reward -0.88、std 1.00、catastrophic 0，runtime YAML 确认 action wheel scale 10、init std 1、resume false。
- 新正式 run `2026-07-13_19-43-59_recovery_history5_wscale10_std1_fresh_5k` 以 seed42/4096 env/5000 iterations fresh 启动；PID 28576、PPID1、SID28576，日志 `/tmp/recovery_history5_wscale10_std1_fresh_5k.log`。iteration 84 时约 47,985 steps/s、std 1.22、catastrophic 0、fatal marker 0，近期显存 4,924 MiB；`model_0.pt` SHA256 `4df48d8c...17a3ad`。早期 reward -758.39 仍属高探索/未收敛阶段，不能据此判断最终 tracking/jitter。
- 一次带内联完整训练命令的 `pgrep` guard 自匹配而安全退出，未启动 gate；改用进程可执行名过滤时 awk shell quoting 又报语法错误，但 guard 变量为空后仍启动了唯一 gate。gate 完成后已确认没有残留训练进程；正式 run 启动前 GPU 空闲。后续防重检查应使用 `ps -C python -C python3 ... | grep`，不要让 guard 搜索自身完整命令行。

## 2026-07-13 五帧 history model3000 高度 0.30 m / 速度 1.5 m/s MP4

- 用户要求固定 `height=0.30 m`、`vx=1.5 m/s` 录制视频；查询时最新落盘 checkpoint 仍为 `model_3000.pt`。不改产品源码，以临时 context/运行时单场景列表运行现有 worker；seed 47、8 s、yaw 0、其余 command 0，独立输出在 `custom_eval/model_3000_h030_vx15/`。
- MP4 H.264 1280×720@50 FPS、399 frames、7.98 s、1,171,954 bytes，SHA256 `1150ff91140d28e7a8bbd92da97fa7f2ad676768ef392192bb6f1d395eed3d62`；本地为 `artifacts/recovery_history5/model_3000-h030-vx15-{step-0.mp4,metrics.json,telemetry.json}`。
- 400 telemetry rows 的 vx/yaw command 恒定为 `1.5/0.0`，0 termination/non-finite。后 4 s vx mean/RMSE `1.4699/0.0700 m/s`、height mean/RMSE `0.3049/0.0056 m`；后 2 s vx mean/RMSE `1.4699/0.0699 m/s`、height mean/RMSE `0.3049/0.0056 m`、yaw RMS `0.1358 rad/s`。
- 评估后确认训练 PID 2577 仍在运行，iteration 3343/5000、reward 253.13、catastrophic 0；早先过窄的 `pgrep` 模式未匹配到 `--task` 参数位置，并非训练退出。

## 2026-07-13 五帧 history model3000 高度 0.35 m / 速度 1.5 m/s MP4

- 用户要求最新 checkpoint 执行 height/vx `0.35 m/1.5 m/s` 固定 command。查询时训练 iteration 3017，最新已落盘 checkpoint 为 `model_3000.pt`，5,868,725 bytes，SHA256 `912a7f53c31b1f8cc3a9e6c766780d1c06de781925743af1ac5f81ec2737fe10`。
- 不改产品源码，用临时 context/运行时单场景列表运行现有 worker；seed 47、8 s、height 0.35 m、vx 1.5 m/s、yaw 0，其余 command 0。训练 height 范围为 0.20–0.32 m，所以本次为轻度 OOD 高度泛化测试。run-local 输出在 `custom_eval/model_3000_h035_vx15/`，不覆盖 standard eval。
- MP4 H.264 1280×720@50 FPS、399 frames、7.98 s、1,348,208 bytes，SHA256 `29a80335f9fc4b9277a56df1f67cd26670cd553215164e7d04ec34bb06bb2a27`；本地为 `artifacts/recovery_history5/model_3000-h035-vx15-{step-0.mp4,metrics.json,telemetry.json}`。
- 400 telemetry rows 的 vx/yaw command 恒定为 `1.5/0.0`，0 termination/non-finite。后 4 s vx mean/RMSE `1.3848/0.1317 m/s`，height mean/RMSE `0.3486/0.0044 m`；后 2 s 分别为 `1.3907/0.1275 m/s` 与 `0.3500/0.0027 m`，yaw RMS `0.1383 rad/s`。评估后训练 iteration 3076，reward 251.78、std 0.29、catastrophic 0，无 fatal marker。

## 2026-07-13 五帧 history model2500 固定 2 m/s MP4

- 用户要求用最新 checkpoint 查看 2 m/s 效果。查询时训练 iteration 2605，最新已落盘 checkpoint 为 `model_2500.pt`，5,868,725 bytes，SHA256 `3488dfb7f72a41ed5add8c8e7a6a106f9c193a2a3e4f495d434186d909e7f397`。
- 不改生产源码，用临时 context 和运行时单场景列表启动现有 worker；seed 47、8 s、`vx=2.0 m/s`、yaw 0、height 0.26 m、其余 command 0。输出位于 run-local `custom_eval/model_2500_forward_2mps/`，不覆盖标准 six-scenario eval。
- MP4 H.264 1280×720@50 FPS、399 frames、7.98 s、1,271,481 bytes，SHA256 `586288bba673076d6fafdb0b0c72f6ea770dc03af3b9b6416e02458626688f2b`；本地为 `artifacts/recovery_history5/model_2500-forward-2mps-{step-0.mp4,metrics.json,telemetry.json}`。
- 400 telemetry rows 的 command 恒定为 vx/yaw `2.0/0.0`，0 termination/non-finite。整段 mean/RMSE `1.1087/1.3055 m/s` 混入起步瞬态；后 4 s mean/RMSE `1.9047/0.0991 m/s`，后 2 s mean `1.8967 m/s`。评估后训练 iteration 2674，reward 250.94、std 0.30、catastrophic 0，无 fatal marker。

## 2026-07-13 五帧 history model2000 最新 checkpoint MP4

- 用户要求录制最新 model；查询时正式训练为 iteration 2318，最新已落盘 checkpoint 是 `model_2000.pt`。使用与 model500/1000 一致的 seed-47、`flat-basic` 6×4 s、deterministic actor/no corruption、translation-only 78° FOV、`--no-rerun` 合同；worker exit 0，训练未暂停。
- MP4 H.264 1280×720@50 FPS、1199 frames、23.98 s、2,353,573 bytes，SHA256 `8b1cd91f19cf1e4a2d8596c75971089001f4c048eb1f1925c5102c3d768e7b22`。本地保存 `artifacts/recovery_history5/model_2000-{step-0.mp4,metrics.json,telemetry.json}`。
- metrics 为 1200 steps、0 termination/non-finite、vx/yaw RMSE `0.16774/0.24523`。相比 model1000，yaw RMSE 下降，vx RMSE 上升；stand/reverse vx RMSE 为 `0.27276/0.22349`。因已知聚合 RMSE 不能代替视觉 tracking/jitter 验收，当前不提前宣称 model2000 行为优劣。
- 评估完成后训练仍在 PID 2577 健康继续：iteration 2410、约 51,039 steps/s、reward 250.81、std 0.29、catastrophic 0，无 fatal/NaN/OOM marker。

## 2026-07-13 五帧 history model1000 对比评估

- 正式 run 健康落盘 `model_1000.pt`，SHA256 `0fc487f4dc4dffa55e6a4c272461fc1daa1cad6dc281f2f62e35e20302e0e65d`。首次 CLI 调用错用 `--checkpoint model_1000.pt` 选择器而 exit 1，未启动 Isaac worker/未改动训练；改用支持的 `--checkpoint 1000` 后完整评估 exit 0。
- 同 model500 的 seed-47、`flat-basic` 6 scenarios × 4 s、deterministic actor/no corruption、translation-only 78° FOV、`--no-rerun` 合同。MP4 H.264 1280×720@50 FPS、1199 frames、23.98 s、2,522,290 bytes，SHA256 `4827d724baabcd7dcd6276f4f2052df0e697e0e6cd2402af7b5616133528ca71`。
- 1200 rows 全部 finite、0 termination；总 vx/yaw RMSE `0.21508/0.70924→0.14640/0.35554`，stand vx/yaw RMSE `0.22301/1.08666→0.16683/0.40593`。用户查看并排 MP4 后明确更正：model1000 相比 model500 的抖动已改善。stand base-height 整段 detrended RMS/p2p 混入姿态漂移和大幅运动，不能单独代表高频抖动；flat-basic 仍未记录 pitch-rate/逐关节 action/wheel saturation，后续需专用 jitter probe 量化改善幅度。
- 用户进一步目视判定 model1000 tracking 较差。拆分每场景后 100 steps 的稳态 telemetry：yaw-left `1.325` vs command `1.0`，yaw-right `-1.561` vs `-1.0`，forward-turn `1.050` vs `0.8`，过冲约 `33%/56%/31%`；forward/reverse 线速度 `0.436/-0.567` vs `0.5/-0.5`，仍约 13% 欠冲/过冲。因此结论为“相对 model500 聚合 RMSE 改善，但绝对 tracking 不合格”。
- 本地保存 `artifacts/recovery_history5/model_1000-{step-0.mp4,metrics.json,telemetry.json}`，并生成 1280×360@50 FPS、23.98 s 的 `model_500-vs-1000-side-by-side.mp4`。评估后正式训练仍在 PID 2577 继续，iteration 1110、显存 5,042 MiB。

## 2026-07-13 五帧 history model500 MP4

- 用户要求查看 500 轮模型。确认正式 `recovery_history5_fresh_5k` 已产出 `model_500.pt`，并在训练继续运行时用现有 `se3rl eval` 固定合同执行 seed-47、6 scenarios × 4 秒、`--no-rerun` 录制；未暂停或修改训练。
- 用户查看 MP4 后明确反馈“还是抖得不行”。诊断确认 stand 段 velocity/yaw-rate RMSE 为 `0.2230 m/s`/`1.0867 rad/s`，且 telemetry 未包含 pitch-rate、逐关节 action 或 wheel saturation；因此当前 `model_500` 判为控制质量不合格，但尚不能仅凭该早期 checkpoint 判定完整 5k 历史方案最终失败。后续 checkpoint 必须补同 seed jitter telemetry 并与 4–5 Hz baseline 比较。
- Eval runtime 确认 actor `command+proprio=138D`、critic `command+privileged=168D`，固定世界朝向相机为 78° FOV。输出 `model_500-step-0.mp4` 为 H.264 1280×720@50 FPS、1199 frames、23.98 秒、2,933,035 bytes，SHA256 `0faac91344dae0ee942009f786d0d09ea12f482ff7c20c5695d5e49882799ece`；日志无 Traceback/OOM/Error/NaN。
- metrics 为 1200 steps、0 termination/non-finite、vx/yaw RMSE `0.21508/0.70924`。stand/reverse/yaw_right 三处抽帧均有有效机器人/地面/箭头，但 stand 与 yaw_right 明显侧倾或倒地；termination 合同未触发，不能用 survival 1.0 代替姿态/recovery 验收。
- MP4 与 metrics 已同步本地为 `artifacts/recovery_eval/model_500-history5-recovery-eval.mp4` 和 `model_500-history5.metrics.json`，本地 SHA/ffprobe 与远端一致。录制后正式训练继续到 iteration 641，reward 242.20、std 0.44、catastrophic 0。

## 2026-07-13 五帧历史 4096-env 门禁与 fresh 5k 启动

- 用户开启 GPUFree 服务器并授权训练验证。远端 RTX 4090 24 GiB 空闲、数据盘余 27 GiB、无训练进程；远端 dirty worktree 为上一轮功能文件，未整仓覆盖。首次 `rsync` 因远端无命令在传输前失败，改用仅包含 13 个本次路径的 tar stream，同步后逐项 SHA256 为 13/13 OK。
- 训练机相关 Ruff 全通过，`test_serialleg_observations.py + test_recovery_contract.py + test_experiment_tools.py` 为 `26 passed in 4.53s`。
- 4096-env/1-update CUDA gate `2026-07-13_17-22-53_recovery_history5_4096_gate` 通过：actor/critic 首层 138/168，98,304 steps、29,441 steps/s、peak GPU 4,818 MiB、reward -0.84、std 0.50、catastrophic 0，保存 model0。日志 `/tmp/recovery_history5_4096_gate_20260713_172240.log`。
- 正式训练以 seed 42、4096 env、5000 iterations、24 steps/env、save interval 500、`resume=false` 启动；PID 2577/PPID1/SID2577，日志 `/tmp/recovery_history5_fresh_5k.log`，run 为 `2026-07-13_17-24-18_recovery_history5_fresh_5k`。两次带内联 `pgrep` 的防重启动 guard 因匹配自身命令行而安全退出，未生成日志或训练进程；随后拆分 probe/launch 后成功启动唯一进程。
- runtime YAML 锁定 seed42、actor `command+proprio`、critic `command+privileged`、normalization/PPO 预期值和 `resume=false`。iteration 117 时 49,073 steps/s、value 22.9083、reward -652.90、std 0.72、catastrophic 0，显存约 5.0 GiB，无 NaN/OOM/Traceback；早期完整 episode reward 尚未收敛，训练继续运行。

## 2026-07-13 Recovery Kyber-style 五帧历史实施

- 用户在只读方案核对后明确授权实施。为保留既有 flat 策略/checkpoint，历史只落到 `SerialLeg-Recovery-v0`：新增 `command/proprio/privileged` groups，当前 command 为 8D，policy/critic 历史分别为 `26×5=130D` 与 `32×5=160D`；RSL-RL mapping 得到 actor 138D、critic 168D，MLP/PPO 其余结构不变。
- `mdp/observations.py` 新增 Recovery 维度、term dims 和 term-major slice metadata；`recovery_env_cfg.py` 复用 flat 观测 producers/noise，group history length 固定 5、oldest→newest flatten，privileged group 关闭 corruption。保留工作树中既有的 Recovery wheel action-rate `-0.02` 变更，没有回滚或归因到本任务。
- `rsl_rl_ppo_cfg.py` 为 Recovery 设置 actor `['command','proprio']`、critic `['command','privileged']`；flat mapping 保持 `actor/critic`。eval worker 与 play 入口改为根据 runner actor groups 关闭 corruption，兼容两种任务；run manifest 按 task 写入 34/40 或 138/168。
- `smoke_recovery_reset.py` 增加 exact group shape、finite 和 reset 首帧五槽复制 gate；静态测试锁 group term、布局、PPO mapping、flat 不变、eval corruption 与 manifest。README/实验工具文档已移除“Recovery 可直接加载 flat model499”的错误说明，明确必须 fresh train。
- 本机 4-env CPU runtime smoke 通过，manager 实际显示 `command/proprio/privileged=(8/130/160)`；2 steps finite，reset history、height default、passive/tendon/clearance 均通过。随后 4-env CPU PPO 完成 96 samples/1 update，实际模型首层为 actor `138→512`、critic `168→512`，生成 `.../2026-07-13_17-09-31_recovery_history5_smoke/model_0.pt`（5,868,043 bytes）。
- 聚焦 pytest 为 `25 passed, 1 deselected`；完整同组测试唯一失败是本机未安装可选 `rerun-sdk` 的既有 Rerun export test。相关 Ruff、`py_compile` 与 `git diff --check` 通过。尚未跑 4096-env GPU capacity gate、长训练、JIT/ONNX 或 sim2sim。

## 2026-07-13 Kyber-style 5-frame observation history 方案核对

- 用户指定参考 `BioInnov/kyber_rl_lab`，在网络输入端堆叠历史观测，并要求当前先不改代码。GitHub connector/网页因仓库权限返回 404；通过现有只读 Git 凭据确认远端默认分支为 `main@93aacd351cb9a453baa9c29141dcc1e0fb6bde4e`，在 `/tmp/kyber_rl_lab_ref_93aacd` 浅克隆核对，未触碰本项目或已有 dirty Kyber 工作树。
- Kyber Recovery 将 command 与 proprioception 分为独立 observation groups：runner actor 使用 `['vel_cmd','proprio']`、critic 使用 `['vel_cmd','priv']`；`ProprioceptionCfg.history_length=5`，`PrivilegedCfg` 继承同一 5 帧历史并关闭 corruption，command group 不堆叠。网络仍为 `[512,256,128]` ELU MLP。
- 读取固定 IsaacLab `b4c3210` 的 `ObservationManager`/`CircularBuffer`：每个 term 独立缓存，输出顺序为 term-major 且每个 term 内 oldest→newest；reset 清空计数/数据，首次 append 把当前样本复制到全部历史槽。Kyber MuJoCo `ObservationBuilder` 也按相同顺序和首帧复制语义组装部署输入。
- 当前 actor 34D 可分为 8D command/jump 与 26D proprioception；critic 另有 6D privileged state。按 Kyber 的 5 帧方案，actor 为 `8 + 26×5 = 138D`，critic 为 `8 + (26+6)×5 = 168D`。50 Hz 下 5 个样本时间戳跨度 80 ms，对 4.5 Hz 振荡约覆盖 130° 相位。
- 为保持可归因性，首次实施建议只改变 observation history：继续使用 feed-forward MLP、actor normalization off、critic normalization on、24-step rollout、现有 Recovery PPO/reward/action/物理和训练预算，并从 seed 42 fresh train。现有 checkpoint 输入形状不兼容。当前未修改任何生产/测试源码或配置。

## 2026-07-13 同 PhysX reference GRU 与 hidden-state 因果消融

- 按用户“先找问题、不要改代码”的约束，使用 inline Python 只读加载 `origin/se3_wheel_leg_spring_add:assets/base_model/recovery-flat.pt` Git object 和本地 `m005/model_4999.pt`；没有创建诊断源码文件，也未改 production config。运行时只在内存中构造 34D normalized hidden-512 GRU。
- 两个 checkpoint 使用同一个本机 CPU PhysX、1 env、seed 47、50 Hz、actor corruption/startup randomization/curriculum push 关闭、0.26 m 固定站立命令、相同 closure-consistent 人工状态和 50-step zero-action 初态；各 rollout 600 control steps，均无 termination。
- 当前 `m005` unnormalized MLP 精确复现 `4.5 Hz`：稳态 pitch RMS/p2p95=`3.159°/9.319°`，pitch-rate RMS=`1.546 rad/s`，镜像 wheel-coordinate action/speed difference RMS=`1.070/12.477 rad/s`，wheel action 超 `71.81 rad/s` no-load target 的比例为 9.3%。这把远端 MP4 的约 4 Hz 视觉证据落到了本机 raw state/action telemetry。
- 旧 normalized GRU 在完全相同当前 PhysX 中先从约 `-30°` zero-action 倾倒状态恢复，再稳定在约 `3.5°`；分析窗 pitch RMS/p2p95=`0.060°/0.203°`，pitch-rate RMS=`0.000804 rad/s`，wheel action/speed difference RMS=`0.000998/0.0395 rad/s`，0% 超 no-load target。其标注的 2.5/7.2 Hz 频点幅值接近数值噪声，不是可见极限环。
- 对同一个 GRU 在每次 policy forward 前清空 hidden state，其他条件不变，立即得到 `4.8 Hz`：pitch RMS/p2p95=`0.393°/1.111°`，pitch-rate RMS=`0.205 rad/s`，wheel action/speed difference RMS=`0.180/2.368 rad/s`。因此历史隐状态对抑制 4–5 Hz wheel–plant 相位振荡具有直接因果作用，不只是“旧 checkpoint 参数更好”的相关性。
- 结论边界：PhysX/contact/backend 与 `wheel_action_rate` 已从主因降级；当前从已验证 GRU 合同改为部分可观测的无记忆 MLP 是核心迁移错误。normalization、64-step rollout、PPO 参数和 `5.33×` 训练预算仍与 architecture 同时不同，需要在获准改配置/训练后再逐项拆分。
- Isaac Sim 启动仍打印既有 inotify `errno=28` change-watch 噪声；`df -h/-i` 显示磁盘仅 15%、inode 2%，未影响环境或两次 600-step rollout。并行 Kyber 进程仍占约 5.7 GiB GPU，因此本轮有意使用 CPU PhysX；未终止或修改该用户进程。

## 2026-07-13 wheel reward 之外的抖动根因对照

- 按用户要求停止把 `wheel_action_rate` 数值当主假设，全程未修改生产源码；读取本地旧仓库 `/home/am345/se3_rl`、历史分支 `origin/se3_wheel_leg_spring_add@93f6ba2`、本地备份 checkpoint/config/log 与两段最终 MP4。
- 对 `-0.02/-0.05` MP4 的首个站立场景做 50–199 帧背景特征光流；left/right/both 三种独立 crop 均得到相同 `4.027 Hz` 主峰。两段视觉 flow RMS 约 `0.44–0.67 px/frame`，说明权重改变了局部幅值但没有改变闭环模态。
- 最终训练日志中 `-0.02/-0.05` wheel action-rate 为 `-0.0196/-0.0447`，除以权重后原始量约 `0.98/0.894`，只下降约 9%；action-smoothness 为 `-0.1546/-0.1537`，除以 `-0.03` 后约 `5.15/5.12`，几乎不变。更强惩罚没有把策略带到不同的平滑控制解。
- 源码逐项对照确认参考与当前的 34D actor observation 布局/缩放、6D action、leg/wheel scale `0.25/45`、action clip `100`、4–6 ms delay（5 ms physics 下恒为一拍）、50 Hz control 和分段轮 T-N 包络一致；这些不是当前找到的迁移漂移。
- 旧分支 exact-reward checkpoint `assets/base_model/recovery-flat.pt` 通过 Git object 只读加载：iteration 4999、34D input、actor normalization enabled、GRU hidden 512、约 1.269M actor values；当前三档 checkpoint 均为 unnormalized 34D MLP、约 0.183M actor values。旧仓库 README 还明确写着 `mlp.pt` 是随机初始化占位，当前没有“同奖励完整 MLP 且不抖”的旧基线。
- 参考 checkpoint actor normalizer count `2,621,964,288`、env common step `320,064`，精确对应 8192 env；当前合同为 4096 env × 24 steps × 5000，total transitions 仅参考的 `1/5.33`，每 env 步数仅 `120,000/320,064≈37.5%`。同为 5000 iterations 并不代表同训练预算或同 curriculum 熟化程度。
- 对 baseline/`-0.02/-0.05` MLP 在近似直立固定外部 observation 下只闭合 `last_actions` 递推，均收敛到固定点；局部 last-action Jacobian 谱半径分别约 `0.684/0.641/0.725`。因此 last-action 回灌会影响增益，但不能单独产生持续振荡；必须经 robot state/wheel plant 反馈闭环，与既有 hold-wheels A/B 一致。
- 本阶段形成的工作假设是：相同瞬时 34D actor 输入缺少 base linear velocity、wheel contact 和 base height，旧 normalized GRU 可用历史隐状态估计/滤波这些量，当前无记忆 MLP 只能依赖 IMU/joint/wheel velocity/last-action 代理，学成约 4 Hz 有相位滞后的动态平衡。该假设随后已由上节同 PhysX reference-GRU/hidden-reset A/B 验证；24-step rollout、normalization 和较小样本预算的独立贡献仍未拆分，backend 已降为次级风险。

## 2026-07-13 wheel action-rate 三档 fresh 5k 串行训练与值守

- 在远端确认 RTX 4090 空闲、数据盘剩余 28 GB、无既有训练进程或长 run 名称冲突后，创建仅位于远端 `/tmp` 的串行监督器；不新增仓库训练代码。
- 监督器顺序固定为 `-0.02→-0.05→-0.1`，每档使用 `SerialLeg-Recovery-v0`、4096 env、seed 42、5000 iterations、fresh `resume=false`。每档独立日志/进程组；只有 exit 0、iteration 4999 且 `model_4999.pt` 存在才启动下一档。
- 安全值守检查 fatal log marker、非有限指标、reward/value/action-std/leg-acc 数值爆炸和 catastrophic spread；异常时停止当前进程组并终止 sweep。历史健康/失败日志回放分别判定正常与 value-loss 爆炸，监督器本地/远端 `py_compile` 及本地 Ruff 通过。
- 第一档 `-0.02` 于 13:00 健康完成：`2026-07-13_10-38-12_recovery_wheel_rate_m002_fresh_5k` iteration 4999 reward/value/std/wheel-rate/leg-acc=`261.20/0.1667/0.31/-0.0196/-0.0043`，catastrophic 0，8466.76 秒；安全跨过全部 cache stages 与旧 3193–3204 污染窗口。`model_4999.pt` 为 4,441,781 bytes、SHA256 `9455a0e4...e4832abf`，72 个 tensor 全部 finite。
- 监督器等待 20 秒后于 13:00:26 自动启动第二档 `-0.05`，run `2026-07-13_13-00-34_recovery_wheel_rate_m005_fresh_5k`；runtime YAML 精确记录 weight `-0.05`、seed 42、4096 env、5000 iterations、24 steps、`resume=false`。iteration 16 reward `-257.40`、std `0.51`、catastrophic 0，无 NaN/OOM。
- `-0.05` 已越过 iteration 2000 的 25% cache stage，并额外值守至 2112；精确 iteration 2000 reward/value/std/wheel-rate/leg-acc=`253.38/0.2281/0.30/-0.0383/-0.0049`、catastrophic 0。切换后 value loss 短时升至 0.3994，至 2094 回落为 0.2093；iteration 1780/1910 附近各有 `catastrophic=0.0002` 的孤点并自行回零，未形成扩散。`model_2000.pt` 4,441,781 bytes、SHA256 `4886587a...39bdf59`。
- `-0.05` 后续健康通过 2600 cache stage 与旧 3193–3204 首爆窗口。iteration 3000 reward/value/std/wheel-rate/leg-acc=`254.57/0.1947/0.30/-0.0391/-0.0044`、catastrophic 0，`model_3000.pt` SHA256 `2125b6f0...1b0342f`；逐轮核对 3188–3219 全部有限且 catastrophic 0，关键 3193/3195/3204 reward/value=`255.44/0.1667`、`254.49/0.1855`、`255.49/0.1938`，未复现旧 run 的巨额污染。
- `-0.05` 已继续通过 3400 与 4200 cache stages，并在每个边界后值守至少 100 轮；至 iteration 4301 reward/value/std=`255.79/0.1558/0.30`、catastrophic 0。精确 iteration 4000 reward/value/std=`257.16/0.1741/0.30`，`model_4000.pt` SHA256 `aed065e3...92cb6e0`；本次 `model_3500.pt` 72 tensors 全 finite、SHA256 `cff68c76...f7e1ad2`，不同于旧失败 run 的污染 checkpoint。
- `-0.05` 于 15:20 健康完成 iteration 4999：reward/value/std/wheel-rate/leg-acc=`256.17/0.1494/0.31/-0.0447/-0.0049`、catastrophic 0，训练耗时 8347.43 秒；`model_4999.pt` 4,441,781 bytes、SHA256 `8c847802...eceb21b`，72 tensors 全 finite。监督器登记 COMPLETE 后等待 20 秒，自动启动第三档 `-0.1`。
- `-0.1` run `2026-07-13_15-20-56_recovery_wheel_rate_m010_fresh_5k` 已于 15:20:48 启动，PID `64897`。runtime YAML/Reward Manager 精确确认 seed 42、4096 env、5000 iterations、24 steps、save interval 500、`resume=false`、weight `-0.1`、空 params；iteration 37 reward/value/std=`-509.09/29.8073/0.52`、catastrophic 0，监督器 warning streak 0。
- 按用户要求录制已完成的前两档最终 checkpoint。为避免 4096-env 训练与渲染争抢 GPU，先等 `-0.1` iteration 506 且 `model_500.pt` 落盘（SHA256 `2aef0731...c0e67c`），再 SIGSTOP 其进程组；监督器无 stale timeout，暂停期间未误判。两段 eval exit 0 后 SIGCONT，训练连续恢复并于 iteration 559 保持 reward/value/std=`259.56/0.2328/0.37`、catastrophic 0、warning streak 0。
- `-0.02/-0.05` 均使用 `model_4999.pt`、`SerialLeg-Recovery-v0`、seed 47、同一 `flat-basic` 6×4 秒 suite、translation-only 78° FOV 相机与 `--no-rerun`。两段均为 H.264 1280×720@50 FPS、1199 frames、23.98 秒、survival 1.0、1200 steps、0 non-finite；本地 MP4 为 `artifacts/recovery_eval/wheel-rate-m00{2,5}-model4999-recovery-eval.mp4`，抽帧确认机器人/场景/箭头可见。
- 用户准备关闭服务器后，先冻结第三档并盘点四个有效 run，再把 baseline、`-0.02`、`-0.05` 的全部 11 个现有 checkpoint，以及 `-0.1` partial 的 `model_0.pt/model_500.pt` 拉回本地；每组同时保留 `params/{agent,env}.yaml`、TensorBoard events、`git/se3_rl_lab.diff`，并备份训练/监督器日志、最终 status JSON 与监督器脚本。
- 本地归档位于 `artifacts/recovery_checkpoints/wheel_action_rate_sweep/`，共 59 files/226 MiB（其中 `SHA256SUMS` 覆盖 57 个数据文件，另含 README 和 manifest）。四组远端/本地逐文件 SHA256 diff 均为空，随后离线 `sha256sum -c SHA256SUMS` 为 57/57 passed。
- `-0.1` 在用户关机要求下有意停止：常规 SIGTERM 未使 Isaac Sim 退出后，冻结并 SIGKILL 进程组；监督器如实记录 phase `halted`、iteration 667、return code `-9`、reward/value/std/leg-acc=`259.9/0.1549/0.31/-0.0061`、catastrophic `0`。这不是训练数值异常；该 run 未完成，正式比较必须 fresh 重跑。最终复查远端 supervisor/train process `0`、GPU compute process `0`。

## 2026-07-13 wheel action-rate 三档配置与短训练 gate

- 按用户要求只修改 Recovery wheel action-rate penalty：默认 `-0.001→-0.02`，不增加 upright gate；腿 action-rate、action smoothness、动作映射、filter、PD、观测和其他 reward 均未改。
- 复用 train.py 现有 Hydra 通道运行 `env.rewards.wheel_action_rate.weight=-0.05/-0.1`，没有新增 CLI 参数或 task variant；每个 run 的 `params/env.yaml` 已验证精确保存实际权重。
- 更新 `scripts/test_recovery_contract.py`：默认 reward table 锁 `-0.02`，并新增 AST 契约确认 wheel term 无 `params`/gate。
- 本地 Ruff/format/py_compile/diff 通过；本地 pytest 在导入 torch 时进程 abort（exit 134，非断言失败）。同步两个目标文件到训练机后，相关 recovery/experiment/actuator/observation 回归为 `29 passed in 4.80s`，Ruff/format/diff 通过。
- 三档各完成 4096-env/1-update CUDA gate：`-0.02/-0.05/-0.1` mean reward 为 `-0.85/-0.86/-0.87`，wheel action-rate episode penalty 为 `-0.0003/-0.0006/-0.0013`，std 均 `0.50`、catastrophic 均 `0`、无 NaN/OOM；只证明配置与数值链路健康。
- 短 gate run 分别为 `2026-07-13_10-28-44_recovery_wheel_rate_m002_gate`、`10-29-28_recovery_wheel_rate_m005_gate`、`10-30-05_recovery_wheel_rate_m010_gate`。完整 fresh sweep 已在上述新条目中启动。

## 2026-07-13 服务器日志复核与抖动因果 A/B

- 用户提供服务器 endpoint 后，在本机 `~/.ssh/config` 恢复 `se3_rl_lab_gpufree` alias；连接确认远端 `gpufree-container`/RTX 4090 正常。endpoint/密钥未写入仓库。
- 读取 `/tmp/recovery_height_default_fresh_5k.log`、TensorBoard events、model4999 SHA 与既有 `/tmp/jitter_probe*`。最终日志为 reward `259.81`、action smoothness `-0.1783`、leg action-rate `-0.0012`、wheel action-rate `-0.0013`；训练从 iteration 1000 起长期接受约 `-0.16~-0.19` smoothness 代价。
- 新增临时 `/tmp/jitter_causality_probe.py`（不进仓库），先 warmup 300 steps，再做 policy/hold-all/hold-legs/hold-wheels；同时跑 startup domain randomization on/off。randomized 与 nominal 的 root-z/pitch 主峰分别约 `4.00/4.67 Hz`，nominal pitch-rate std `1.56 rad/s`，排除 seed-47 domain randomization 为主因。
- 冻结最近 50 拍平均动作：前 10 steps 仍约 `3.37°` 直立，pitch-rate std `1.262→0.323 rad/s`、root-z std `1.245→0.658 mm`、轮力矩均值 `2.499→0.530 N·m`，随后因失去反馈逐渐倾倒；证明恒定目标下 plant 振荡快速衰减，极限环由 policy 逐拍更新主动维持。
- 只冻结腿动作/目标后机器人保持直立，wheel action、root-z、pitch 仍同频约 `3.67 Hz`；只冻结轮动作时前 10 steps pitch-rate std 降至 `0.379 rad/s`，随后失去轮式平衡。主驱动因此定位到轮速度 policy，腿目标振荡属于耦合响应。
- model4999 站立稳态左右 wheel target 约 `22.7%/38.7%` 超过 `71.81 rad/s` 空载速度，wheel torque 约 `42.7%/48.0%` 采样大于 `3.6 N·m`；轮 policy 实际在用饱和式速度目标维持动态平衡。

## 2026-07-13 抖动根因源码复核

- 只读核对 `mdp/actions.py`、`mdp/rewards.py`、`recovery_env_cfg.py`、actor observations、SerialLeg actuator/YAML、eval camera/worker 与参考 recovery 配置；未修改生产源码。
- 现有 probe 与源码一致指向 actor–plant 闭环极限环：50 Hz policy 直接写腿位置目标，只有固定 1 个 5 ms physics step 延迟，无 rate limiter/low-pass；model4999 的 target delta RMS `0.204 rad/20 ms` 在 `Kp=60` 下对应约 `12.2 N·m` 的单拍比例力矩增量量级。
- 当前 leg action-rate 权重为 `-0.001`，比旧 flat 的 `-0.48` 弱 480 倍；smoothness 为二阶差分 `-0.03`。按 model4999 `4.67 Hz`、raw action delta RMS `0.666` 的近似正弦估算，leg action-rate/smoothness 未缩放代价约 `0.0018/0.0178`，不足以证明策略会偏好静态平衡。
- 当前 actor 是不做 observation normalization 的 feed-forward MLP；34D actor observation 没有 base linear velocity、wheel contact force 或 base height，这三项只在 critic 40D privileged observation 中。参考 recovery/discovery 使用 normalized GRU + 64-step rollout；该差异可能使 actor 依赖瞬时 joint/IMU/last-action 代理并形成相位锁定，但尚无同环境架构 A/B，不能写成已确认根因。
- 发现未排除的 eval 变量：worker 只关闭 actor observation corruption，仍运行 startup material、base mass/COM 与 actuator-gain randomization，且抖动 probe 只使用 seed 47 单环境。因此“随机化后的 actor–plant 闭环确有振荡”已确认，但名义 plant 的严重程度仍为 `UNKNOWN`。
- 下一步应先做同 seed nominal-vs-randomized plant A/B 和稳态 hold-action/hold-target A/B；本机没有当前 run checkpoint、MP4 或 raw telemetry，SSH alias `se3_rl_lab_gpufree` 在本机无法解析，未重跑模型。

## 2026-07-13 height-conditioned recovery 提交与推送

- 从同步的 `main@46edeee` 创建 `codex/height-conditioned-recovery`，明确排除未跟踪的 `.codex/` 可视化和 `artifacts/` MP4/PNG/metrics，只暂存 22 个源码、测试、文档与 handoff 文件。
- 提交 `8f5ee8e Complete height-conditioned recovery contract`：840 insertions、60 deletions，包含 height-conditioned default 完整 contract、yaw 大误差梯度、deterministic eval schedule/camera、eval corruption 修复及回归/交接记录。
- `git push -u origin codex/height-conditioned-recovery` 成功；分支跟踪 `origin/codex/height-conditioned-recovery`。用户只要求 commit/push，本轮未创建 PR。
- 提交前 `uvx ruff check` 全通过，所有变更 Python 文件 `py_compile` 通过，`git diff --check` 与 staged diff check 通过。本机轻量 `.venv` 缺少 `pytest/torch/numpy`，训练机 SSH 仍不可用，因此未重复 pytest；同一代码此前远端 pytest/CUDA gates 已记录通过。

## 2026-07-12 model2000/model4999 视觉与控制抖动因果诊断

- 用户确认 noisy/no-noise 两段 MP4 观感均“非常抖”，因此撤回“关闭 eval observation corruption 已解决视觉抖动”的推断。逐帧蓝色轮廓、背景网格与 telemetry 均显示约 4.5–5 Hz 主峰。
- production camera 每拍跟随 root x/y/z。相同 seed、相同前 50-step 物理轨迹仅把诊断 camera z 固定到 0.26 m 后，底部背景垂直逐帧位移 RMS `0.508→0.095 px`，约降 81%；生成 5.98 秒 H.264 诊断 MP4 `artifacts/recovery_eval/model_2000-height-default-xy-camera-diagnostic.mp4`。该实验未修改生产源码。
- 新建并清理临时 headless probe，记录 policy raw/processed action、leg/wheel target、joint state/effort、root pose/velocity 与逐 body contact。model2000 forward 稳态 actor/leg-target/root-z/contact 同频约 `4.67 Hz`；raw action/target delta RMS `0.533/0.152`，root-z std `1.899 mm`，pitch-rate std `1.418 rad/s`。
- 碰撞审计显示直立 baseline 仅左右轮接地，两轮法向力同相；底盘、腿和连杆无误触地。固定 restitution=0 后 root-z std `1.855 mm`。4–6 ms action delay 在 5 ms physics step 下恒定为 1 step；关闭后 root-z std `1.853 mm`。Kd `3→6` 将 leg qvel RMS `2.43→1.49 rad/s`，但 root-z std 仍 `1.887 mm`。三者都不消除极限环。
- fresh 训练健康完成 iteration 4999：reward 259.81、value 0.1753、std 0.33、`leg_dof_acc=-0.0044`、catastrophic 0；watchdog `COMPLETE`。最终 `model_4999.pt` SHA256 `c3aed3f72be660bd44a269df04be52ed2fd063ca316886ea720bac4cc31f3027`。
- 相同 probe 检查 model4999：forward root-z std `1.625 mm`、pitch-rate std `1.505 rad/s`、action/target delta RMS `0.666/0.204`，说明完整 5k 未消除抖动式动态平衡。参考 commit `93f6ba2` 的 PD `60/3`、wheel Kd `0.08`、4–6 ms delay、50 Hz control 与当前一致，且参考同样只有 reward 级 action rate/smoothness、无硬 low-pass。
- 本机临时 probe 脚本、raw frames 与 contact telemetry 已清理；保留用户可看的短诊断 MP4。远端 `/tmp/jitter_probe*` 与 `/tmp/se3_camera_z_diag` 清理时 SSH alias 突然无输出退出，是否删除成功未确认，重连后应补查；均为 `/tmp` scratch，不影响 run。production control/camera 未在本轮修改。

## 2026-07-12 model 2000 视频抖动诊断

- Telemetry 证明六场景 command 每 200 步内严格恒定，只在场景边界切换；排除 command 重采样抖动。baseline raw action 每拍 delta RMS 为约 0.40–0.58，腿 target 为 0.10–0.16 rad，抖动在进入 PD/碰撞前已存在；运动场景腿 action 有约 4.4 Hz 主峰。
- 固定 seed 短 A/B 的 stand steps25–49：baseline action/target/qvel/torque/contact delta RMS `0.2769/0.0597/0.4478/2.201/22.995`；no-delay `0.2784/0.0607/0.5188/2.047/17.656`；Kd=6 `0.2692/0.0591/0.3561/2.195/18.353`；zero restitution `0.2766/0.0596/0.4359/2.199/23.293`。
- 关闭 eval actor observation corruption 后为 `0.0642/0.0246/0.0729/0.404/8.120`，action/qvel/torque 分别约降 77%/84%/82%。根因是 eval worker 沿用训练配置 `enable_corruption=True`；尤其 scaled leg velocity noise `±1.5` 等价于原速度 `±6 rad/s`。参考仓库 play 明确用 `enable_corruption=not play`。
- 所有 `[DEBUG]`/临时 worker 字段、A/B 配置、checkpoint 副本、diag metrics/reports/logs 已删除；正式 worker 恢复并通过 Ruff，原 model2000 latest_result 已恢复。
- 用户授权重录后，在正式 eval worker 创建环境前设置 `env_cfg.observations.actor.enable_corruption=False`；训练 cfg 不变。新增静态回归，Ruff 与 experiment/recovery `18 passed`。同一 model2000 完整重录通过，产物 `model_2000-height-default-no-noise-*` 已同步本地，旧 noisy MP4 保留。

## 2026-07-12 height-conditioned default 完整迁移与 fresh 5k

- 将参考仓库 height-conditioned default 作为统一 contract 迁移：参考四连杆 8192/1024 点 LUT、per-env height cache、command resample 刷新、非-cache recovery reset 基准、action 零点、三个关节姿态 reward 和固定命令 eval 刷新均使用同一 4D policy default。
- settled-state cache rows 继续整行覆盖 root/policy/passive/wheel 状态，不强行改写为 height default；非-cache 随机化从当前 command height 对应腿型开始，随后重新求 passive joints 并执行 wheel clearance lift。
- 参考 0.20/0.22/0.26/0.30/0.32 m 输出逐点锁定，误差阈值 `2e-6 rad`；64-env mixed reset 与 4096-env/1-update CUDA gates 通过。
- 启动 fresh seed-42、4096-env、5000-iteration run `recovery_height_default_fresh_5k`；log `/tmp/recovery_height_default_fresh_5k.log`，run dir `2026-07-12_20-32-29_recovery_height_default_fresh_5k`。iteration 868 reward 251.18、value 0.2697、std 0.33、catastrophic 0。
- 部署远端独立 watchdog PID `29876`，每 30 秒更新 `/tmp/recovery_height_default_watchdog.status`；明确巨额 reward/value、catastrophic 扩散或 NaN/OOM/Traceback 时自动 SIGTERM 训练，避免污染继续写入 checkpoint。
- 对最新已落盘 `model_2000.pt` 运行完整 6×4 秒 eval 并录制 MP4；1199 frames/23.98 s/2,820,743 bytes，survival 1.0、vx/yaw RMSE 0.22453/0.37779、0 termination/non-finite。产物已同步到本地 `artifacts/recovery_eval/model_2000-height-default-*`；并行训练继续健康推进到 iteration 2299。

## 2026-07-12 recovery 污染源追踪（禁止兜底）

- 确认 PPO 直接污染项为 `leg_dof_acc`：它只覆盖 `lf0/l_drive_bar/rf0/r_drive_bar` 四个主动腿关节，3195 日志为 `-3.29e5`、3196 为 `-1.65e7`，后续峰值 `-9.37e20`；vertical/angular root velocity 项是次生污染。
- IsaacLab joint velocity reset 会同步 `_previous_joint_vel` 并将 joint_acc 清零；reward 又在物理步后、reset 前读取，因此巨峰是真实 PhysX velocity jump，不是 reset history 伪差分。
- 40k dataset 数值审计：root linear max 0.147 m/s、root angular max 0.346 rad/s、joint velocity <1 rad/s，全 finite，排除原始速度离群。
- dataset 中 fixed-tendon 坐标确有 MuJoCo 软限位残余越界（左最大 +0.00375 rad、右 +0.00233 rad），但 64+64 A/B 显示越界组不比刚好限内组更差；加入 interior 对照后各组均为约 10³ rad/s² 首步峰值，排除“越界本身”作为独立首因。
- 扫描全部 20k train cache rows，按真实 4 physics-substep 控制周期执行 zero delayed action：全部 finite，最大净 acceleration 854.16 rad/s²、joint velocity 16.34 rad/s、root linear/angular 0.766/4.056，0 个 catastrophic。排除任一 cache row 单独致炸。
- 用 model3000 重建 actor：deterministic mean 跑 3000 steps/12.3M transitions、Gaussian std 跑 4000 steps/16.4M transitions，均 0 catastrophic，reward abs max 约 2.38。说明静态 checkpoint、cache/reset、随机 action tail 单独不足；触发需要 PPO 继续更新、精确 RNG 或长时 solver/contact 历史之一。
- fresh seed-42、4096-env、保留 PPO 更新的探针在 iteration 476 可重复捕获 env 1587 严重事件：普通 reset 后 age 180、非 cache reset；`r_drive_bar_Joint=-625.29 rad/s`、`-101256 rad/s²`，`rf1_Link` 接触力 `7241 N`，passive wrapped error `2.50 rad`。
- 动作分布探针确认 `rf0` 最终 action `-18.62` 对应 mean `-17.74`、std `0.572`、z-score `-1.52`，不是 Gaussian 尾部。32-step 历史起点 age148 时 `lf0` mean 已达 `+17.90`；age165–179 的 `rf0` mean 又为 `-2.41,-3.36,-5.37,...,-17.74`，说明 actor 整体先离开物理动作域，异常随后转移至右腿。
- 上一拍 action 会通过 actor observation 的 `last_actions` 槽回灌并参与后续放大；但 mean 最初外飘早于已捕获窗口，且 age164→165 还伴随 leg velocity/base angular velocity 变化，因此当前证据不足以把 `last_actions` 定为唯一首因。
- action wrapper 的 `clip_actions=None`，ActionTerm 仅在 `±100` clip；`-18.62 × 0.25` 将 `rf0` 目标推至 `-4.378 rad`。这一不可实现的腿目标先打爆右闭链，`leg_dof_acc` 再把巨额有限负 reward 写入 PPO。
- 临时 diagnostic scripts 已从本地和远端清理；生产代码、reward/reset/termination/课程均未修改，正式训练未恢复。

## 2026-07-12 recovery 5k iteration 3195 级联崩溃

- PID `28338` 已退出，日志完整停在 iteration 3606；无 Python traceback/NaN check/OOM 文本。主机内存、磁盘和 GPU 当前正常，内核无本次 OOM/Xid，coredump 为空；最终退出信号 `UNKNOWN`。
- 日志定位首个连续异常：3192 正常；3193 `leg_dof_acc` 从约 `-0.006` 到 `-0.0659`；3194 reward 77/value loss 1.44e4；3195 reward `-1.11e7`、value loss `6.97e13`、catastrophic 0.0067；3204 catastrophic 0.101，之后长期约 0.4–0.6。
- 首因不是 std：3195 std 仅 0.36；也不是 3400 cache stage，故障早 205 iterations。cache 在 2600 起为 45%，精确的罕见物理触发样本/动作仍未知。clearance adjustment 不是充分解释，历史更大 lift 在正常期出现过。
- 级联机制已由源码顺序确认：IsaacLab `step` 先 `termination_manager.compute()`，再 `reward_manager.compute()`，之后 reset；Recovery 的 vertical/angular velocity 与 joint acceleration L2 项无 cap。catastrophic termination 可防 NaN，但不能阻止终止帧的巨额有限 reward 进入 PPO。
- `model_3000.pt` 是最后一个故障前 checkpoint；`model_3500.pt` 已污染。两者 actor/critic state tensors finite，3000 actor std param 0.410、3500 为 0.532，但 finite checkpoint 不等于健康策略。
- 尝试用 checkpoint smoke 做 postmortem：首次命令因 PowerShell 变量提前展开误传 `model_.pt`，已终止并清理；第二次 model3000 runner 在 180 秒内未完成，已终止清理，未作为证据。未修改代码、未恢复训练。

## 2026-07-12 Recovery yaw 大误差梯度语义

- 对照 `se3_wheel_leg_spring_add@93f6ba2`：当前与参考 Recovery-Discovery 原配置均为固定 `sigma=0.25` 的纯指数 yaw reward；“高 yaw 大误差保留梯度”来自同分支 flat reward 的 `sigma_cmd_scale=0.4`、`ratio_blend=0.2`。
- 按用户要求只迁移这两个 yaw tracking 语义；保留 Recovery term 名、权重 `1.5`、直立门控、其余 24 个 reward、command/PPO/reset/termination 不变。线速度 reward 仍使用 Recovery 的 adaptive pure-exp 语义。
- 新增纯函数 `angular_tracking_reward`：`sigma_eff=sigma*(1+scale*|cmd|)`，再混合 exponential 与比例项。`cmd=12/error=6` 回归锁定 reward≈0.1、error gradient `<-0.01`；旧固定 sigma exp 为 `exp(-144)`，float32 下近零。
- test-first RED 命中配置缺少两个参数；GREEN 为四组回归 `25 passed`，Ruff format/check 通过。64-env/8-step CUDA runtime gate 通过，reward/obs finite、`max_abs_reward=1.176`。
- 正式训练 PID `28338` 未停止；到 iteration 3100 为 std 0.35、mean reward 242.08、catastrophic 0。由于 Python 进程已在启动时加载旧 reward，该 run 不包含新语义；需要新进程/重新训练才能做有效 A/B。

## 2026-07-12 eval deterministic schedule bugfix

- 只修改 eval 链路：新增 `isaac_eval/schedule.py`，在 `gym.make` 前将 episode timeout 与 command resampling 设到完整 suite 时长加 1 秒之后；未修改训练 task、reward、command curriculum、reset 或 termination。
- 场景切换顺序改为“写入固定命令 → 刷新 policy observation → policy inference”，删除逐 step 重写命令的旧路径，避免边界第一步使用上一场景命令 observation。
- test-first 红灯确认 `ModuleNotFoundError`；实现后 experiment/recovery/actuator/observation 共 `24 passed`，Ruff format/check 通过。
- 用 `model_1000.pt` 重跑 6×4 秒完整 eval：1200 telemetry rows、0 termination、0 command mismatch（`abs_tol=1e-6`）、0 non-finite；vx/yaw RMSE 从受 timeout 污染的 `0.3206/0.4129` 降为 `0.2096/0.3345`。
- MP4 为 H.264 1280×720@50 FPS、23.98 秒、1199 frames，已覆盖同步到 `artifacts/recovery_eval/model_1000-recovery-eval.mp4`。并行训练 PID `28338` 未停止，验证后运行到 iteration 2671。

## 2026-07-12 eval camera-v2

- 用户反馈 yaw-relative camera 旋转观感不适；改为固定世界 eye offset `(0.0,-2.4,0.57) m`，eye/target 每帧只加相同 root translation，不再读取 root quaternion/yaw。
- 新增纯函数 camera geometry 模块与两项测试；水平 FOV 按角度精确乘 `1.3`，runtime 日志确认 `60.00°→78.00°`、focal length `18.148→12.939`。
- recovery/actuator/observation/experiment tests 共 `22 passed`，相关 Ruff check/format 与 diff check 通过。
- 完整重录 model_1000：H.264 1280×720@50 FPS、23.98 s、1199 frames、3.08 MB；yaw_left 13.0/15.5 s 抽帧的地面网格方向一致，机器人在固定世界视角内旋转，确认 camera 不随 yaw 转动。
- 新 MP4 覆盖本地 `artifacts/recovery_eval/model_1000-recovery-eval.mp4`；训练并行运行到 iteration 1650，std 0.42、mean reward 227.82、catastrophic/NaN/Traceback 0。

## 2026-07-12 model_1000 recovery eval MP4

- 当前 run 不存在 `model_999.pt`，按 RSL-RL save naming 使用对应的 `model_1000.pt`。
- 与 4096-env 训练并行完成 1-env/seed47、6 scenarios × 4 s eval；录制 H.264 1280×720@50 FPS、23.98 s、1199 frames、4.82 MB，无 eval Traceback/Error/NaN。
- metrics: score 49.432、survival 0.9992、vx RMSE 0.3206 m/s、yaw RMSE 0.4129 rad/s、non-finite 0；仅 yaw_right 发生 1 次 termination。
- MP4、metrics、report 和 6 s preview 已同步到本地 `artifacts/recovery_eval/model_1000-*`；抽帧确认机器人、相机与目标/实际速度箭头可见。
- 录制结束后正式训练到 iteration 1228，std 0.46、mean reward 219.13、catastrophic/NaN/Traceback 0。

## 2026-07-12 Recovery/Motor PR

- 创建分支 `codex/recovery-motor-model`，提交 `e506dda Implement recovery task and motor envelopes` 并推送到 `origin`。
- GitHub App 创建 PR 因 integration 403 失败，按发布流程使用已认证 `gh` CLI 成功创建 Draft PR [#9](https://github.com/am345/se3_rl_lab/pull/9)。
- PR 正文记录当前 5k progress（iteration 487、std 0.79、mean reward 140.69、无 NaN/Traceback/OOM）、旧 std 失控/reward 爆点、历史 PhysX NaN、电机固定 limit 问题和未跨过的长训练风险。
- 明确排除本地 `.codex/` 和 `artifacts/` 生成产物；reset dataset、USD、电机/recovery 代码、测试和文档均已纳入提交。
- 用户授权后将 PR 转 Ready 并 squash merge 到 `main`，merge commit `46edeee`；本地/远端 main 已同步，功能分支已删除。
- Merge 收尾时训练到 iteration 705，std 0.58、mean reward 189.30、catastrophic 0、无 NaN/Traceback，已跨过 iteration 650。

## 2026-07-12 删除 Recovery-Loco

- 按用户要求删除 `SerialLeg-Recovery-Loco-v0` Gym 注册、`RecoveryLocoEnvCfg`、`RecoveryLocoRewardsCfg`、三组 `_LOCO_*` 速度限制、两个 dense Smooth-L1 tracking reward 函数。
- 静态契约改为确认 loco task/dense terms 不存在；远端 recovery/actuator/observation 回归 `17 passed`，Ruff check/format 通过。
- 当前正式训练使用 `SerialLeg-Recovery-v0`，进程启动时已加载基础 recovery 配置，因此本次删除不改变其运行时环境；PR 前更新到 iteration 427、std 0.83、mean reward 87.22、catastrophic 0、无 NaN/Traceback。

## 2026-07-12 recovery 参考随机策略参数重启 5k

- 停止旧 `recovery_motor_tn_fresh_5k`：PID `22920` 最终约 iteration 907，mean std 约 2.96；进程与 GPU 占用已清理。
- 新增 `RecoveryPPORunnerCfg`，保持 MLP/24-step rollout 不变，对齐参考值 `init_std=0.5`、`entropy=0.00516`、`lr=3e-4`、`desired_kl=0.008`；Recovery 使用新配置，flat 保持原配置。
- 静态回归 `17 passed`，Ruff check/format 通过；4096-env/1-update runtime gate 显示 std 0.50、无 NaN/OOM，保存的 agent YAML 与目标参数一致。
- 启动 fresh 5k：run `recovery_ref_std_fresh_5k`，PID `28338`，日志 `/tmp/recovery_ref_std_fresh_5k.log`，run dir `2026-07-12_16-00-33_recovery_ref_std_fresh_5k`。iteration 108 时 std 0.75、catastrophic 0、无非有限值。

## 2026-07-12 fresh recovery 5k

- Preflight: RTX 4090 空闲（约 24 GB free）、数据盘剩余 28 GB、无残留训练进程。
- Gate: `SerialLeg-Recovery-v0`、4096 env、1 PPO update 通过；98,304 steps、30.7k steps/s、`catastrophic_state=0`、无 NaN/OOM。
- Formal run: fresh seed 42、4096 env、5000 iterations、`resume=false`、save interval 500；run name `recovery_motor_tn_fresh_5k`。
- Runtime: PID `22920`；日志 `/tmp/recovery_motor_tn_fresh_5k.log`；run dir `logs/rsl_rl/serialleg_flat_closed_chain/2026-07-12_15-28-33_recovery_motor_tn_fresh_5k`。
- Initial health: iteration 0–31 已运行，首轮约 29.9k steps/s、catastrophic 0、无 NaN/Traceback/OOM，ETA 约 4h34m。
- Later diagnosis: mean action std 由 1.01 单调增至约 2.96；iteration 727–733 出现巨额负 reward。用户授权后，该 run 已在约 iteration 907 停止并由参考随机策略参数的 fresh run 取代。

## 2026-07-12 YAML action-scale 单一来源

- Objective: 消除 YAML `40/3.71` 与实际 policy `0.25/45` 的矛盾。
- Changes: `robot_config.yaml` 改为 legs `0.25`、wheels `45.0`；`SerialLegDelayedActionCfg` 默认值通过 `SERIALLEG_CONTRACT` 读取，不再维护第二份数字；静态测试锁定 YAML→contract→action wiring；README 同步。
- Asset: YAML SHA 变化后重建 collision-only USD，磁盘 `--check` 报告 13 links/12 tree joints/2 loops/2 tendons/54 meshes/7102 faces/2 cylinders/0 visuals、质量 `12.72874553 kg`、大小 `536348 bytes`。
- Runtime: config probe 输出 `yaml 0.25 45.0` / `runtime 0.25 45.0`；64-env CUDA recovery 16-step gate 通过，reward/obs finite、passive/tendon error 0、wheel clearance 0.0010 m。

## 2026-07-12 电机扭矩—速度模型迁移

- Objective: 迁移 `se3_wheel_leg_closedchain_obs34` 的腿部四象限 DC motor 与轮部实测非线性 T-N 包络，不改 policy/action I/O、reward、reset 或 termination。
- Changed files:
  - `source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg_motors.py`: 新增共享 `MotorSpec`、DM-8009P 参数及 M3508+C620 14:1 的 12 点曲线。
  - `source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg_actuators.py`: 新增 IsaacLab `TorqueSpeedCurveActuator`，按当前关节速度分段线性插值并裁剪显式 PD 扭矩。
  - `source/se3_rl_lab/se3_rl_lab/assets/robots/serialleg.py`: 腿切换为 `DCMotorCfg`，轮切换为曲线 actuator，passive linkage 保持 implicit zero actuator。
  - `scripts/test_serialleg_actuators.py`: 新增曲线点、插值、正反转、四象限腿电机和 wiring/action 合同测试。
  - `README.md`: 记录显式 actuator、参数来源以及 YAML/action-scale 边界。
- Result: 远端 IsaacLab 实例化为 `DCMotor`/`TorqueSpeedCurveActuator`，定点裁剪与参考值一致；64-env CUDA recovery reset + 16-step random rollout 通过，无 non-finite。
- Follow-up: 新增 `scripts/smoke_serialleg_motor_envelopes.py`，在实际 runtime actuator 上全速域采样 801 点并与共享 `MotorSpec` 对照；腿/轮最大误差分别为 `5.836e-06/7.366e-06 N·m`。同时生成腿/轮 T-N 包络可视化，README 补充 gate 命令。
- Remaining risks: 尚未用新 dynamics 跑 4096-env PPO update 或正式从头训练；低速目标区仍处于轮曲线恒扭矩平台，跟踪改善幅度需实训评估。

## 2026-07-12 recovery locomotion finetune（已删除）

- 新增 recovery-loco task、固定实用速度范围与两个 dense tracking reward terms。
- 从原 recovery `model_1999.pt` 成功 resume；1-update runtime gate 后启动 1000-iteration finetune。
- 该独立任务、专用速度范围和 dense reward 已按用户后续要求从代码删除，不再是活跃训练路径。

## 2026-07-12 model_1999 recovery eval MP4

- 修正 eval worker 对 recovery reset 无 `pose_range` 参数的兼容性。
- 录制 H.264 1280×720@50 FPS、23.98 秒 MP4，抽帧确认 collision preview、相机与箭头可见。
- 将 MP4 和 metrics 从远端同步到 `artifacts/recovery_eval/`。

## 2026-07-12 确定性定位 recovery NaN

- 第二次正式 run 在 iteration 210 失败，推翻“wheel clearance 是 NaN 根因”的判断。
- 插桩复现到 env 2821 的完整 PhysX state 同步变 NaN，之前 raw policy action 达 627.8；contact force 仍 finite。
- 对照参考源码确认 recovery 保留 `catastrophic_state`；本仓库 timeout-only 测试和配置属于不完整迁移。
- 恢复 hard-error termination 后，同 seed 原始 400-iteration repro 通过；临时 debug 插桩已清理。

## 2026-07-12 recovery iteration-835 NaN

- 定位旧训练在 iteration 835、82,182,144 steps 后 reward NaN；dataset 尚未启用。
- 1024 env、iteration 650、1200 steps 的随机动作 std 1.0/9.1 均未复现。
- 参考 recovery 启用了 `align_root_height_to_wheels=True` 和最终 collision snap；当前迁移此前遗漏了 joint randomization 后的实际 wheel clearance 修正。
- 已在 `recovery_events.py` 增加 post-joint-reset wheel lift，并扩展 `smoke_recovery_reset.py` 的持续/策略/clearance 诊断能力。
- 已启动 fresh `recovery_full_2k_wheel_clearance`。

## 2026-07-11 — 完整reset运行时gate通过并启动正式2k

- 新增 `scripts/smoke_recovery_reset.py`；64-env和4096-env iteration-2000 gate均通过，4096 env cache比例25.3%、passive误差0、两个tendon-root position/velocity为0，16步reward/observation有限。
- 4096-env/100-iteration PPO soak完成9830400 steps，无NaN或异常退出；源码grep确认无runtime settle和debug钩子。
- fresh `recovery_full_2k` 已启动，日志 `/tmp/recovery_full_2k.log`；第4轮约58k steps/s、显存4.9 GiB、无NaN。

## 2026-07-11 — 完整迁移 recovery dataset/passive reset

- 重新核对最新 `se3_wheel_leg_spring_add@058b800`，确认正式 Recovery-Discovery 使用 `serialleg_closedchain_stair_v3_40k.npz`、五姿态混合、cache ratio curriculum和完整 joint reset。
- 新增四连杆 policy→passive position/velocity映射；标准 reset同步写4 policy、4 passive、2 wheel和2 virtual tendon-root；cache按名称将10-joint样本映射到当前12-joint资产。
- 复用40k NPZ（20k train/20k eval），cache比例为 iteration `1500/2000/2600/3400/4200` 的 `10%/25%/45%/60%/70%`；删除会污染PPO rollout的零动作settle。
- 本地 Ruff/diff通过，dataset/schema/passive映射测试 `5 passed`。服务器恢复后已同步全部核心源码与NPZ，5个文件本地/远端SHA一致；远端同一测试 `5 passed`。确认GPU空闲且无训练进程，未启动Isaac环境或训练。

## 2026-07-11 — 修复 recovery reset 后 PhysX NaN 并重启 2k

- 定位钩子两次捕获到单 env root/joint state 爆炸至 `1e13–1e23`，首个非有限 reward 分别为 `leg_dof_acc`/`tracking_lin_vel`；reward 不是根因。
- 迁移完整机器人包络 clearance；单独使用仍在第 52 轮复现。随后为 recovery reset 增加 40 physics-step 零动作 settle，并在 action term 中只对 settle env 清 raw/processed/FIFO。
- 带诊断与清理诊断后的两次 4096-env/100-iteration soak 均完成 983 万 steps，无 NaN；临时 `[DEBUG-recovery-nan]` 已移除。
- fresh run `2026-07-11_17-42-49_recovery_2k_settle` 已启动；第 18 轮正常，预计约 50 分钟。

## 2026-07-11 — 启动 recovery 2k fresh 训练

- 远端数据盘剩余 28 GB、RTX 4090 空闲后，从零启动 `SerialLeg-Recovery-v0`：4096 env、2000 PPO iterations、run `2026-07-11_16-52-22_recovery_2k`。
- 后台日志为 `/tmp/recovery_2k_20260711_165215.log`；第 19 轮约 84k steps/s、mean reward 45.43、显存约 4.5 GiB，预计约 40 分钟。

## 2026-07-11 — 新增 SerialLeg recovery 微调任务

- 注册 `SerialLeg-Recovery-v0`，继承 flat scene/action/observation/command/curriculum/PPO，只替换 recovery reward、reset 和 termination。
- `RecoveryRewardsCfg` 锁定 `se3_wheel_leg_spring_add` Recovery-Discovery 的 25 个 term 与权重；新增姿态/高度/稳定、腿轮动作正则、能耗、限位和接触实现，`diagnostics` 恒返回零。
- reset 按 iteration `0/300/650/1000/1400` 从 `±15°` 扩展到全姿态，并随机化 root xy/yaw/线角速度；termination 只保留 timeout。
- 更新 README、实验工具链文档和 run manifest reward profile；新增 `scripts/test_recovery_contract.py`。
- 远端 CUDA 完成 1 env/24 steps/1 PPO update；6D action、34D/40D observation、25 reward 与 timeout-only termination 均成功实例化并执行。

## 2026-07-11 — eval 录制相机跟随机器人

- eval worker 新增逐控制步相机更新：以机器人 root yaw 旋转侧后方 offset，保持约 `2.4 m` 横向距离和 `0.57 m` 高差，target 始终指向 root。
- 1 秒 × 6 scenarios 短测中对 forward 段 1.10s/1.90s 抽帧，机器人始终位于画面中央附近而地面网格发生相对移动；随后完整 24 秒 MP4/RRD 重录并覆盖本地交换目录。

## 2026-07-11 — 放大 eval 速度 debug_vis 箭头

- 将目标/实际速度箭头基准 scale 从 `(0.45, 0.06, 0.06)` 放大到 `(1.0, 0.18, 0.18)`，速度长度倍率从 `2.0` 提高到 `3.0`，离机器人高度从 `0.18 m` 提高到 `0.35 m`。
- 先用 0.5 秒短测检查，再完成 4 秒 × 6 scenarios 重录；抽帧确认绿色/蓝色箭头在 1280×720 画面中清晰可辨，最终 MP4/RRD 已覆盖本地交换目录版本。

## 2026-07-11 — 修复 debug-vis MP4 中机器人外壳静止

- Diagnosis: telemetry 和新增的 `base_world_x/y` 证明策略与物理刚体正常移动；问题只发生在 render-only collision preview。副本原先作为 replicated articulation body prim 的子节点，未可靠继承 tensor-driven body transforms，因此视频里的外壳停在初始位置。
- Fix: preview 改为独立 world-space Xform 树，保存每个 body 的 transform op，并在 rollout 每步从 `robot.data.body_pos_w/body_quat_w` 显式同步；不修改 collision-only USD，也不参与物理。
- Result: 0.5 秒短测中前进段 0.55s/0.95s 抽帧确认外壳位置和姿态均变化；随后完整重录 4 秒 × 6 scenarios 的 MP4/RRD 并复制到本地交换目录。

## 2026-07-11 — eval MP4 增加速度 debug_vis

- `VelocityHeightCommand` 按 IsaacLab marker 合同新增绿色目标速度与蓝色实际速度箭头，默认训练不开启；eval worker 显式启用。
- 为稳定录制 marker，eval-only 关闭 Fabric、固定 reset x/y/yaw=0 并使用侧视相机；训练仍保留 Fabric 和随机 reset。
- 完整 24 秒 debug-vis MP4/RRD/metrics 已复制到 `D:\RoboMaster\se3_checkpoint_exchange\model_499_flat_basic_24s`，抽帧确认箭头可见。

## 2026-07-11 — model_499 完整 flat-basic 录制

- 使用 six-scenario、每场景 4 秒的完整 eval 录制 `model_499.pt`；生成 23.98 秒/1199 帧/1280×720 MP4 与同 rollout 的 334KB Rerun。
- MP4、RRD、metrics 和 Markdown 报告已复制到本机 `D:\RoboMaster\se3_checkpoint_exchange\model_499_flat_basic_24s`，便于直接查看和交换。

## 2026-07-11 — finetune 前两阶段实验工具链完成

- Lifecycle: 新增 `se3rl` Python CLI，覆盖 train/resume/play/eval/record/runs/compare；run resolver 支持 path/name/唯一子串和 latest/best/iteration checkpoint，manifest/status 持久记录 Git/合同/训练/评估状态。
- Isaac Eval: 独立 worker + `flat-basic` 六 scenario；collision-only robot 从 54 meshes/2 cylinders 创建 render-only copies，自动输出 MP4、metrics、逐步 telemetry、context 和 latest result，不改物理 USD。
- Diagnostics: 同一次 rollout 生成 Rerun `.rrd`、单 checkpoint Markdown 和 compare report；统一 score 更新 best checkpoint。Rerun 固定 0.20.3，因 0.31.4/NumPy 2 与 IsaacLab NumPy `<2` 冲突。
- Runtime gates: 64-env CLI train/1 update 通过并生成 manifest/status；model_499 完整 eval 生成全部产物，抽帧确认机器人可见；pure tests `3 passed`、Ruff/format/uv lock/diff checks 通过。
- Docs/scope: 新增 `docs/experiment_tooling.md` 并更新 README；未实现 Viser/MuJoCo sim2sim，未修改资产/YAML/USD，未开始 legacy reward finetune。

## 2026-07-11 — collision-only USD 策略回放可视化

- Play CLI: `scripts/rsl_rl/play.py` 新增 `--show_colliders`；环境创建后将 PhysX `SETTING_DISPLAY_COLLIDERS` 设为 `2`（All），使 collision-only SerialLeg 在普通策略回放窗口中可见。
- Runtime: 关闭旧的不可见 play，使用 `DISPLAY=:20`、1 env、CUDA 和 `model_499.pt` 重启；日志确认 collider visualization 与 checkpoint 加载，Isaac Sim GUI 常驻 PID `6622`。
- Docs/validation: README 增加 collision-only play 命令和说明；远端 Ruff check/format 通过。

## 2026-07-11 — 4096-env/500-iteration 平地训练

- Runtime: 默认 PhysX capacity、4096 environments 完成 500 PPO iterations/49,152,000 steps，训练约 `470.93s`，最终迭代吞吐约 `110,765 steps/s`；运行中显存观测约 4.65 GiB，无 OOM 或异常退出。
- Learning result: mean reward 从启动 gate 的 `0.19` 增至最终 `26.30`，最终 episode length `985.91/1000`；termination time-out/bad-orientation/base-contact 分别为 `0.9981/0.0016/0.0005`，线速度/偏航 tracking reward 为 `0.9382/0.4432`。
- Artifact/scope: 保存 `model_499.pt`。500 轮仅到 velocity curriculum stage 1，push stage 仍为 0，因此可判定已学会当前课程范围的稳定平地运动，不能声称已通过最终高速范围、push robustness、长回放闭链 residual 或 sim2sim。

## 2026-07-11 — 4096-env CUDA 默认容量短训练通过

- Preflight: 远端 RTX 4090 空闲（约 24 GB 可用），数据盘剩余 29 GB，无并行训练进程；项目 clean `main@efa13d9`。
- Runtime: 使用默认 PhysX capacity 直接启动 4096 environments，完成 24 steps/env、总计 98,304 samples 和 1 PPO update，退出 0；吞吐约 `35,871 steps/s`，生成约 4.44 MB `model_0.pt`。
- Scope: 证明 GPU 空闲时 4096-env 默认容量可启动并完成短训练；未采集运行中峰值显存，也未完成多 iteration、push curriculum、长 rollout、termination 分布趋势或 fixed-tendon enabled/disabled A/B。

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
