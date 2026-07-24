#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


TZ = ZoneInfo("Asia/Shanghai")
SKILL_DIR = Path(__file__).resolve().parents[1]


THEMES: list[tuple[str, tuple[str, ...], str, str, str]] = [
    (
        "Agent 工作流正在从聊天走向可复用流程",
        ("agent", "workflow", "automation", "mcp", "skill", "codex", "claude code", "自动化", "工作流"),
        "Agent 不再只是帮人写一段话，而是在进入真实流程和工具调用。",
        "可以写普通人如何把重复工作沉淀成一个可复用的 AI 工作流。",
        "比 prompt 更重要的，是把重复工作变成一个可以反复调用的流程。",
    ),
    (
        "AI 编程正在变成非技术创作者的表达工具",
        ("coding", "code", "developer", "github", "cursor", "vibe coding", "编程", "开发"),
        "AI 编程的讨论正在从工程效率，扩展到普通人如何做产品和表达。",
        "可以写非技术创作者如何用 AI 把想法做成可见的作品。",
        "我发现不会代码的人，反而更容易把 AI 编程当成一种表达方式。",
    ),
    (
        "AI 内容工具进入视频、图像和设计工作流",
        ("image", "video", "design", "creator", "content", "midjourney", "flow", "stitch", "生图", "视频", "设计", "内容"),
        "创作工具的重点正在从生成更多内容，转向帮创作者提高判断和成品质量。",
        "可以写内容人如何把 AI 放进选题、视觉、剪辑和发布前判断。",
        "AI 生图之后，真正拉开差距的不是会不会生成，而是会不会判断。",
    ),
    (
        "模型更新正在变成产品和工作方式更新",
        ("model", "gpt", "chatgpt", "claude", "gemini", "qwen", "deepseek", "kimi", "模型"),
        "模型新闻本身不重要，重要的是能力变化会改变哪些具体任务。",
        "可以写创作者如何判断一个新模型值不值得迁移到自己的工作台。",
        "不要追每一次模型发布，要看它有没有改变你的真实工作流。",
    ),
    (
        "AI 进入组织后，真正难的是流程和验收标准",
        ("enterprise", "business", "company", "team", "eval", "security", "企业", "组织", "安全", "验收"),
        "AI 落地的瓶颈越来越多地出现在流程、数据、权限和验收标准上。",
        "可以写内容团队和小团队怎样先整理流程，再谈 AI 提效。",
        "AI 进公司以后，最先暴露的不是模型能力，而是流程有没有被整理过。",
    ),
]


@dataclass(frozen=True)
class Post:
    handle: str
    text: str
    url: str
    created_at: datetime
    likes: int
    replies: int
    reposts: int


@dataclass(frozen=True)
class Item:
    rank: int
    priority: str
    account: str
    topic: str
    source_signal: str
    original_excerpt: str
    engagement: str
    url: str
    published_at: str
    why_it_matters: str
    recommended_angle: str
    suggested_hook: str
    score: float


BASE_FIELDS = [
    "日期",
    "批次",
    "分类",
    "优先级",
    "来源账号",
    "来源信号",
    "原文前300字",
    "互动数据",
    "信号判断",
    "原帖链接",
    "主题",
    "可改编选题",
    "建议钩子",
    "状态",
    "报告文件",
]


def clean_text(value: object, limit: int = 300) -> str:
    text = " ".join(str(value or "").replace("\n", " ").split()).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def has_enough_chinese(text: str) -> bool:
    return len(re.findall(r"[\u4e00-\u9fff]", text)) >= 5


def should_add_chinese_translation(text: str) -> bool:
    if not text or "中文翻译：" in text or "中文翻译:" in text:
        return False
    if has_enough_chinese(text):
        return False
    return len(re.findall(r"[A-Za-z]", text)) >= 20


def translate_to_zh(text: str) -> str:
    query = urllib.parse.urlencode(
        {
            "client": "gtx",
            "sl": "auto",
            "tl": "zh-CN",
            "dt": "t",
            "q": text[:1200],
        }
    )
    url = "https://translate.googleapis.com/translate_a/single?" + query
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return ""
    try:
        return "".join(part[0] for part in payload[0] if part and part[0]).strip()
    except (TypeError, IndexError):
        return ""


