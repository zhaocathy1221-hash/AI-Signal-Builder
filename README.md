# AI Signal Builder

AI Signal Builder 是一个面向内容创作者的 X / Twitter AI 情报 Skill。

它会采集 83 个 AI Builder、模型公司、中文 AI 实践者和创作者工具账号的近期内容，筛出高密度信号，并生成中文选题日报。

它的目标不是帮你刷更多信息，而是帮你每天动笔前先看到：

- AI 圈真正发生了什么变化
- 哪些工具或工作流已经值得关注
- 哪些外部信号可以改编成中文内容选题
- 哪些角度已经被过度使用

## 适合谁

- 内容创作者、公众号作者、小红书创作者
- AI Agent / AI 工作流实践者
- 想跟踪 AI Builder、Codex、Claude Code、Cursor、MCP、自动化工作流的人
- 想每天收到 5-10 个可写选题的人

## 你会得到什么

每次运行会生成：

- 本地 Markdown 日报
- 本地 JSON 数据
- 5-10 个推荐选题
- 来源账号、原帖链接、原文前 300 字
- 互动数据快照
- 信号判断
- 可改编选题
- 建议钩子
- 可选写入飞书多维表格
- 可选推送到飞书群或私聊

示例推送：

```text
【X AI 情报博主采集完毕】

采集时间：2026-07-24 14:24
采集范围：X AI 情报账号
扫描账号：83 个
抓取内容：852 条
今日重点关注：@AndrewYNg、@dotey、@OpenAI

本轮值得看的 5 个信号：

1. Agent 工作流正在从聊天走向可复用流程
@OpenAI：ChatGPT Voice 进入桌面端，可语音控制电脑并调度多个 Agent。
对内容创作的启发：可以写普通人如何把重复工作沉淀成一个可复用的 AI 工作流。
原帖：https://x.com/OpenAI/status/...

更多查看：
报告路径或飞书多维表格链接
```

## 安装

克隆到你的 Skill 目录：

```bash
git clone https://github.com/zhaocathy1221-hash/AI-Signal-Builder.git ~/.codex/skills/x-ai-intel
cd ~/.codex/skills/x-ai-intel
```

安装 X 采集工具：

```bash
npm install -g xreach-cli@0.3.3
```

确认可用：

```bash
xreach -v
xreach tweets OpenAI -n 5 --json
```

## 配置

复制配置模板：

```bash
cp references/config.example.json config.local.json
```

如果你访问 X 需要代理，在 `config.local.json` 里填写：

```json
"proxy": "http://127.0.0.1:7890"
```

常见代理端口可能是：

```text
7890
7897
1087
10808
6478
```

如果浏览器能打开 X，但脚本超时，通常就是代理没有写进 `config.local.json`。

## 运行

第一次先用试跑模式：

```bash
python3 scripts/x_ai_intel_daily.py --config config.local.json --dry-run
```

`--dry-run` 会生成报告和推送预览，但不会写飞书，也不会发消息。

确认没问题后运行：

```bash
python3 scripts/x_ai_intel_daily.py --config config.local.json
```

## 写入飞书多维表格

先在 `config.local.json` 里填写：

```json
"feishu": {
  "base_token": "",
  "table_id": "",
  "view_url": "",
  "chat_id": "",
  "message_as": "bot",
  "base_as": "user"
}
```

然后运行：

```bash
python3 scripts/x_ai_intel_daily.py --config config.local.json --sync-feishu-base
```

写入规则：

- 只新增，不清空
- 按 `原帖链接` 去重
- 不覆盖人工判断字段
- 不删除历史记录

推荐多维表格字段见：

```text
references/output-schema.md
```

## 推送飞书群或私聊

确认 `chat_id` 和机器人身份后运行：

```bash
python3 scripts/x_ai_intel_daily.py --config config.local.json --send-feishu
```

如果要同时写表和推送：

```bash
python3 scripts/x_ai_intel_daily.py --config config.local.json --sync-feishu-base --send-feishu
```

