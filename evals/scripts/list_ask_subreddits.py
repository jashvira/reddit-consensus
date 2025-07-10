#!/usr/bin/env python
"""
list_ask_subreddits.py ────────────────────────────────────────────────────────
Find and print sub‑reddits whose names start with "Ask" (case‑insensitive).
Uses the official Reddit API via **PRAW** and the broader subreddits.search() method.

Minimal usage (after exporting env variables):
    REDDIT_CLIENT_ID=... \
    REDDIT_CLIENT_SECRET=... \
    USER_AGENT="ask-finder/0.1 by <you>" \
    python scripts/list_ask_subreddits.py --min-subs 1000 --limit 100

Arguments
─────────
--min-subs   Minimum subscriber count (default 1 000) 
--limit      Max number of subs returned (default 100)
--out        Optional text file path to save the subreddit names

The script prints a sorted table: name, subscribers, over‑18 flag, title.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import List, Tuple

try:
    import praw  # type: ignore
except ImportError as e:
    sys.exit("praw not installed.  Run: pip install praw")

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def get_reddit_instance() -> "praw.Reddit":
    cid     = os.getenv("REDDIT_CLIENT_ID")
    secret  = os.getenv("REDDIT_CLIENT_SECRET")
    agent   = os.getenv("USER_AGENT", "ask-finder/0.1")
    if not cid or not secret:
        sys.exit("Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET env vars.")
    return praw.Reddit(client_id=cid, client_secret=secret, user_agent=agent)


def find_ask_subs(reddit: "praw.Reddit", min_subs: int, limit: int) -> List[Tuple[str, int, bool, str]]:
    """Return [(name, subscribers, over18, title)]."""
    subs: List[Tuple[str, int, bool, str]] = []
    found_names = set()
    
    # Use the broader subreddits.search() method
    print("Searching for Ask subreddits...")
    for sr in reddit.subreddits.search('ask', limit=limit):
        name = sr.display_name
        if not name.lower().startswith("ask"):
            continue
        if sr.subscribers < min_subs:
            continue
        if name in found_names:
            continue
            
        found_names.add(name)
        subs.append((name, sr.subscribers, sr.over18, sr.title))
        print(f"Found: {name} ({sr.subscribers:,} subs)")
    
    # Also try some additional search patterns
    additional_patterns = ['subreddit:ask', 'askscience', 'askengineers']
    for pattern in additional_patterns:
        try:
            for sr in reddit.subreddits.search(pattern, limit=50):
                name = sr.display_name
                if not name.lower().startswith("ask"):
                    continue
                if sr.subscribers < min_subs:
                    continue
                if name in found_names:
                    continue
                    
                found_names.add(name)
                subs.append((name, sr.subscribers, sr.over18, sr.title))
                print(f"Found (additional): {name} ({sr.subscribers:,} subs)")
        except Exception as e:
            print(f"Warning: Error with pattern '{pattern}': {e}")
    
    # Sort by subscribers desc
    subs.sort(key=lambda x: -x[1])
    return subs


def print_table(rows: List[Tuple[str, int, bool, str]]):
    if not rows:
        print("No sub-reddits matched the criteria.")
        return
    # table header
    print(f"\n{'Name':<25s} {'Subs':>8s} {'18+':>4s}  Title")
    print("-" * 80)
    for name, subs, over, title in rows:
        t = (title[:60] + "…") if len(title) > 60 else title
        print(f"{name:<25s} {subs:>8,d} {'Y' if over else 'N':>4s}  {t}")


def save_names_txt(rows: List[Tuple[str, int, bool, str]], path: str):
    """Save just the subreddit names to a text file, one per line."""
    with open(path, "w", encoding="utf-8") as fh:
        for name, _, _, _ in rows:
            fh.write(f"{name}\n")
    print(f"Saved {len(rows)} subreddit names → {path}")


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="List Ask* sub-reddits via PRAW.")
    p.add_argument("--min-subs", type=int, default=1_000, help="Minimum subscriber count (default 1 000).")
    p.add_argument("--limit", type=int, default=100, help="Maximum number of results (default 100).")
    p.add_argument("--out", help="Optional text file output path for subreddit names.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    reddit = get_reddit_instance()
    rows = find_ask_subs(reddit, min_subs=args.min_subs, limit=args.limit)
    print_table(rows)
    if args.out:
        save_names_txt(rows, args.out)


if __name__ == "__main__":
    main()