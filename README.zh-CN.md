# Cairn Lite

[English](README.md) | [简体中文](README.zh-CN.md)

**让两个 AI Agent 通过同一张交接单协作的本地协议。**

计划方写下目标、边界和验收标准；执行方复述、执行、逐步记录，卡住时把问题写回
同一个文件。人只在三个地方出现：定目标、做决定、验收。

它替代的是这种做法：写一份长交接文档，把提示词贴给另一个 Agent，再在两边来回
转述进度和问题。

> 当前状态：实验阶段。文件格式已经可用，但在 1.0 前仍可能调整。

## 一次完整的循环

```text
人：一句话目标
  → 计划方（例如云端 Claude）写交接单：目标、决定、建议做法、验收、不做什么
  → 执行方（例如本机 Codex）进入项目，通过 AGENTS.md 自己找到交接单
  → 执行方先写复述，再执行，每完成一步在 Log 里记一条，附证据
  → 遇到会改变决定、验收或范围的问题：写进 Questions，标成 blocked，停下
  → 计划方或人在同一个文件里回答；执行方被叫醒时先重读交接单
  → 验收全部满足：标成 done
```

计划方不用问人「它做到哪了」，直接读交接单；人不用复制粘贴任何东西。

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

在要交接的项目里接入协议，然后开一张交接单：

```bash
cd /path/to/your-project
cairn init
cairn handoff new site-v1 --title "个人网站 v1" --from claude --to codex \
  --planner-url https://claude.ai/your-project-link
```

计划方把 `cairn/handoffs/site-v1.md` 里的 Goal、Decisions、Design、Acceptance、
Out of scope 填好。之后执行方进入这个项目时会自己找到它，不需要贴提示词。

随时查看所有交接单的状态：

```bash
cairn handoff status
```

`cairn init` 采用追加式写入，可以安全地重复执行，不覆盖任何已有文件；
可以先用 `cairn init --dry-run` 预览。它会：

- 在 `AGENTS.md` 里追加一个带边界标记、可移除的规则区块，让 Agent 进入项目时
  先检查有没有写给自己的交接单；
- 需要时向 `CLAUDE.md` 追加 `@AGENTS.md`；
- 把 `cairn/handoffs/` 加进 `.gitignore`。交接单是工作过程，经常带有本机路径和
  私有信息，默认不进 Git。

## 交接单

每件工作一个文件：`cairn/handoffs/<id>.md`。

头部记录状态：`open`、`acknowledged`、`running`、`blocked`、`done`、`cancelled`，
以及 `from`、`to` 和可选的 `planner_url`。

| 部分 | 谁负责 | 规则 |
|---|---|---|
| Goal | 人 | 做完时人想要什么 |
| Decisions | 人 | 只引用已确认的决定，不复制 |
| Design | 计划方 | 是假设；执行方可以改，但要在 Log 里写明原因 |
| Acceptance、Out of scope | 人 | 只有负责人能改 |
| Readback | 执行方 | 开工前先写：目标、不做什么、停在哪 |
| Log | 执行方 | 每完成一步追加一条，带证据 |
| Questions | 执行方 | 会改变决定的问题；写下后设为 `blocked` 并停下 |

执行方的规则：

1. 开工前用自己的话写 Readback（不超过 6 行），状态设为 `acknowledged`。
2. 状态设为 `running` 后开始执行；每完成一步，在 Log 里追加一条，附证据。
3. 问题会改变 Decisions、Acceptance 或 Out of scope 时，写进 Questions，
   设为 `blocked`，停下。
4. 所有验收都满足时，设为 `done`。
5. 每次被叫醒（「继续」、新消息、新会话），先重读交接单，不要凭对话记忆。

交接单里的记录不能代替人的授权。推送、发布这类对外动作，执行方要在自己的对话里
得到人的确认。

`cairn validate` 会检查状态和内容是否一致：acknowledged 必须有 Readback，blocked
必须有未回答的问题，done 必须有 Log，`planner_url` 只接受 `https://`。

## 和其他工具配合

Cairn Lite 只管「一件事从派出去到做完」。它可以单独使用，也可以和下面两个工具
组成一个循环：

- **[cairn-context](https://github.com/alexliu072903-bit/cairn-context)**：
  记录跨任务长期有效的决定。交接单的 Decisions 只写它的引用，不复制内容。
- **AirJelly**：执行方停下时读取交接单的状态。`blocked` 或 `done` 时弹出卡片，
  让人选择下一步；需要重新规划时，按 `planner_url` 把人送回计划方。

## 命令

| 命令 | 用途 |
|---|---|
| `cairn init [path]` | 在不覆盖已有文件的情况下接入协议 |
| `cairn handoff new ID --title T --from A --to B [--planner-url URL]` | 新建一张交接单 |
| `cairn handoff status [path]` | 列出交接单、状态和未回答的问题 |
| `cairn validate [path]` | 检查目录结构、配置和交接单 |
| `cairn status [path]` | 同 `cairn handoff status` |
| `cairn test write/read/clean` | 验证两个 Agent 指向同一个项目目录（见附录） |

所有命令都支持 `--help`。`validate`、`status`、`handoff status` 支持 `--json`。

## 安全与移除

Cairn Lite 不会向外部服务发送数据。写入任何外部知识库前，协议要求先得到人的
明确确认。

移除方式：

1. 删除 `.cairn/` 和 `cairn/`；
2. 删除 `AGENTS.md` 中 `<!-- cairn-lite:start -->` 与
   `<!-- cairn-lite:end -->` 之间的内容；
3. 只有在确认没有其他内容依赖它时，才从 `CLAUDE.md` 中删除 `@AGENTS.md`。

## 附录

### 从早期版本升级

早期版本的 Cairn Lite 还带有项目笔记（`cairn/LOG.md` 和 `cairn/topics/`），现在已经
移除，原因见 [HISTORY.md](HISTORY.md)。旧项目仍然能通过 `cairn validate`，这些文件
会被忽略，可以保留，也可以删掉。需要长期保存的决定，建议记进 cairn-context。

`cairn init` 不会改写已有的规则区块。要换成新的入口规则，先删除 `AGENTS.md` 中
`<!-- cairn-lite:start -->` 与 `<!-- cairn-lite:end -->` 之间的内容和
`.cairn/PROTOCOL.md`，再运行一次 `cairn init`。

### 验证两个 Agent 看到的是同一个目录

交接单能用的前提，是计划方和执行方读写的是同一个真实目录。

1. 在 Claude 里运行 `cairn test write --agent claude`。6 位验证码会写入项目，
   但不会显示在终端中。
2. 在 Codex 里，打开同一个目录，运行 `cairn test read --agent codex`。
3. 通过后运行 `cairn test clean`。

还需要确认两边的 primary folder、working directory 和自动生效的 `AGENTS.md`
都指向同一个项目根目录。CLI 只能验证目录，不能验证命令究竟来自哪个 AI 产品。

### 其他文档

- [docs/PROTOCOL.md](docs/PROTOCOL.md)：协议规范
- [HISTORY.md](HISTORY.md)：Cairn Lite 的演变过程
- [CONTRIBUTING.md](CONTRIBUTING.md)：参与贡献
- [SECURITY.md](SECURITY.md)：安全与隐私问题报告方式

## License

[MIT](LICENSE)

## 致谢

Cairn Lite 的灵感来自
[iBlinkQ/project-cairn](https://github.com/iBlinkQ/project-cairn)。当前实现
围绕更小、更偏本地、与 Agent 无关的协议重新编写，没有复制原项目代码。
