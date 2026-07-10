<!-- AGENT_HANDOFF_PROTOCOL:START -->
# Codex Agent Handoff Protocol

Layout: multi-document

## Required Startup Routine / 必需启动流程

规划或编辑文件前，读取：

1. `AGENT_HANDOFF.md`
2. `.agent-handoff/snapshot.md`
3. `.agent-handoff/risks.md`
4. `.agent-handoff/backlog.md`
5. 当前任务需要时，再按 `AGENT_HANDOFF.md` 的 Recovery Reading Order 读取其他 `.agent-handoff/` 文件
6. 与用户当前请求直接相关的源码文件

把接力文件当作连续性记忆；修改行为前必须从源码验证实现细节。

## Default Documentation Language / 默认文档语言

默认使用中文维护 handoff 文档、项目规则和 session prompts。文件名、路径、命令、代码符号、状态 token（例如 `UNKNOWN`）以及精确输出保持原样。用户明确要求其他语言时，以用户要求为准。

## Default Implementation Standard / 默认实现标准

非平凡开发任务默认以生产/商业级质量为目标，而不是最低可用实现。优先选择稳健、可维护的方案，考虑必要验证、运行时行为和边界情况，并清楚报告已测试和未测试内容。范围保持与用户请求一致；不要添加无关功能或推测性抽象。

## Stable File Reading Protocol / 稳定读文件协议

为避免 Read 工具行号或 offset 漂移：

1. 普通文件查找、内容搜索和读取优先使用专用搜索/读取工具。
2. 读取大型或易变文件前确认文件大小，必要时使用行数统计或定向搜索。
3. 先搜索精确目标，再读取目标附近的小范围内容。
4. 除非已知文件很小，Read 范围不要超过 240 行。
5. 如果 Read 返回意外空输出、offset 警告、过期片段、行号不一致、`file is shorter than the provided offset`，或 Read 后 API 终止，立即停止继续用 Read 分页读取该文件。
6. 将 Read `offset` 视为行号，不是字符偏移。不要重试同一个越界 offset，也不要通过加零或粗略大 offset 猜测。如果工具报告文件有 N 行，后续 Read offset 必须在 `0..N` 内。
7. Read offset 失败后，用针对章节/标题/符号的 `Grep` 重新锚定，或读取 offset `0` 等已知有效小范围；确认行号后再读取附近小范围。
8. Read 不可靠时，使用 shell 验证命令，如 `wc -l`、`rg -n`、`sed -n '<start>,<end>p'`，并给路径加引号；范围保持小，相关时在验证记录中说明 fallback。
9. 将只读 shell 检查命令（`wc`、`rg`、`grep`、`sed -n`、`ls`、`pwd`，以及非变更的 `git status`/`git diff`/`git log`/`git ls-files`）视作安全查询操作。项目设置中应尽量预授权，避免源码验证反复要求手动批准。
10. 不要基于不确定 offset 提议或编辑代码；先用搜索结果重新锚定。

## Continuation Recovery Guard / 继续请求恢复保护

如果用户说 `continue`、`继续`、`Continue from where you left off.` 或等价继续请求，应视为明确要求恢复任务。不要回答 `No response requested.`，也不要静默停止。先说明最后已知目标和下一个具体动作，再继续。如果上下文不足，先从 handoff 文件和任务相关源码恢复。

## Durable Handoff Memory / 持久接力记忆

本仓库使用多文档持久接力记忆：

- `AGENT_HANDOFF.md`: 索引和恢复路线
- `.agent-handoff/snapshot.md`: 当前目标、状态、下一步、活跃文件、阻塞和开放问题
- `.agent-handoff/workspace.md`: 仓库地图、入口、命令和稳定上下文
- `.agent-handoff/decisions.md`: 带原因和证据的长期决策
- `.agent-handoff/work-log.md`: 近期仍有操作价值的工作
- `.agent-handoff/validation.md`: 验证命令/检查及结果
- `.agent-handoff/backlog.md`: 待处理工作
- `.agent-handoff/risks.md`: 风险、阻塞、未知项和待确认事项
- `.agent-handoff/archive.md`: 压缩后的旧历史

维护最小相关文件。不要把所有状态都塞进 `AGENT_HANDOFF.md`；它只是索引。

## Handoff Size Discipline / 接力文档大小纪律

- 保持 `AGENT_HANDOFF.md` 简短；它是索引。
- 保持 `.agent-handoff/snapshot.md` 简短、当前、面向行动。
- `.agent-handoff/work-log.md` 只保留近期且仍相关的工作。
- 优先更新现有条目，避免追加重复或矛盾记录。
- 过期长历史移动到 `.agent-handoff/archive.md`。
- 在未中断的连续聊天中，仅在压缩、恢复、不确定或任务变化后重读相关接力文件。

## Mandatory Closeout Protocol / 强制收尾协议

非平凡任务最终回复前，无需等待用户要求，更新相关接力文件。

最低要求：

- 刷新 `.agent-handoff/snapshot.md` 的当前目标、状态、下一步、活跃文件、阻塞和开放问题。
- 文件或任务状态变化时，添加或更新 `.agent-handoff/work-log.md`。
- 对已运行或有意未运行的命令/检查，添加 `.agent-handoff/validation.md` 记录。
- 在 `.agent-handoff/decisions.md` 记录长期决策。
- 后续事项、阻塞、风险或未知项变化时，更新 `.agent-handoff/backlog.md` 和 `.agent-handoff/risks.md`。
- 删除或重写会误导下一个 Agent 的过期状态。

如果任务只是对话且项目状态未变化，则无需更新文件。

## Work Discipline / 工作纪律

- 不要假设当前活跃子项目；从用户请求、handoff 文件和仓库证据推断。
- 优先采用现有项目约定，而不是新抽象。
- 编辑前先读文件。
- 编辑范围限定在当前任务内。
- 未明确要求时，不修改生成的依赖目录。
- 不回滚用户或其他 Agent 的无关改动。
- 如实记录验证。未运行测试或检查时，在 handoff 文件和最终回复中说明。

## Session Closeout Checklist / 会话收尾清单

最终回复前，更新相关 `.agent-handoff/` 文件，写明最终任务状态、改动文件、运行的命令/检查及结果，以及剩余风险、阻塞、开放问题或下一步。
<!-- AGENT_HANDOFF_PROTOCOL:END -->
