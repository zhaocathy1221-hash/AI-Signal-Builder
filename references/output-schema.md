# Output Schema

## JSON Report

The script writes:

```json
{
  "generated_at": "2026-07-24T10:00:00+08:00",
  "lookback_hours": 72,
  "handles_total": 83,
  "handles_succeeded": 79,
  "handles_failed": 1,
  "posts_collected": 400,
  "items": []
}
```

Each item includes:

| Field | Meaning |
| --- | --- |
| `rank` | Recommendation rank |
| `priority` | S / A / B |
| `account` | X handle |
| `topic` | One-line Chinese topic |
| `source_signal` | Account + engagement + signal |
| `original_excerpt` | First 300 chars of source post |
| `engagement` | Approximate likes/replies/reposts when available |
| `url` | Source X URL |
| `published_at` | Source post time |
| `why_it_matters` | Why the signal is useful |
| `recommended_angle` | Creator-facing adaptation idea |
| `suggested_hook` | Suggested Chinese hook |

## Feishu Base Suggested Fields

Use these field names when syncing to Base:

- 日期
- 批次
- 分类
- 优先级
- 来源账号
- 来源信号
- 原文前300字
- 互动数据
- 信号判断
- 原帖链接
- 主题
- 可改编选题
- 建议钩子
- 状态
- 报告文件

Write rules:

- Create-only by default.
- Deduplicate by `原帖链接`.
- Do not overwrite human fields.
- Do not delete or clear records.
- Use `feishu.base_as` for Base writes and `feishu.message_as` for chat pushes.