def format_original_excerpt(text: str) -> str:
    original = clean_text(text, 300)
    if not should_add_chinese_translation(original):
        return original
    translation = translate_to_zh(original)
    if not translation:
        return original
    return f"原文：\n{original}\n\n中文翻译：\n{translation}"


def normalize_handle(value: str) -> str:
    return value.strip().lstrip("@").lower()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_handles(path: Path) -> list[str]:
    handles: list[str] = []
    seen: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        handle = value.lstrip("@")
        if not re.fullmatch(r"[A-Za-z0-9_]{1,15}", handle):
            raise ValueError(f"Invalid X handle: {value}")
        key = handle.lower()
        if key not in seen:
            seen.add(key)
            handles.append("@" + handle)
    return handles


def resolve_config_path(raw: str, config_path: Path) -> Path:
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    candidate = (config_path.parent / path).resolve()
    if candidate.exists():
        return candidate
    return (SKILL_DIR / path).resolve()


def find_bin(name: str) -> str:
    env_key = name.upper().replace("-", "_") + "_BIN"
    explicit = os.environ.get(env_key, "").strip()
    if explicit:
        candidate = Path(explicit).expanduser()
        if candidate.exists():
            return str(candidate)
        raise FileNotFoundError(f"{env_key} points to a missing file: {candidate}")
    found = shutil.which(name)
    if found:
        return found
    raise FileNotFoundError(f"Missing command: {name}")


def run_json(cmd: list[str], timeout: int, attempts: int) -> dict[str, Any]:
    last_error = ""
    for attempt in range(max(1, attempts)):
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False)
        if proc.returncode == 0:
            try:
                return json.loads(proc.stdout)
            except json.JSONDecodeError as exc:
                last_error = f"Invalid JSON: {exc}"
        else:
            last_error = proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}"
        if attempt + 1 < attempts:
            continue
    raise RuntimeError(last_error)


