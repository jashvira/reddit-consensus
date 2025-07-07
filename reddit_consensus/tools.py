import json
from typing import Any

import asyncpraw

from .config import (
    DEFAULT_MAX_COMMENTS,
    DEFAULT_MAX_DEPTH,
    DEFAULT_REPLACE_MORE_LIMIT,
    get_reddit_credentials,
)


def _build_comment_tree(
    comment, max_depth: int = DEFAULT_MAX_DEPTH, current_depth: int = 0
) -> dict[str, Any]:
    """Recursively build comment tree structure preserving Reddit hierarchy."""
    comment_data = {
        "id": comment.id,
        "text": comment.body,
        "score": comment.score,
        "depth": current_depth,
        "author": str(comment.author) if comment.author else "[deleted]",
        "created_utc": comment.created_utc,
        "parent_id": comment.parent_id,
        "replies": [],
        "is_expanded": False,
        "reply_count": 0,
    }

    # Process replies if within depth limit
    if current_depth < max_depth and hasattr(comment, "replies") and comment.replies:
        try:
            for reply in comment.replies:
                if hasattr(reply, "body"):  # Skip MoreComments objects
                    reply_data = _build_comment_tree(
                        reply, max_depth, current_depth + 1
                    )
                    comment_data["replies"].append(reply_data)

            comment_data["reply_count"] = len(comment_data["replies"])
        except Exception:
            pass  # Skip problematic replies

    return comment_data


async def reddit_get_post_comments(
    post_id: str,
    max_comments: int = DEFAULT_MAX_COMMENTS,
    max_depth: int = DEFAULT_MAX_DEPTH,
    include_all_replies: bool = False,
) -> str:
    """Fetch comments for a Reddit post with hierarchical tree structure.

    Args:
        post_id: The ID of the post to fetch comments from.
        max_comments: The maximum number of top-level comments to return.
        max_depth: Maximum depth of comment tree to fetch (default: 3).
        include_all_replies: If True, fetch all replies regardless of max_comments limit.

    Returns:
        A JSON string containing the hierarchical comment tree.
    """
    credentials = get_reddit_credentials()

    async with asyncpraw.Reddit(**credentials) as reddit:
        try:
            submission = await reddit.submission(id=post_id)
            await submission.load()

            # Replace "more comments" with actual comments, but limit for performance
            await submission.comments.replace_more(
                limit=0 if include_all_replies else DEFAULT_REPLACE_MORE_LIMIT
            )

            # Build comment tree
            comments_tree = []
            comment_count = 0

            for comment in submission.comments:
                if hasattr(comment, "body"):  # Skip MoreComments objects
                    comment_data = _build_comment_tree(comment, max_depth, 0)
                    comments_tree.append(comment_data)
                    comment_count += 1

                    if not include_all_replies and comment_count >= max_comments:
                        break

            return json.dumps(
                {
                    "post_id": post_id,
                    "post_title": submission.title,
                    "post_created_utc": submission.created_utc,
                    "post_author": str(submission.author)
                    if submission.author
                    else "[deleted]",
                    "status": "success",
                    "comment_tree": comments_tree,
                    "total_comments": len(comments_tree),
                    "max_depth": max_depth,
                },
                indent=2,
            )

        except Exception as e:
            return json.dumps(
                {
                    "post_id": post_id,
                    "status": "error",
                    "error": str(e),
                    "comment_tree": [],
                },
                indent=2,
            )


async def reddit_search_for_posts(
    query: str, subreddit: str = "all", max_results: int = DEFAULT_MAX_COMMENTS
) -> str:
    """Search for Reddit posts on a given topic. Returns a list of posts with their IDs.

    Args:
        query: The search query string.
        subreddit: The subreddit to search within. Defaults to "all".
        max_results: The maximum number of posts to return.

    Returns:
        A JSON string containing the search results.
    """
    credentials = get_reddit_credentials()

    async with asyncpraw.Reddit(**credentials) as reddit:
        try:
            subreddit_obj = await reddit.subreddit(subreddit)

            results = []
            async for submission in subreddit_obj.search(query, limit=max_results):
                results.append(
                    {
                        "post_id": submission.id,
                        "title": submission.title,
                        "score": submission.score,
                        "num_comments": submission.num_comments,
                        "upvote_ratio": submission.upvote_ratio,
                        "url": f"https://reddit.com{submission.permalink}",
                        "snippet": (
                            submission.selftext[:200] + "..."
                            if submission.selftext
                            else ""
                        ),
                        "created_utc": submission.created_utc,
                        "author": str(submission.author)
                        if submission.author
                        else "[deleted]",
                        "subreddit": str(submission.subreddit),
                    }
                )

            return json.dumps(
                {
                    "query": query,
                    "status": "success",
                    "results": results,
                    "count": len(results),
                },
                indent=2,
            )

        except Exception as e:
            return json.dumps(
                {"query": query, "status": "error", "error": str(e), "results": []},
                indent=2,
            )


# Clean async tools - no sync wrappers needed
