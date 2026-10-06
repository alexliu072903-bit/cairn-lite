# History and design rationale

## 起点

我们最初研究的是
[iBlinkQ/project-cairn](https://github.com/iBlinkQ/project-cairn)。

它指出了一个真实问题：项目持续一段时间后，最有价值的知识经常留在
Agent 会话里——为什么做出某个决定、尝试过什么、什么结论被推翻、当前
边界是什么。

一旦切换会话或 Agent，这些知识就很难继续利用。

原项目提供了一个有价值的方向：

```text
局部观察 → 项目结论 → 可复用知识 → 外部知识库
```

但我们没有直接安装，而是先追问：

1. 它是 Agent Memory，还是项目知识协议？
2. 它能否跨 Codex、Claude 等不同 Agent 生效？
3. 会不会让 `AGENTS.md`、`CLAUDE.md` 越来越臃肿？
4. 会不会产生第二套 Product Frame 或 PRD？
5. 不想用了，能不能完整移除？
6. 如何证明它真的完成了跨 Agent 交接？

## 1. 从 Agent 私有记忆转向共享项目文件

如果知识只存在于 Claude 或 Codex 自己的会话记录里，它仍然属于单个
Agent：

```text
Claude conversation ≠ Codex conversation
```

真正能跨 Agent 的内容必须存在于双方都能访问的介质中。

我们选择的不是数据库，也不是某个厂商专用的 Memory API，而是项目目录
里的普通 Markdown 文件：

```text
Agent A
   ↓
shared project files
   ↑
Agent B
```

由此形成第一个核心判断：

> Cairn Lite 不让不同 Agent 共享内部记忆；它让不同 Agent 通过相同项目
> 文件恢复相同的判断、证据和边界。

普通文件是透明的、可审查的、Git 友好的，也不会锁定某一个 Agent 平台。

## 2. 把入口改成薄路由层

最初最大的顾虑之一，是 `AGENTS.md` 和 `CLAUDE.md` 会随着项目积累不断
膨胀。

如果把每个决策、失败记录和背景材料都塞进入口文件，会出现三个问题：

- 每次任务都加载大量无关信息；
- 真正重要的规则被历史内容淹没；
- Agent 的上下文成本持续增加。

因此 Cairn Lite 使用薄入口：

```text
AGENTS.md
CLAUDE.md
.cairn/
  PROTOCOL.md
  config.json
cairn/
  LOG.md
  topics/
    <topic>.md
```

`AGENTS.md` 只告诉 Agent 去哪里读取；`CLAUDE.md` 只导入同一份入口；
完整协议保存在 `.cairn/PROTOCOL.md`；`LOG.md` 只做索引；topic 保存单个
主题的当前结论和演变。

Agent 默认只读取：

1. 协议；
2. LOG 最新 5 条；
3. 当前任务相关的 topic。

它不会默认加载整个 `cairn/`。

所以 Cairn Lite 不是把更多内容喂给 Agent，而是为 Agent 提供一条最短的
上下文恢复路径。

## 3. 不创建第二套事实源

项目里已经有不同类型的权威文件：

- Product Frame 决定产品方向和边界；
- PRD 描述交付需求；
- 代码和 Schema 描述实际实现；
- 任务系统描述执行状态。

如果 Cairn Lite 再保存一份相同内容，它很快就会与正式文档冲突。

我们因此划定职责：

> 正式文档保存“当前是什么”；Cairn Lite 保存“为什么变成这样，以及这个
> 判断如何被验证”。

Cairn Lite 可以指向权威来源，但不能复制或替代它们。

只有满足以下任一条件，才应该写入：

- 产品或技术决策发生变化；
- 失败原因或修复结果得到验证；
- 既有结论被推翻或显著收窄；
- 某个已验证模式可能在其他项目复用。

普通进度、文件列表、会议流水、未经验证的猜测、个人数据和密钥都不应该
进入 Cairn Lite。

## 4. 保存判断的演变，而不只是最终答案

普通文档通常只保留最新版本，但 Agent 交接还需要知道：

- 原来如何判断；
- 什么证据改变了判断；
- 当前结论为什么成立；
- 哪些部分仍然只是 hypothesis。

每个 topic 因此采用固定契约：

1. Current judgment
2. Evidence
3. Boundaries
4. Evolution
5. Sources
6. Validation log

当结论变化时，Current judgment 可以更新，但旧判断和改变原因必须进入
Evolution，不能被静默删除。

这使 Cairn Lite 成为一条可追溯的项目判断轨迹，而不是活动日志。

## 5. 从第一天开始保证可移除

一个项目级协议如果安装容易、卸载困难，就会成为基础设施负担。

第一轮验证没有改造真实项目，而是创建了完全隔离的试验目录：

```text
/path/to/cairn-pilot
```

试验期间：

- 不修改现有项目；
- 不写入 Obsidian、飞书或 Notion；
- 不依赖外部服务；
- 不产生全局配置；
- 所有变化都限制在一个目录内。

正式 CLI 延续了这个原则：

- 现有文件只追加带边界标记的区块；
- 已存在的 Cairn 文件不会被覆盖；
- 重复执行 `init` 不产生重复内容；
- 删除 Cairn 目录和标记区块即可卸载。

## 6. 区分 Agent 与具体运行入口

验证早期，我们误用了 Claude CLI，但实际使用场景是 Claude Desktop。

这个纠正暴露了一个重要事实：“支持 Claude”或“支持 Codex”并不够精确。
不同运行入口选择目录、加载指令和授予权限的方式不同：

```text
Claude Desktop Code
Codex Desktop
Claude Code CLI
Codex CLI
other file-capable agents
```

Cairn Lite 只定义公共文件协议。每个入口如何选择同一个 primary folder，
需要单独说明和验证。

## 7. 设计可证伪的跨 Agent 测试

第一次完整测试遵循冷启动原则：

1. Codex 创建一个未写进后续提示词的 `pilot_id`；
2. Claude Desktop 在新会话中只依靠项目文件恢复它；
3. Claude 把读取结果写入 topic 和 LOG；
4. 新 Codex 任务不读取 Claude 会话，只读取项目文件；
5. Codex 成功看见 Claude 的更新；
6. Claude 写入随机 6 位验证码，Codex 再次从文件中读取。

这证明了两个 Agent 可以借助共享文件传递彼此会话中未知的信息。

但我们随后发现：

```text
Claude working directory:
  /path/to/cairn-pilot

Codex working directory:
  /path/to
```

Codex 能读到文件，是因为提示词提供了绝对路径，而且 pilot 位于其可访问
的父目录中。这只证明了文件可访问，还没有证明项目规则自动生效。

因此最终测试增加了三项检查：

```text
primary folder
working directory
automatically active AGENTS.md
```

只有三项都指向同一个项目根目录，才算通过。

最终验证确认：

- Claude 与 Codex 使用同一项目目录；
- 双方可以读写同一组 Cairn 文件；
- 新会话可以从文件恢复历史；
- Codex 自动发现项目级 `AGENTS.md`；
- 交接不依赖复制上一段对话。

## 8. 最终形成的 Cairn Lite

Cairn Lite 不是自动记住所有内容的 Memory 系统，而是一个受约束的项目
学习层：

```text
进入项目
  ↓
读取薄入口
  ↓
查看最近变化
  ↓
按需读取相关 topic
  ↓
完成任务
  ↓
仅在产生 material change 时更新
```

它主要解决：

- 跨 Agent 交接；
- 跨会话恢复；
- 项目判断不随聊天消失；
- 结论变化可以追溯；
- 用户不必重复补充项目背景；
- 不同 Agent 不必重新探索已验证的问题。

它不解决：

- Agent 私有记忆同步；
- 不同设备间自动同步；
- 不同项目副本之间的自动合并；
- 自动判断所有内容是否值得沉淀；
- 正式产品文档管理；
- 未经确认写入外部知识库。

## 9. 开源定位

Cairn Lite 不应该宣传成 Universal AI Memory。

更准确的定位是：

> A portable project-context protocol for handing off decisions, evidence,
> and boundaries across AI agents.

它的价值不在于存储更多，而在于：

- agent-agnostic；
- plain files；
- human-readable；
- Git-friendly；
- 按需加载；
- 不污染正式文档；
- 随时可移除；
- 结论有证据和演变记录。

第一版因此只提供本地协议、验证工具和跨 Agent 测试。外部知识库同步不在
V1 范围内，因为它会过早引入权限、覆盖、冲突和回滚问题。

## 10. 从项目笔记转向交接单（2026-10）

2026-10-06，我们用交接单试跑了四件真实工作（一个 Skill 的 v1、Cairn Lite 自己、
AirJelly 的两个功能），发现两件事。

第一，四件工作里，项目笔记（`cairn/LOG.md` 和 `cairn/topics/`）一次都没有用到；「被确认的
决定及其演变」由另一个工具 [cairn-context](https://github.com/alexliu072903-bit/cairn-context)
承担，而且它放在个人的私有仓库里，比放在项目目录里更合适。两者重叠，会让
Agent 不知道该写在哪里。

第二，真正反复出现的成本，不是「Agent 忘了项目背景」，而是人在计划方和执行方
之间来回转述：贴提示词、复制进度、转达问题、再说一句「继续」。

所以 Cairn Lite 重新定位为一件事：

> 让两个 Agent 通过同一张交接单协作。计划方写目标、边界和验收；执行方复述、
> 执行、记录，卡住时把问题写回同一个文件。

项目笔记功能被移除。分工变成：

- **cairn-context**：长期决定，跨任务、跨项目，经人确认才写入。
- **Cairn Lite**：一件工作从派出去到做完的过程，做完即结束，默认不进 Git。

前面几节记录的薄入口、可移除、不创建第二套事实源、可证伪的跨 Agent 测试，
这些原则都保留了下来，并直接用在交接单上。
