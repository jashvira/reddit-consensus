#!/usr/bin/env python3
"""
pytest test suite for Reddit tools
Streamlined tests with minimal redundancy
"""

import json

import pytest

from reddit_consensus.config import get_reddit_credentials
from reddit_consensus.recommender import AutonomousRedditConsensus
from reddit_consensus.tools import (
    _build_comment_tree,
    reddit_get_post_comments,
    reddit_search_for_posts,
)


@pytest.fixture
def agent():
    """Shared agent fixture to eliminate boilerplate"""
    return AutonomousRedditConsensus()


def assert_valid_json_response(result: str, min_length: int = 0) -> dict:
    """Helper to validate JSON response structure"""
    assert isinstance(result, str)
    assert len(result) >= min_length
    data = json.loads(result)
    assert isinstance(data, dict)
    assert "status" in data
    return data


async def get_valid_post_id() -> str:
    """Helper to get a valid post ID for comment testing"""
    result = await reddit_search_for_posts("python", max_results=1)
    data = json.loads(result)
    if data["results"]:
        return data["results"][0]["post_id"]
    pytest.skip("No posts found for comment testing")


class TestRedditTools:
    """Comprehensive testing of Reddit tools through agent"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "query,subreddit,max_results,min_length",
        [
            ("python", "all", 2, 500),  # Basic search with performance check
            ("", "all", 1, 0),  # Empty query
            ("programming", "Python", 2, 0),  # Specific subreddit
        ],
    )
    async def test_search_variations(
        self, agent, query, subreddit, max_results, min_length
    ):
        """Test search functionality with various parameters"""
        params = {"query": query, "max_results": max_results}
        if subreddit != "all":  # Only add subreddit if not default
            params["subreddit"] = subreddit

        result_list = await agent._execute_tools(
            [{"tool_name": "reddit_search_for_posts", "tool_params": params}],
            log_results=False,
        )

        result = result_list[0]["result"]
        data = assert_valid_json_response(result, min_length)
        assert data["count"] <= max_results

        if data["results"]:
            post = data["results"][0]
            # Test new fields are present
            required_fields = [
                "post_id",
                "title",
                "score",
                "url",
                "created_utc",
                "author",
                "subreddit",
            ]
            assert all(key in post for key in required_fields)
            # Verify timestamp is numeric
            assert isinstance(post["created_utc"], int | float)

    @pytest.mark.asyncio
    async def test_get_comments_with_subtree_flag(self, agent):
        """Test backward compatibility - include_subtree parameter was removed"""
        post_id = await get_valid_post_id()

        # This should work without any special flags since we always return tree format
        result_list = await agent._execute_tools(
            [
                {
                    "tool_name": "reddit_get_post_comments",
                    "tool_params": {"post_id": post_id, "max_comments": 3},
                }
            ],
            log_results=False,
        )

        result = result_list[0]["result"]
        data = assert_valid_json_response(result)

        # Should always return hierarchical structure now
        assert "comment_tree" in data
        assert isinstance(data["comment_tree"], list)
        assert "max_depth" in data
        # Test post timestamp fields
        assert "post_created_utc" in data
        assert "post_author" in data

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "tool_name,params,expected_error",
        [
            (
                "invalid_tool_name",
                {"query": "test"},
                "Tool invalid_tool_name not found",
            ),
            (
                "reddit_search_for_posts",
                {},
                "Error",
            ),  # Missing required query parameter
            ("reddit_get_post_comments", {}, "Error"),  # Missing required post_id
        ],
    )
    async def test_error_handling(self, agent, tool_name, params, expected_error):
        """Test error handling for various failure scenarios"""
        result_list = await agent._execute_tools(
            [{"tool_name": tool_name, "tool_params": params}], log_results=False
        )

        result = result_list[0]["result"]
        assert isinstance(result, str)
        assert expected_error in result

    @pytest.mark.asyncio
    async def test_direct_tool_functions(self):
        """Test calling tool functions directly"""
        # Test basic functionality
        result = await reddit_search_for_posts("python", max_results=1)
        data = assert_valid_json_response(result)

        # Verify new fields in search results
        if data.get("results"):
            post = data["results"][0]
            assert "created_utc" in post
            assert "author" in post
            assert "subreddit" in post

        # Test hierarchical comments function (now unified)
        post_id = await get_valid_post_id()
        result = await reddit_get_post_comments(post_id, max_comments=1, max_depth=2)
        data = assert_valid_json_response(result)
        assert "comment_tree" in data
        assert "post_created_utc" in data
        assert "post_author" in data

        # Test error handling
        with pytest.raises(TypeError):
            await reddit_search_for_posts()  # Missing required parameter

    @pytest.mark.asyncio
    async def test_invalid_post_comments(self, agent):
        """Test comment retrieval with invalid post ID"""
        result_list = await agent._execute_tools(
            [
                {
                    "tool_name": "reddit_get_post_comments",
                    "tool_params": {"post_id": "invalid_post_id", "max_comments": 2},
                }
            ],
            log_results=False,
        )

        result = result_list[0]["result"]
        data = json.loads(result)
        # Should handle gracefully, might return empty results or error
        assert "comments" in data or "error" in data.get("status", "")

    @pytest.mark.asyncio
    async def test_parallel_tool_execution(self, agent):
        """Test parallel execution including hierarchical comments"""
        post_id = await get_valid_post_id()

        # Execute multiple tools in parallel
        result_list = await agent._execute_tools(
            [
                {
                    "tool_name": "reddit_search_for_posts",
                    "tool_params": {"query": "python", "max_results": 1},
                },
                {
                    "tool_name": "reddit_get_post_comments",
                    "tool_params": {
                        "post_id": post_id,
                        "max_comments": 2,
                        "max_depth": 2,
                    },
                },
            ],
            log_results=False,
        )

        assert len(result_list) == 2

        # Verify both tools executed successfully
        search_result = next(
            r for r in result_list if r["tool_name"] == "reddit_search_for_posts"
        )
        comments_result = next(
            r for r in result_list if r["tool_name"] == "reddit_get_post_comments"
        )

        search_data = json.loads(search_result["result"])
        comments_data = json.loads(comments_result["result"])

        assert "results" in search_data
        assert "comment_tree" in comments_data or "error" in comments_data.get(
            "status", ""
        )

    def test_comment_tree_building_function(self):
        """Test the comment tree building helper function"""

        # Create a mock comment object
        class MockComment:
            def __init__(self, id, body, score, author=None, replies=None):
                self.id = id
                self.body = body
                self.score = score
                self.author = author
                self.replies = replies or []
                self.created_utc = 1234567890
                self.parent_id = f"parent_{id}"

        # Test basic comment structure
        comment = MockComment("123", "Test comment", 5, "testuser")
        result = _build_comment_tree(comment, max_depth=2)

        assert result["id"] == "123"
        assert result["text"] == "Test comment"
        assert result["score"] == 5
        assert result["author"] == "testuser"
        assert result["depth"] == 0
        assert result["replies"] == []
        assert result["reply_count"] == 0
        assert result["created_utc"] == 1234567890

    @pytest.mark.asyncio
    async def test_timestamp_data_consistency(self, agent):
        """Test that timestamp data is consistently captured across all tools"""
        post_id = await get_valid_post_id()

        # Test comment tool for timestamp consistency with different parameters
        tools_to_test = [
            ("reddit_get_post_comments", {}),
            ("reddit_get_post_comments", {"max_depth": 2}),
            ("reddit_get_post_comments", {"max_depth": 1}),
        ]

        for tool_name, extra_params in tools_to_test:
            params = {"post_id": post_id, "max_comments": 1, **extra_params}
            result_list = await agent._execute_tools(
                [{"tool_name": tool_name, "tool_params": params}], log_results=False
            )

            result = result_list[0]["result"]
            data = json.loads(result)

            # All tools should return post timestamp info and tree format
            if data.get("status") != "error":
                assert "post_created_utc" in data or "error" in data.get(
                    "status", ""
                ), f"Missing post timestamp in {tool_name}"
                assert "post_author" in data or "error" in data.get("status", ""), (
                    f"Missing post author in {tool_name}"
                )
                assert "comment_tree" in data or "error" in data.get("status", ""), (
                    f"Missing comment_tree in {tool_name}"
                )

    def test_credential_management(self):
        """Test centralized credential management"""
        # Test that the function exists and can be called
        try:
            credentials = get_reddit_credentials()
            assert isinstance(credentials, dict)
            required_keys = ["client_id", "client_secret", "user_agent"]
            assert all(key in credentials for key in required_keys)
        except ValueError as e:
            # If credentials are missing, that's expected in test environment
            assert "Reddit API credentials not found" in str(e)

    def test_validation_script(self):
        """Test configuration validation script functionality"""
        import io
        import sys
        from unittest.mock import patch

        from reddit_consensus.validate_config import main

        # Capture stdout to check validation output
        captured_output = io.StringIO()
        with patch("sys.stdout", captured_output):
            try:
                result = main()
                output = captured_output.getvalue()

                # Should contain validation messages
                assert "Validating Reddit Consensus Configuration" in output

                # Result should be boolean
                assert isinstance(result, bool)

            except SystemExit as e:
                # Script may exit with code 0 or 1, both are valid test outcomes
                assert e.code in [0, 1]
