import json
from typing import Any

import asyncpraw

from .config import (
    DEFAULT_ADAPTIVE_PERCENTILE,
    DEFAULT_MAX_COMMENTS,
    DEFAULT_MAX_DEPTH,
    DEFAULT_REPLACE_MORE_LIMIT,
    DEFAULT_SORT_BY_SCORE,
    get_reddit_credentials,
)


def _calculate_score_threshold(scores: list[int], percentile: int = DEFAULT_ADAPTIVE_PERCENTILE) -> int:
    """Calculate adaptive score threshold based on percentile of all scores."""
    if not scores:
        return 0
    
    sorted_scores = sorted(scores)
    threshold_index = len(sorted_scores) * percentile // 100
    return max(0, sorted_scores[threshold_index])


def _has_high_scoring_descendant(comment, threshold: int) -> bool:
    """Check if comment or any of its descendants meets the score threshold."""
    if comment.score >= threshold:
        return True
    
    if hasattr(comment, "replies") and comment.replies:
        for reply in comment.replies:
            if hasattr(reply, "body") and _has_high_scoring_descendant(reply, threshold):
                return True
    
    return False


def _build_comment_tree(
    comment, max_depth: int = DEFAULT_MAX_DEPTH, current_depth: int = 0, 
    score_threshold: int = 0, sort_by_score: bool = DEFAULT_SORT_BY_SCORE
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
            # Filter and sort replies by score
            valid_replies = []
            for reply in comment.replies:
                if hasattr(reply, "body") and reply.score >= score_threshold:
                    valid_replies.append(reply)
            
            # Sort replies by score if enabled
            if sort_by_score:
                valid_replies.sort(key=lambda x: x.score, reverse=True)
            
            # Build tree for filtered/sorted replies
            for reply in valid_replies:
                reply_data = _build_comment_tree(
                    reply, max_depth, current_depth + 1, score_threshold, sort_by_score
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
    adaptive_filtering: bool = True,
    sort_by_score: bool = DEFAULT_SORT_BY_SCORE,
) -> str:
    """Fetch comments for a Reddit post with hierarchical tree structure.

    Args:
        post_id: The ID of the post to fetch comments from.
        max_comments: The maximum number of top-level comments to return.
        max_depth: Maximum depth of comment tree to fetch (default: 3).
        include_all_replies: If True, fetch all replies regardless of max_comments limit.
        adaptive_filtering: Use adaptive score-based filtering (default: True).
        sort_by_score: Sort comments by score instead of chronological (default: True).

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

            # Collect all comments for adaptive filtering
            all_comments = []
            all_scores = []
            
            def collect_scores(comment_obj):
                """Recursively collect all comment scores."""
                if hasattr(comment_obj, "body"):
                    all_scores.append(comment_obj.score)
                    if hasattr(comment_obj, "replies") and comment_obj.replies:
                        for reply in comment_obj.replies:
                            collect_scores(reply)
            
            # First pass: collect all comments and scores
            for comment in submission.comments:
                if hasattr(comment, "body"):
                    all_comments.append(comment)
                    collect_scores(comment)
            
            # Calculate adaptive threshold
            score_threshold = 0
            if adaptive_filtering and all_scores:
                score_threshold = _calculate_score_threshold(all_scores)
            
            # Filter and sort top-level comments (include if comment OR any descendant is high-scoring)
            valid_comments = []
            for comment in all_comments:
                if adaptive_filtering:
                    if _has_high_scoring_descendant(comment, score_threshold):
                        valid_comments.append(comment)
                else:
                    valid_comments.append(comment)
            
            # Sort comments by score if enabled
            if sort_by_score:
                valid_comments.sort(key=lambda x: x.score, reverse=True)
            
            # Build comment tree with filtered/sorted comments
            comments_tree = []
            comment_count = 0

            for comment in valid_comments:
                comment_data = _build_comment_tree(comment, max_depth, 0, score_threshold, sort_by_score)
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
                    "adaptive_filtering": adaptive_filtering,
                    "score_threshold": score_threshold,
                    "total_scores_analyzed": len(all_scores),
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