def xreach_global_args(config: dict[str, Any]) -> list[str]:
    args: list[str] = []
    proxy = str(config.get("proxy") or "").strip()
    if not proxy:
        for key in ["XREACH_PROXY", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy"]:
            proxy = os.environ.get(key, "").strip()
            if proxy:
                break
    if proxy:
        args.extend(["--proxy", proxy])

    timeout_ms = int(config.get("xreach_timeout_ms") or int(config.get("request_timeout_seconds") or 25) * 1000)
    args.extend(["--timeout", str(timeout_ms)])

    cookie_source = str(config.get("cookie_source") or "").strip()
    if cookie_source:
        args.extend(["--cookie-source", cookie_source])
    chrome_profile = str(config.get("chrome_profile") or "").strip()
    if chrome_profile:
        args.extend(["--chrome-profile", chrome_profile])
    auth_env = str(config.get("auth_token_env") or "").strip()
    if auth_env and os.environ.get(auth_env):
        args.extend(["--auth-token", os.environ[auth_env]])
    ct0_env = str(config.get("ct0_env") or "").strip()
    if ct0_env and os.environ.get(ct0_env):
        args.extend(["--ct0", os.environ[ct0_env]])
    return args


def fetch_handle(handle: str, config: dict[str, Any]) -> tuple[str, list[Post], str | None]:
    node = find_bin("node")
    xreach = find_bin("xreach")
    global_args = xreach_global_args(config)
    timeout = int(config.get("request_timeout_seconds") or 25)
    attempts = int(config.get("attempts") or 1)
    count = int(config.get("per_handle_count") or 40)
    cmd = [node, xreach, *global_args, "tweets", handle.lstrip("@"), "-n", str(count), "--json"]
    try:
        payload = run_json(cmd, timeout=timeout, attempts=attempts)
    except Exception as exc:
        if not config.get("search_fallback", True):
            return handle, [], str(exc)
        fallback_count = int(config.get("fallback_count") or max(count, 60))
        fallback_cmd = [
            node,
            xreach,
            *global_args,
            "search",
            f"from:{handle.lstrip('@')}",
            "--type",
            "latest",
            "-n",
            str(fallback_count),
            "--json",
        ]
        try:
            payload = run_json(fallback_cmd, timeout=timeout, attempts=attempts)
        except Exception as fallback_exc:
            return handle, [], f"tweets failed: {exc}; search fallback failed: {fallback_exc}"

    posts: list[Post] = []
    for raw in payload.get("items") or []:
        if config.get("exclude_retweets", True) and raw.get("isRetweet"):
            continue
        if config.get("exclude_replies", True) and raw.get("isReply"):
            continue
        created = parse_x_date(raw.get("createdAt"))
        if not created:
            continue
        user = raw.get("user") or {}
        screen_name = user.get("screenName") or handle.lstrip("@")
        post_id = str(raw.get("id") or "").strip()
        if not post_id:
            continue
        posts.append(
            Post(
                handle="@" + str(screen_name).lstrip("@"),
                text=clean_text(raw.get("text"), 1200),
                url=f"https://x.com/{screen_name}/status/{post_id}",
                created_at=created,
                likes=int(raw.get("likeCount") or 0),
                replies=int(raw.get("replyCount") or 0),
                reposts=int(raw.get("retweetCount") or 0),
            )
        )
    return handle, posts, None


def parse_x_date(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%a %b %d %H:%M:%S %z %Y",):
        try:
            return datetime.strptime(text, fmt).astimezone(TZ)
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.astimezone(TZ)
    except ValueError:
        return None


def load_feed_payload(config: dict[str, Any], config_path: Path) -> dict[str, Any]:
    feed_url = str(config.get("feed_url") or "").strip()
    if feed_url:
        try:
            with urllib.request.urlopen(feed_url, timeout=int(config.get("feed_timeout_seconds") or 30)) as response:
                return json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError):
            pass

    feed_file = str(config.get("feed_file") or "feeds/x-ai-feed.json")
    feed_path = resolve_config_path(feed_file, config_path)
    return json.loads(feed_path.read_text(encoding="utf-8"))


def post_from_feed_item(raw: dict[str, Any]) -> Post | None:
    created = parse_x_date(raw.get("created_at") or raw.get("createdAt"))
    if not created:
        return None
    metrics = raw.get("metrics") or {}
    account = str(raw.get("account") or raw.get("handle") or "").strip()
    if not account:
        return None
    return Post(
        handle="@" + account.lstrip("@"),
        text=clean_text(raw.get("text") or raw.get("text_excerpt_300"), 1200),
        url=str(raw.get("url") or "").strip(),
        created_at=created,
        likes=int(metrics.get("likes") or raw.get("likes") or 0),
        replies=int(metrics.get("replies") or raw.get("replies") or 0),
        reposts=int(metrics.get("reposts") or metrics.get("retweets") or raw.get("reposts") or raw.get("retweets") or 0),
    )


def load_posts_from_feed(config: dict[str, Any], config_path: Path) -> tuple[list[Post], dict[str, Any]]:
    payload = load_feed_payload(config, config_path)
    posts: list[Post] = []
    for raw in payload.get("items") or []:
        if config.get("exclude_retweets", True) and raw.get("is_retweet"):
            continue
        if config.get("exclude_replies", True) and raw.get("is_reply"):
            continue
        post = post_from_feed_item(raw)
        if post and post.url:
            posts.append(post)
    return posts, payload


def term_present(text: str, term: str) -> bool:
    lowered = text.lower()
    needle = term.lower()
    if re.fullmatch(r"[a-z0-9_ ]+", needle):
        return needle in lowered
    return needle in text


def classify(post: Post, keywords: list[str]) -> tuple[str, str, str, str, int]:
    text = post.text
    best = THEMES[0]
    best_hits = 0
    for theme in THEMES:
        hits = sum(1 for term in theme[1] if term_present(text, term))
        if hits > best_hits:
            best = theme
            best_hits = hits
    keyword_hits = sum(1 for term in keywords if term_present(text, term))
    total_hits = best_hits + keyword_hits
    return best[0], best[2], best[3], best[4], total_hits


def score_post(post: Post, hits: int, now: datetime, lookback_hours: int) -> float:
    age_hours = max(0.0, (now - post.created_at).total_seconds() / 3600)
    freshness = max(0.0, lookback_hours - min(age_hours, lookback_hours))
    engagement = post.likes + post.replies * 2 + post.reposts * 2
    return hits * 35 + math.log1p(max(0, engagement)) * 10 + freshness


def build_items(posts: list[Post], config: dict[str, Any]) -> list[Item]:
    now = datetime.now(TZ)
    lookback = int(config.get("lookback_hours") or 72)
    cutoff = now - timedelta(hours=lookback)
    keywords = [str(x) for x in config.get("keywords") or []]
    candidates: list[tuple[float, Post, tuple[str, str, str, str, int]]] = []
    seen_urls: set[str] = set()

    for post in posts:
        if post.created_at < cutoff or post.url in seen_urls:
            continue
        topic, why, angle, hook, hits = classify(post, keywords)
        if hits <= 0:
            continue
        score = score_post(post, hits, now, lookback)
        candidates.append((score, post, (topic, why, angle, hook, hits)))
        seen_urls.add(post.url)

    candidates.sort(key=lambda x: (x[0], x[1].created_at, x[1].likes), reverse=True)
    max_items = int(config.get("max_items") or 10)
    items: list[Item] = []
    for index, (score, post, classified) in enumerate(candidates[:max_items], start=1):
        topic, why, angle, hook, _hits = classified
        priority = "S" if index <= 5 else "A" if index <= 10 else "B"
        engagement = f"点赞约 {post.likes}，回复约 {post.replies}，转发约 {post.reposts}"
        signal = f"{post.handle}：{engagement}。信号：{why}"
        items.append(
            Item(
                rank=index,
                priority=priority,
                account=post.handle,
                topic=topic,
                source_signal=signal,
                original_excerpt=format_original_excerpt(post.text),
                engagement=engagement,
                url=post.url,
                published_at=post.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                why_it_matters=why,
                recommended_angle=angle,
                suggested_hook=hook,
                score=round(score, 2),
            )
        )
    return items


def item_to_dict(item: Item) -> dict[str, Any]:
    return {
        "rank": item.rank,
        "priority": item.priority,
        "account": item.account,
        "topic": item.topic,
        "source_signal": item.source_signal,
        "original_excerpt": item.original_excerpt,
        "engagement": item.engagement,
        "url": item.url,
        "published_at": item.published_at,
        "why_it_matters": item.why_it_matters,
        "recommended_angle": item.recommended_angle,
        "suggested_hook": item.suggested_hook,
        "score": item.score,
    }


def build_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# X AI 情报日报",
        "",
        f"采集时间：{payload['generated_at']}",
        f"扫描账号：{payload['handles_total']} 个",
        f"抓取内容：{payload['posts_collected']} 条",
        f"入选推荐：{len(payload['items'])} 条",
        "",
        "## 今日推荐",
        "",
    ]
    for item in payload["items"]:
        lines.extend(
            [
                f"### {item['rank']}. {item['topic']}",
                "",
                f"- 账号：{item['account']}",
                f"- 优先级：{item['priority']}",
                f"- 互动：{item['engagement']}",
                f"- 信号：{item['why_it_matters']}",
                f"- 可改编选题：{item['recommended_angle']}",
                f"- 建议钩子：{item['suggested_hook']}",
                f"- 原帖：{item['url']}",
                f"- 原文前300字：{item['original_excerpt']}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def build_group_text(payload: dict[str, Any], base_url: str = "") -> str:
    items = payload["items"][:5]
    focus = []
    for item in items:
        if item["account"] not in focus:
            focus.append(item["account"])
    lines = [
        "【X AI 情报博主采集完毕】",
        "",
        f"采集时间：{payload['generated_at']}",
        "采集范围：X AI 情报账号",
        f"扫描账号：{payload['handles_total']} 个",
        f"抓取内容：{payload['posts_collected']} 条",
        f"今日重点关注：{'、'.join(focus[:8]) if focus else '暂无'}",
        "",
        f"本轮值得看的 {len(items)} 个信号：",
        "",
    ]
    for item in items:
        lines.extend(
            [
                f"{item['rank']}. {item['topic']}",
                f"{item['account']}：{item['why_it_matters']}",
                f"对内容创作的启发：{item['recommended_angle']}",
                f"原帖：{item['url']}",
                "",
            ]
        )
    if base_url:
        lines.extend(["更多查看：", base_url])
    else:
        lines.extend(["更多查看：", payload["markdown_path"]])
    return "\n".join(lines).strip()


def write_reports(payload: dict[str, Any], config: dict[str, Any], config_path: Path) -> dict[str, Any]:
    output_dir = resolve_config_path(str(config.get("output_dir") or "reports"), config_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(TZ).strftime("%Y%m%d_%H%M")
    json_path = output_dir / f"x_ai_intel_{stamp}.json"
    md_path = output_dir / f"x_ai_intel_{stamp}.md"
    payload["json_path"] = str(json_path)
    payload["markdown_path"] = str(md_path)
    md_text = build_markdown(payload)
    payload["group_text"] = build_group_text(payload, (config.get("feishu") or {}).get("view_url") or "")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(md_text, encoding="utf-8")
    return payload


def run_lark(args: list[str]) -> dict[str, Any]:
    lark_cli = find_bin("lark-cli")
    proc = subprocess.run([lark_cli, *args], text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"lark-cli exited {proc.returncode}")
    payload = json.loads(proc.stdout)
    if not payload.get("ok"):
        raise RuntimeError(json.dumps(payload.get("error") or payload, ensure_ascii=False))
    return payload


def send_feishu_group(payload: dict[str, Any], config: dict[str, Any]) -> dict[str, Any] | None:
    feishu = config.get("feishu") or {}
    chat_id = str(feishu.get("chat_id") or "").strip()
    if not chat_id:
        raise RuntimeError("Missing feishu.chat_id")
    send_as = str(feishu.get("message_as") or feishu.get("send_as") or "bot")
    key = "x-ai-intel-" + datetime.now(TZ).strftime("%Y%m%d%H%M")
    return run_lark(
        [
            "im",
            "+messages-send",
            "--chat-id",
            chat_id,
            "--text",
            payload["group_text"],
            "--idempotency-key",
            key,
            "--as",
            send_as,
        ]
    )


def list_existing_base_urls(config: dict[str, Any]) -> set[str]:
    feishu = config.get("feishu") or {}
    base_token = str(feishu.get("base_token") or "").strip()
    table_id = str(feishu.get("table_id") or "").strip()
    send_as = str(feishu.get("base_as") or "user")
    if not base_token or not table_id:
        raise RuntimeError("Missing feishu.base_token or feishu.table_id")

    urls: set[str] = set()
    offset = 0
    while True:
        payload = run_lark(
            [
                "base",
                "+record-list",
                "--base-token",
                base_token,
                "--table-id",
                table_id,
                "--field-id",
                "原帖链接",
                "--offset",
                str(offset),
                "--limit",
                "200",
                "--format",
                "json",
                "--as",
                send_as,
            ]
        )
        data = payload.get("data") or {}
        records = data.get("items") or data.get("records") or []
        for record in records:
            fields = record.get("fields") or record.get("record", {}).get("fields") or {}
            url = str(fields.get("原帖链接") or "").strip()
            if url:
                urls.add(url)
        has_more = bool(data.get("has_more"))
        offset = int(data.get("offset") or data.get("next_offset") or offset + len(records))
        if not has_more or not records:
            break
    return urls


def item_to_base_row(item: dict[str, Any], payload: dict[str, Any], batch: str) -> list[Any]:
    return [
        payload["generated_at"].split(" ")[0],
        batch,
        "我今天应该发的创意",
        item["priority"],
        item["account"],
        item["source_signal"],
        item["original_excerpt"],
        item["engagement"],
        item["why_it_matters"],
        item["url"],
        item["topic"],
        item["recommended_angle"],
        item["suggested_hook"],
        "待判断",
        payload["markdown_path"],
    ]


def sync_feishu_base(payload: dict[str, Any], config: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    feishu = config.get("feishu") or {}
    base_token = str(feishu.get("base_token") or "").strip()
    table_id = str(feishu.get("table_id") or "").strip()
    send_as = str(feishu.get("base_as") or "user")
    if not base_token or not table_id:
        raise RuntimeError("Missing feishu.base_token or feishu.table_id")

    existing_urls = list_existing_base_urls(config)
    batch = "x-ai-" + datetime.now(TZ).strftime("%Y%m%d-%H%M")
    rows = [
        item_to_base_row(item, payload, batch)
        for item in payload["items"]
        if item["url"] not in existing_urls
    ]
    result: dict[str, Any] = {
        "batch": batch,
        "dedupe_field": "原帖链接",
        "new_rows": len(rows),
        "skipped_existing": len(payload["items"]) - len(rows),
        "dry_run": dry_run,
    }
    if dry_run or not rows:
        return result

    created_ids: list[str] = []
    for start in range(0, len(rows), 200):
        chunk = rows[start : start + 200]
        response = run_lark(
            [
                "base",
                "+record-batch-create",
                "--base-token",
                base_token,
                "--table-id",
                table_id,
                "--json",
                json.dumps({"fields": BASE_FIELDS, "rows": chunk}, ensure_ascii=False),
                "--as",
                send_as,
            ]
        )
        created_ids.extend(response.get("data", {}).get("record_id_list") or [])
    result["record_ids"] = created_ids
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect X AI creator intelligence and build daily recommendations.")
    parser.add_argument("--config", type=Path, default=SKILL_DIR / "references" / "config.example.json")
    parser.add_argument("--source", choices=["xreach", "feed"], help="Override config.source_type.")
    parser.add_argument("--dry-run", action="store_true", help="Preview only; do not send Feishu messages.")
    parser.add_argument("--sync-feishu-base", action="store_true", help="Create new Feishu Base rows, deduped by source URL.")
    parser.add_argument("--send-feishu", action="store_true", help="Send the short briefing to Feishu.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = args.config.expanduser().resolve()
    config = load_json(config_path)
    source_type = args.source or str(config.get("source_type") or "xreach")
    handles_path = resolve_config_path(str(config.get("handles_file") or "references/default-handles.txt"), config_path)
    handles = load_handles(handles_path)

    posts: list[Post] = []
    failures: dict[str, str] = {}
    feed_meta: dict[str, Any] | None = None

    if source_type == "feed":
        posts, feed_meta = load_posts_from_feed(config, config_path)
    else:
        max_workers = max(1, int(config.get("max_workers") or 4))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {executor.submit(fetch_handle, handle, config): handle for handle in handles}
            for future in as_completed(future_map):
                handle, handle_posts, error = future.result()
                if error:
                    failures[handle] = error
                posts.extend(handle_posts)

    items = build_items(posts, config)
    payload: dict[str, Any] = {
        "generated_at": datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "source_type": source_type,
        "feed_generated_at": feed_meta.get("feed_generated_at") if feed_meta else None,
        "lookback_hours": int(config.get("lookback_hours") or 72),
        "handles_total": len(handles),
        "handles_succeeded": len(handles) - len(failures),
        "handles_failed": len(failures),
        "failures": failures,
        "posts_collected": len(posts),
        "items": [item_to_dict(item) for item in items],
    }
    payload = write_reports(payload, config, config_path)

    if args.sync_feishu_base:
        payload["feishu_base_result"] = sync_feishu_base(payload, config, dry_run=args.dry_run)
        Path(payload["json_path"]).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.send_feishu and not args.dry_run:
        payload["feishu_send_result"] = send_feishu_group(payload, config)
        Path(payload["json_path"]).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({k: payload[k] for k in ["generated_at", "handles_total", "handles_succeeded", "handles_failed", "posts_collected", "json_path", "markdown_path"]}, ensure_ascii=False, indent=2))
    if args.dry_run:
        print("\n--- GROUP PREVIEW ---\n")
        print(payload["group_text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