第一次推送前建议先跑：

```bash
python3 scripts/x_ai_intel_daily.py --config config.local.json --dry-run
```

## 每日自动化

把这条命令放进 cron、launchd、Hermes 或其他自动化工具即可：

```bash
cd ~/.codex/skills/x-ai-intel
python3 scripts/x_ai_intel_daily.py --config config.local.json --sync-feishu-base --send-feishu
```

例如每天 10 点运行，就让你的调度器每天 10:00 执行上面的命令。

## 账号名单

默认账号在：

```text
references/default-handles.txt
```

当前包含 83 个账号，覆盖：

- 官方模型与平台信号
- AI 研究者与技术大佬
- Agent 与 AI 编程实践者
- 产品、商业与公司经营信号
- 中文 AI 实践与内容现场
- 内容、写作、知识管理与创作者工具
- 争议、批评与反向观点

代表账号包括：

```text
@OpenAI
@AnthropicAI
@GoogleAI
@karpathy
@swyx
@thsottiaux
@dotey
@op7418
@bourneliu66
@DesignArena
```

你可以直接编辑 `references/default-handles.txt`，加入自己的观察账号。

## 输出字段

每条入选内容会包含：

| 字段 | 说明 |
| --- | --- |
| 来源账号 | X handle |
| 来源信号 | 这条内容为什么值得看 |
| 原文前300字 | 方便人工复核 |
| 原帖链接 | 可追溯来源 |
| 互动数据 | 点赞、回复、转发快照 |
| 主题 | 中文主题判断 |
| 可改编选题 | 面向创作者的二创方向 |
| 建议钩子 | 可直接进入写作的开头 |
| 优先级 | S / A / B |
| 状态 | 默认待判断 |

## 常见问题

### 1. xreach 超时

先确认浏览器能打开 X。

如果浏览器能打开，但脚本不能抓，通常是命令行没有走代理。

在 `config.local.json` 里设置：

```json
"proxy": "http://127.0.0.1:你的代理端口"
```

也可以用环境变量：

```bash
export XREACH_PROXY=http://127.0.0.1:7890
```

### 2. 飞书写入失败

检查：

- `lark-cli` 是否已配置并授权
- `base_token` 是否正确
- `table_id` 是否正确
- 多维表格字段是否和 `references/output-schema.md` 一致
- `base_as` 是否应该用 `user`

### 3. 飞书消息没有发出去

检查：

- `chat_id` 是否正确
- bot 是否在群里
- `message_as` 是否应该用 `bot`
- 第一次是否已经用 `--dry-run` 看过预览

### 4. 入选内容太少

可以调整：

- `lookback_hours`
- `max_items`
- `keywords`
- `per_handle_count`
- 是否放宽 `exclude_replies`

默认会排除转发和回复，避免重复和低密度内容。

## 安全提醒

- 不要提交 `config.local.json`
- 不要把 X cookie、auth token、飞书 app secret 放进仓库
- 不要把别人的原帖直接改成自己的成稿
- 互动数据是采集时的快照，建议用“约”
- 第一次群推送前先确认群和机器人身份

## Skill 触发提示

安装后，可以在 Agent 里这样说：

```text
使用 x-ai-intel，采集 AI 博主最近 72 小时的 X 内容，生成今天最值得看的 5-10 个选题。
```

或：

```text
跑一遍 X AI 情报日报，先 dry-run，不要写飞书，也不要推送。
```

或：

```text
刷新 AI Signal Builder，并把结果写入飞书多维表格后推送到群里。
```

## 这不是自动写作工具

AI Signal Builder 负责的是：

```text
采集情报 → 筛选信号 → 生成选题推荐
```

真正的写作仍然需要创作者判断：

```text
哪些选题值得合并
哪些适合今天写
哪些只是趋势观察
哪些角度已经被过度使用
```

它更像每天动笔前的一份 AI 选题雷达。
