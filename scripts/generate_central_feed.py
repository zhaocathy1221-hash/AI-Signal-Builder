#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from x_ai_intel_daily import TZ, clean_text, fetch_handle, load_handles, resolve_config_path  # noqa: E402


def tweet_id_from_url(url: str) -> str:
    match = re.search(r"/status/(\d+)", url)
    return match.group(1) if match else ""


def post_to_feed_item(post: Any, captured_at: str) -> dict[str, Any]:
    tweet_id = tweet_id_from_url(post.url)
    excerpt = clean_text(post.text, 300)
    return {
        "tweet_id": tweet_id,
        "account": post.handle,
        "url": post.url,
        "created_at": post.created_at.isoformat(),
        "text": excerpt,
        "text_excerpt_300": excerpt,
        "metrics": {
            "likes": post.likes,
            "replies": post.replies,
            "reposts": post.reposts,
            "captured_at": captured_at,
        },
        "source_type": "xreach",
        "is_retweet": False,
        "is_reply": False,
        "dedupe_key": tweet_id or post.url,
    }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the central X AI feed for feed-mode users.")
    parser.add_argument("--config", type=Path, default=SKILL_DIR / "references" / "config.example.json")
    parser.add_argument("--output", type=Path, default=SKILL_DIR / "feeds" / "x-ai-feed.json")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without writing feed file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = args.config.expanduser().resolve()
    config = load_json(config_path)
    if not config.get("auth_token_env"):
        config["auth_token_env"] = "XREACH_AUTH_TOKEN"
    if not config.get("ct0_env"):
        config["ct0_env"] = "XREACH_CT0"
    config.setdefault("max_workers", 4)
    config.setdefault("per_handle_count", 40)
    config.setdefault("fallback_count", 60)
    config.setdefault("request_timeout_seconds", 30)
    config.setdefault("xreach_timeout_ms", 30000)

    handles_path = resolve_config_path(str(config.get("handles_file") or "references/default-handles.txt"), config_path)
    handles = load_handles(handles_path)
    captured_at = datetime.now(TZ).isoformat()

    posts = []
    failures: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=max(1, int(config.get("max_workers") or 4))) as executor:
        future_map = {executor.submit(fetch_handle, handle, config): handle for handle in handles}
        for future in as_completed(future_map):
            handle, handle_posts, error = future.result()
            if error:
                failures[handle] = error
            posts.extend(handle_posts)

    posts.sort(key=lambda post: (post.created_at, post.likes), reverse=True)
    seen: set[str] = set()
    items: list[dict[str, Any]] = []
    for post in posts:
        item = post_to_feed_item(post, captured_at)
        key = item["dedupe_key"]
        if key in seen:
            continue
        seen.add(key)
        items.append(item)

    payload: dict[str, Any] = {
        "feed_generated_at": captured_at,
        "source_window_hours": int(config.get("lookback_hours") or 72),
        "accounts_total": len(handles),
        "accounts_succeeded": len(handles) - len(failures),
        "accounts_failed": len(failures),
        "posts_total": len(items),
        "source_type": "xreach",
        "items": items,
        "failures": failures,
    }

    if not args.dry_run:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "feed_generated_at": payload["feed_generated_at"],
                "accounts_total": payload["accounts_total"],
                "accounts_succeeded": payload["accounts_succeeded"],
                "accounts_failed": payload["accounts_failed"],
                "posts_total": payload["posts_total"],
                "output": str(args.output),
                "dry_run": args.dry_run,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
