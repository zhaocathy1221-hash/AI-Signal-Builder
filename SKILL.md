---
name: x-ai-intel
description: Collect X/Twitter posts from a curated AI creator watchlist and generate a daily Chinese content-recommendation briefing. Use when the user asks for X AI intelligence, AI creator monitoring, daily topic recommendations, AI Agent / vibe coding / AI workflow topic mining, or wants to refresh, review, export, push, or configure the X AI intelligence workflow.
---

# X AI Intel

## What This Skill Does

Use this skill to collect recent X/Twitter posts from a configured AI watchlist, filter high-density signals, and generate a concise daily recommendation report for creators.

Default output:

- 5-10 recommended topics.
- Source account, engagement, source text excerpt, source URL.
- Why the signal matters.
- A reusable content angle and suggested hook.
- Optional Feishu Base rows and group push text.

## Quick Start

Copy the example config, fill credentials and destinations, then run:

```bash
cp references/config.example.json config.local.json
python3 scripts/x_ai_intel_daily.py --config config.local.json --dry-run
```

When the preview looks right:

```bash
python3 scripts/x_ai_intel_daily.py --config config.local.json
```

To also write new rows to Feishu Base:

```bash
python3 scripts/x_ai_intel_daily.py --config config.local.json --sync-feishu-base
```

Use `--send-feishu` only after the recipient group and bot identity are confirmed.

## Required Setup

1. Install `xreach` and make sure `node` is available.
2. Make sure X access works locally. Use `proxy`, `cookie_source`, `chrome_profile`, `auth_token_env`, or `ct0_env` in `config.local.json` when needed.
3. If your network needs a proxy, set `proxy` in `config.local.json` or use `XREACH_PROXY` / `HTTPS_PROXY` / `ALL_PROXY`.
4. Optional Feishu write/push requires `lark-cli` to be configured and authenticated.
5. Keep secrets out of the skill folder. Put only non-secret tokens such as Base token/table id in config. Put app secrets, X cookies, and auth tokens in the local environment.

## Main Workflow

1. Read `config.local.json`.
2. Validate the handle list. The default list contains 83 AI / Agent / creator accounts.
3. Fetch recent posts from each handle.
4. Exclude retweets and replies by default.
5. Score candidates by keyword relevance, freshness, and engagement.
6. Generate Markdown and JSON reports under `output_dir`.
7. If `--sync-feishu-base` is passed, create new Feishu Base rows and deduplicate by `原帖链接`.
8. If `--send-feishu` is passed, send the short daily briefing to a Feishu chat.

## Daily Automation

Use the host system's scheduler. Keep the command explicit:

```bash
cd /path/to/x-ai-intel
python3 scripts/x_ai_intel_daily.py --config config.local.json --sync-feishu-base --send-feishu
```

For a 10:00 daily run, configure cron, launchd, Hermes, or another scheduler to run the same command. Do not store secrets in the scheduler command; keep them in the local authenticated tools or environment.

## Output Style

Keep the report concise and creator-facing. Do not write a polished brand report.

Preferred group message shape:

```text
【X AI 情报博主采集完毕】

采集时间：YYYY-MM-DD HH:mm
采集范围：X AI 情报账号
扫描账号：N 个
抓取内容：N 条
今日重点关注：@handle, @handle

本轮值得看的 5 个信号：

1. 主题
@账号：发生了什么。
对内容创作的启发：可以写……
原帖：https://x.com/...

更多查看：
报告路径或 Base 链接
```

## Safety Rules

- Do not output access tokens, app secrets, webhook secrets, or cookies.
- Do not delete, clear, or bulk overwrite Feishu Base records.
- Do not send a group message the first time without user confirmation.
- Do not present unverified metrics as exact. Use "约" when engagement is approximate.
- Do not copy the original post as final creator copy. Turn it into a pattern or angle.

## Resources

- `references/config.example.json`: portable configuration template.
- `references/default-handles.txt`: default 83-account AI watchlist.
- `references/output-schema.md`: report and Feishu field mapping.
- `scripts/x_ai_intel_daily.py`: runnable collector and daily briefing generator.
