# Agent Session Prompts

## New Window Startup

```text
确认项目规则已加载，然后读取 AGENT_HANDOFF.md，并按其中的 Recovery Reading Order 恢复上下文。规划前至少读取 .agent-handoff/snapshot.md、.agent-handoff/risks.md 和 .agent-handoff/backlog.md。

恢复当前目标、状态、下一步、活跃文件、阻塞、验证注意事项，以及需要检查的源码文件。之后只读取任务相关文件。任务过程中，目标、决策、改动文件、验证、风险、阻塞或下一步变化时，更新最小相关的 .agent-handoff 文件。最终回复前完成 handoff 收尾。默认使用中文维护文档；文件名、路径、命令、代码符号和 UNKNOWN 保持原样。
```

## Continue Specific Task

```text
Continue this task: <specific task>.

把这视为明确要求继续执行。不要回答 "No response requested."。先说明你认为上一步是什么，识别下一个具体动作，然后继续。如果上下文不足，先从 AGENT_HANDOFF.md 和必需的 .agent-handoff 文件恢复，再行动。

先读取 AGENT_HANDOFF.md，然后读取 .agent-handoff/snapshot.md、.agent-handoff/risks.md 和 .agent-handoff/backlog.md。检查任务相关源码文件。维护多文档 handoff：开始时更新 snapshot，做出长期选择时更新 decisions，文件变化时更新 work-log，运行或跳过检查时更新 validation，后续事项或未知项变化时更新 risks/backlog。默认使用中文维护文档。
```

## Closeout

```text
结束本轮前，更新多文档 handoff：刷新 .agent-handoff/snapshot.md，更新 .agent-handoff/work-log.md，记录 .agent-handoff/validation.md，更新 .agent-handoff/backlog.md 和 .agent-handoff/risks.md，并删除或重写过期状态。然后报告改了什么、验证了什么、还剩什么。
```

## Handoff Quality Review

```text
审查并直接修复多文档 handoff，让新 Agent 可以接手。检查 AGENT_HANDOFF.md 是否只是索引，snapshot 是否当前且简短，下一步是否具体，路径是否可定位，决策是否有原因和证据，验证是否已记录，并删除过期、矛盾、猜测性或聊天记录式内容。默认使用中文维护文档。
```
