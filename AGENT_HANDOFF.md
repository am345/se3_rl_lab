# Agent Handoff Index

> 本仓库持久 Agent 接力记忆的入口。
> 先读本文件，再按下面的 Recovery Reading Order 读取需要的状态文件。

## Maintenance Contract

- 保持本文件简短。它是索引和恢复路线，不是工作日志。
- 当前任务状态写入 `.agent-handoff/snapshot.md`。
- 长期事实、决策、验证、待办、风险和归档写入下面列出的专用文件。
- 所有内容必须基于事实和仓库证据；不确定信息标为 `UNKNOWN`。
- 不写入密钥、凭据、长日志、完整代码块或聊天记录转储。
- 非平凡任务最终回复前，更新相关 `.agent-handoff/` 文件。
- 默认使用中文维护接力文档；文件名、路径、命令、代码符号和 `UNKNOWN` 保持原样。

## Handoff Layout

- `.agent-handoff/snapshot.md`: 当前目标、状态、下一步、活跃文件、阻塞和开放问题。
- `.agent-handoff/workspace.md`: 仓库地图、入口、测试命令、文档和稳定项目背景。
- `.agent-handoff/decisions.md`: 重要决策及其原因和证据。
- `.agent-handoff/work-log.md`: 最近仍有操作价值的工作日志。
- `.agent-handoff/validation.md`: 验证命令/检查、结果和注意事项。
- `.agent-handoff/backlog.md`: 待处理工作和后续事项。
- `.agent-handoff/risks.md`: 风险、阻塞、未知项和需要用户/来源确认的信息。
- `.agent-handoff/archive.md`: 压缩后的旧历史，正常启动时不需要读取。

## Recovery Reading Order

1. 读取本文件。
2. 读取 `.agent-handoff/snapshot.md`。
3. 读取 `.agent-handoff/risks.md`。
4. 读取 `.agent-handoff/backlog.md`。
5. 只有当前任务需要验证状态时，读取 `.agent-handoff/validation.md`。
6. 只有要修改架构、行为、依赖或既有决策时，读取 `.agent-handoff/decisions.md`。
7. 只有需要项目定位、命令、入口或子项目边界时，读取 `.agent-handoff/workspace.md`。
8. 只有需要最近实现细节时，读取 `.agent-handoff/work-log.md`。
9. 只有明确需要旧上下文时，读取 `.agent-handoff/archive.md`。

## Current Pointer

- Last updated: 2026-07-10
- Workspace root: `/home/am345/se3_rl_lab`
- Current state file: `.agent-handoff/snapshot.md`
- Primary next-action source: `.agent-handoff/snapshot.md`
- Risk source: `.agent-handoff/risks.md`
- Backlog source: `.agent-handoff/backlog.md`

## Project Rule Targets

- Codex 项目规则: `AGENTS.md`
- Claude Code 项目规则: `.claude/CLAUDE.md`

## Closeout Rule

非平凡任务最终回复前，更新相关文件：

- 总是更新 `.agent-handoff/snapshot.md`。
- 文件或任务状态变化时，更新 `.agent-handoff/work-log.md`。
- 运行或有意跳过检查时，更新 `.agent-handoff/validation.md`。
- 做出长期决策时，更新 `.agent-handoff/decisions.md`。
- 后续事项、阻塞、风险或未知项变化时，更新 `.agent-handoff/backlog.md` 和 `.agent-handoff/risks.md`。
