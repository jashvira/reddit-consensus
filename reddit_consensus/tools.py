import json
import os
import asyncio
import asyncpraw
from abc import ABC, abstractmethod


class Tool(ABC):
    """Abstract base class for a tool that can be used by an agent."""

    @abstractmethod
    def name(self) -> str:
        """Returns the name of the tool."""
        pass

    @abstractmethod
    def description(self) -> str:
        """Returns a description of what the tool does."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Executes the tool with the given parameters."""
        pass

    @abstractmethod
    async def execute_async(self, **kwargs) -> str:
        """Executes the tool asynchronously with the given parameters."""
        pass


class _RedditTool(Tool):
    """Base class for Reddit tools, handles client initialization."""

    def __init__(self):
        """Initializes the Reddit client using credentials from environment variables."""
        client_id = os.getenv("REDDIT_CLIENT_ID")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        user_agent = os.getenv("REDDIT_USER_AGENT")

        if not all([client_id, client_secret, user_agent]):
            raise ValueError(
                "Reddit API credentials not found in environment variables"
            )

        # Store credentials for async client creation
        self._client_id = client_id
        self._client_secret = client_secret
        self._user_agent = user_agent

    async def _get_async_reddit(self):
        """Get async Reddit client - caller must close it."""
        return asyncpraw.Reddit(
            client_id=self._client_id,
            client_secret=self._client_secret,
            user_agent=self._user_agent,
        )


class RedditSearchForPostsTool(_RedditTool):
    """A tool for searching for posts on Reddit."""

    def name(self) -> str:
        """Returns the tool's name: 'reddit_search_for_posts'."""
        return "reddit_search_for_posts"

    def description(self) -> str:
        """Returns the tool's description."""
        return "Search for Reddit posts on a given topic. Returns a list of posts with their IDs."

    def execute(
        self, query: str, subreddit: str = "all", max_results: int = 5, **kwargs
    ) -> str:
        """Searches for Reddit posts synchronously (wrapper for async version)."""
        return asyncio.run(self.execute_async(query, subreddit, max_results, **kwargs))

    async def execute_async(
        self, query: str, subreddit: str = "all", max_results: int = 5, **kwargs
    ) -> str:
        """Searches for Reddit posts asynchronously.

        Args:
            query: The search query string.
            subreddit: The subreddit to search within. Defaults to "all".
            max_results: The maximum number of posts to return.

        Returns:
            A JSON string containing the search results.
        """
        async with asyncpraw.Reddit(
            client_id=self._client_id,
            client_secret=self._client_secret,
            user_agent=self._user_agent,
        ) as reddit:
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


class RedditGetCommentsTool(_RedditTool):
    """A tool for fetching the top comments from a specific Reddit post."""

    def name(self) -> str:
        """Returns the tool's name: 'reddit_get_post_comments'."""
        return "reddit_get_post_comments"

    def description(self) -> str:
        """Returns the tool's description."""
        return "Fetch the top comments for a specific Reddit post using its ID."

    def execute(self, post_id: str, max_comments: int = 5, **kwargs) -> str:
        """Fetches the top comments synchronously (wrapper for async version)."""
        return asyncio.run(self.execute_async(post_id, max_comments, **kwargs))

    async def execute_async(self, post_id: str, max_comments: int = 5, **kwargs) -> str:
        """Fetches the top comments for a given Reddit post asynchronously.

        Args:
            post_id: The ID of the post to fetch comments from.
            max_comments: The maximum number of top comments to return.

        Returns:
            A JSON string containing the top comments.
        """
        async with asyncpraw.Reddit(
            client_id=self._client_id,
            client_secret=self._client_secret,
            user_agent=self._user_agent,
        ) as reddit:
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
