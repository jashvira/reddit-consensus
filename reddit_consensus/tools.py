import json
import os
import asyncio
import asyncpraw
from typing import Dict, Any, List


def _get_reddit_credentials() -> Dict[str, str]:
    """Get Reddit API credentials from environment variables."""
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT")

    if not all([client_id, client_secret, user_agent]):
        raise ValueError(
            "Reddit API credentials not found in environment variables"
        )

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "user_agent": user_agent,
    }


async def reddit_search_for_posts(
    query: str, subreddit: str = "all", max_results: int = 5
) -> str:
    """Search for Reddit posts on a given topic. Returns a list of posts with their IDs.
    
    Args:
        query: The search query string.
        subreddit: The subreddit to search within. Defaults to "all".
        max_results: The maximum number of posts to return.
    
    Returns:
        A JSON string containing the search results.
    """
    credentials = _get_reddit_credentials()
    
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


async def reddit_get_post_comments(post_id: str, max_comments: int = 5) -> str:
    """Fetch the top comments for a specific Reddit post using its ID.
    
    Args:
        post_id: The ID of the post to fetch comments from.
        max_comments: The maximum number of top comments to return.
    
    Returns:
        A JSON string containing the top comments.
    """
    credentials = _get_reddit_credentials()
    
    async with asyncpraw.Reddit(**credentials) as reddit:
        try:
            submission = await reddit.submission(id=post_id)
            submission.comment_sort = "top"
            await submission.comments.replace_more(limit=0)

            top_comments_data = []
            comment_list = await submission.comments.list()
            for comment in comment_list[:max_comments]:
                top_comments_data.append({"text": comment.body, "score": comment.score})

            return json.dumps(
                {
                    "post_id": post_id,
                    "post_title": submission.title,
                    "status": "success",
                    "comments": top_comments_data,
                },
                indent=2,
            )

        except Exception as e:
            return json.dumps(
                {
                    "post_id": post_id,
                    "status": "error",
                    "error": str(e),
                    "comments": [],
                },
                indent=2,
            )


# Clean async tools - no sync wrappers needed
