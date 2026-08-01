# Cairn Lite

[English](README.md) | [简体中文](README.zh-CN.md)

**一个用于 AI Agent 之间交接的可移植项目上下文协议。**

Cairn Lite 让 Codex、Claude 和其他能够访问文件的 Agent，通过一组简洁的
Markdown 文件恢复相同的项目判断、证据和边界。

它是一个透明、Git 友好、由你掌控的项目学习层。

> 当前状态：实验阶段。文件格式已经可用，但在 1.0 前仍可能调整。

## 为什么需要它

Agent 的会话彼此隔离，但项目知识不应该被困在某一次会话里。

Cairn Lite 为不同 Agent 提供同一条上下文恢复路径：

```text
进入项目
  → 读取薄入口规则
  → 浏览最新 5 条日志
  → 只打开当前任务相关的 topic
  → 只记录重要变化
```

这样可以减少重复的上下文交接，同时避免把 `AGENTS.md` 或 `CLAUDE.md`
变成不断膨胀的记忆仓库。

## 安装

需要 Python 3.9+。

```bash
pipx install git+https://github.com/alexliu072903-bit/cairn-lite.git
```

本地开发：

```bash
git clone https://github.com/alexliu072903-bit/cairn-lite.git
cd cairn-lite
python3 -m pip install -e .
```

## 快速开始

在已有项目中初始化 Cairn Lite：

```bash
cd /path/to/your-project
cairn init
cairn validate
cairn status
```

`cairn init` 采用追加式写入，并且可以安全地重复执行：

- 创建缺失的 Cairn 文件；
- 在已有 `AGENTS.md` 中追加带边界标记、可移除的规则区块；
- 在需要时向已有 `CLAUDE.md` 追加 `@AGENTS.md`；
- 不覆盖任何已有项目规则或 Cairn 文件。

可以先预览所有变化：

```bash
cairn init --dry-run
```

## 生成的目录结构

```text
AGENTS.md                    薄入口规则
CLAUDE.md                    导入 AGENTS.md
.cairn/
  PROTOCOL.md                完整读写协议
  config.json                简洁的机器可读配置
cairn/
  LOG.md                     按时间倒序排列的指针索引
  topics/
    README.md                topic 格式说明
    <topic>.md               一个持续演变的项目结论
```

Agent 只读取最近的日志和当前任务相关的 topic，默认不会加载整个
`cairn/` 目录。

## 什么内容应该进入 Cairn

只有满足以下至少一个条件时才记录：

- 产品或技术决策发生变化；
- 某个失败、根因或修复结果得到验证；
- 已有结论被推翻或显著收窄；
- 一个已验证的模式可能在其他项目中复用。

不要记录日常进度、原始会议笔记、任务状态、未经验证的猜测、密钥、凭证或
个人数据。

Product Frame、PRD、代码、Schema 和任务系统继续作为各自范围内的权威
来源。Cairn Lite 记录的是一个结论为什么变化、有哪些证据支持它，而不是
替代正式事实源。

## 命令

| 命令 | 用途 |
|---|---|
| `cairn init [path]` | 在不覆盖已有文件的情况下接入协议 |
| `cairn validate [path]` | 检查目录结构、配置、topic 和日志限制 |
| `cairn status [path]` | 查看最近变化和 topic 状态 |
| `cairn test write --agent NAME [path]` | 写入一个不显示在终端中的交接验证码 |
| `cairn test read --agent NAME [path]` | 由另一个 Agent 读取并验证验证码 |
| `cairn test clean [path]` | 删除临时验证码 |

所有命令都支持 `--help`。`validate` 和 `status` 还支持 `--json`。

## 跨 Agent 测试

1. 在 Claude Desktop Code 中，将同一个项目设为 **primary folder**。
2. 让 Claude 执行：

   ```bash
   cairn test write --agent claude
   ```

   6 位验证码会写入项目，但不会显示在终端中。

3. 新建一个 Codex 任务，并把同一目录设为 primary folder。
4. 让 Codex 执行：

   ```bash
   cairn test read --agent codex
   ```

只有当另一个 Agent 从相同的真实项目目录中读到验证码时，测试才会通过。

仅仅能够访问文件还不够。还需要在两个 Agent 中分别确认：

```text
primary folder
working directory
自动生效的 AGENTS.md
```

三项必须全部指向同一个项目根目录。

CLI 只能验证不同的 Agent 标签和同一个真实文件目录，不能验证究竟是哪一个
AI 产品发出了命令。因此，全新会话测试仍然是验证流程的一部分。

## 安全与移除

Cairn Lite 不会向外部服务发送数据。默认协议要求：写入任何外部知识库前，
必须获得人的明确确认。

移除方式：

1. 删除 `.cairn/` 和 `cairn/`；
2. 删除 `AGENTS.md` 中 `<!-- cairn-lite:start -->` 与
   `<!-- cairn-lite:end -->` 之间的内容；
3. 只有在确认没有其他内容依赖它时，才从 `CLAUDE.md` 中删除
   `@AGENTS.md`。

## 参与贡献

参见 [CONTRIBUTING.md](CONTRIBUTING.md)。提案应保持范围明确、Agent
无关，并且可以安全移除。

## License

[MIT](LICENSE)

## 附录

- [HISTORY.md](HISTORY.md) — Cairn Lite 为什么被设计成现在这样
- [docs/PROTOCOL.md](docs/PROTOCOL.md) — 协议规范
- [SECURITY.md](SECURITY.md) — 安全与隐私问题报告方式

## 致谢

Cairn Lite 的灵感来自
[iBlinkQ/project-cairn](https://github.com/iBlinkQ/project-cairn)。当前实现
围绕更小、更偏本地、与 Agent 无关的协议重新编写，没有复制原项目代码。
