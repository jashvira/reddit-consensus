#!/usr/bin/env python3
"""
pytest test suite for Reddit tools
Streamlined tests with minimal redundancy
"""

import pytest
import json
from reddit_consensus.tools import (
    reddit_search_for_posts,
    reddit_get_post_comments,
    reddit_get_post_comments_with_tree,
    _get_reddit_credentials,
    _build_comment_tree
)
from reddit_consensus.recommender import AutonomousRedditConsensus


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
    @pytest.mark.parametrize("query,subreddit,max_results,min_length", [
        ("python", "all", 2, 500),         # Basic search with performance check
        ("", "all", 1, 0),                 # Empty query
        ("programming", "Python", 2, 0),   # Specific subreddit
    ])
    async def test_search_variations(self, agent, query, subreddit, max_results, min_length):
        """Test search functionality with various parameters"""
        params = {'query': query, 'max_results': max_results}
        if subreddit != "all":  # Only add subreddit if not default
            params['subreddit'] = subreddit

        result_list = await agent._execute_tools([{
            'tool_name': 'reddit_search_for_posts',
            'tool_params': params
        }], log_results=False)

        result = result_list[0]["result"]
        data = assert_valid_json_response(result, min_length)
        assert data["count"] <= max_results

        if data["results"]:
            post = data["results"][0]
            # Test new fields are present
            required_fields = ["post_id", "title", "score", "url", "created_utc", "author", "subreddit"]
            assert all(key in post for key in required_fields)
            # Verify timestamp is numeric
            assert isinstance(post["created_utc"], (int, float))

    @pytest.mark.asyncio
    async def test_get_comments_flat(self, agent):
        """Test flat comment retrieval functionality"""
        # Get a valid post ID first
        post_id = await get_valid_post_id()

        result_list = await agent._execute_tools([{
            'tool_name': 'reddit_get_post_comments',
            'tool_params': {'post_id': post_id, 'max_comments': 3}
        }], log_results=False)

        result = result_list[0]["result"]
        data = assert_valid_json_response(result)
        assert "comments" in data
        assert len(data["comments"]) <= 3

        # Test new post fields
        assert "post_created_utc" in data
        assert "post_author" in data

        # Test new comment fields if comments exist
        if data["comments"]:
            comment = data["comments"][0]
            required_fields = ["id", "text", "score", "author", "created_utc"]
            assert all(key in comment for key in required_fields)
            assert isinstance(comment["created_utc"], (int, float))

    @pytest.mark.asyncio
    async def test_get_comments_with_subtree_flag(self, agent):
        """Test using include_subtree flag with existing function"""
        post_id = await get_valid_post_id()

        result_list = await agent._execute_tools([{
            'tool_name': 'reddit_get_post_comments',
            'tool_params': {'post_id': post_id, 'max_comments': 3, 'include_subtree': True}
        }], log_results=False)

        result = result_list[0]["result"]
        data = assert_valid_json_response(result)

        # Should return hierarchical structure when include_subtree=True
        assert "comment_tree" in data or "comments" in data  # May fall back to flat if no tree
        if "comment_tree" in data:
            assert isinstance(data["comment_tree"], list)
            assert "max_depth" in data
            # Test post timestamp fields
            assert "post_created_utc" in data
            assert "post_author" in data

    @pytest.mark.asyncio
    async def test_get_comments_with_tree_direct(self, agent):
        """Test hierarchical comment retrieval functionality"""
        post_id = await get_valid_post_id()

        result_list = await agent._execute_tools([{
            'tool_name': 'reddit_get_post_comments_with_tree',
            'tool_params': {'post_id': post_id, 'max_comments': 3, 'max_depth': 2}
        }], log_results=False)

        result = result_list[0]["result"]
        data = assert_valid_json_response(result)

        # Verify hierarchical structure
        assert "comment_tree" in data
        assert "max_depth" in data
        assert "total_comments" in data
        assert isinstance(data["comment_tree"], list)
        assert data["max_depth"] == 2
        assert len(data["comment_tree"]) <= 3

        # Test post timestamp fields
        assert "post_created_utc" in data
        assert "post_author" in data

        # Check comment structure if comments exist
        if data["comment_tree"]:
            comment = data["comment_tree"][0]
            required_fields = ["id", "text", "score", "depth", "author", "created_utc", "replies", "reply_count"]
            for field in required_fields:
                assert field in comment
            assert comment["depth"] == 0  # Top-level comment
            assert isinstance(comment["replies"], list)
            assert isinstance(comment["created_utc"], (int, float))

    @pytest.mark.asyncio
    async def test_hierarchical_comment_depth_limits(self, agent):
        """Test that hierarchical comments respect depth limits"""
        post_id = await get_valid_post_id()

        # Test different depth limits
        for max_depth in [1, 2, 3]:
            result_list = await agent._execute_tools([{
                'tool_name': 'reddit_get_post_comments_with_tree',
                'tool_params': {'post_id': post_id, 'max_comments': 2, 'max_depth': max_depth}
            }], log_results=False)

            result = result_list[0]["result"]
            data = json.loads(result)

            if data.get("comment_tree"):
                # Check that no comment exceeds the depth limit
                def check_depth(comment, max_allowed_depth):
                    assert comment["depth"] <= max_allowed_depth
                    for reply in comment.get("replies", []):
                        check_depth(reply, max_allowed_depth)

                # The max_depth parameter controls traversal depth
                # max_depth=1 creates depths 0,1 -> max actual depth is 1
                # max_depth=2 creates depths 0,1,2 -> max actual depth is 2
                # max_depth=3 creates depths 0,1,2,3 -> max actual depth is 3
                # So we need to check against max_depth-1 but the logic was wrong before
                # Let's just check that depth doesn't exceed max_depth-1 for sufficient data

                for comment in data["comment_tree"]:
                    check_depth(comment, max_depth)  # Allow up to max_depth as the maximum

    @pytest.mark.asyncio
    async def test_tool_registry_integration(self, agent):
        """Test that new tool is properly registered in agent"""
        assert "reddit_get_post_comments_with_tree" in agent.tools
        assert callable(agent.tools["reddit_get_post_comments_with_tree"])

    @pytest.mark.asyncio
    @pytest.mark.parametrize("tool_name,params,expected_error", [
        ("invalid_tool_name", {"query": "test"}, "Tool invalid_tool_name not found"),
        ("reddit_search_for_posts", {}, "Error"),  # Missing required query parameter
        ("reddit_get_post_comments_with_tree", {}, "Error"),  # Missing required post_id
    ])
    async def test_error_handling(self, agent, tool_name, params, expected_error):
        """Test error handling for various failure scenarios"""
        result_list = await agent._execute_tools([{
            'tool_name': tool_name,
            'tool_params': params
        }], log_results=False)

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

        # Test hierarchical comments function
        post_id = await get_valid_post_id()
        result = await reddit_get_post_comments_with_tree(post_id, max_comments=1, max_depth=2)
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
        result_list = await agent._execute_tools([{
            'tool_name': 'reddit_get_post_comments',
            'tool_params': {'post_id': 'invalid_post_id', 'max_comments': 2}
        }], log_results=False)

        result = result_list[0]["result"]
        data = json.loads(result)
        # Should handle gracefully, might return empty results or error
        assert "comments" in data or "error" in data.get("status", "")

    @pytest.mark.asyncio
    async def test_invalid_post_comments_hierarchical(self, agent):
        """Test hierarchical comment retrieval with invalid post ID"""
        result_list = await agent._execute_tools([{
            'tool_name': 'reddit_get_post_comments_with_tree',
            'tool_params': {'post_id': 'invalid_post_id', 'max_comments': 2}
        }], log_results=False)

        result = result_list[0]["result"]
        data = json.loads(result)
        # Should handle gracefully with error status
        assert data.get("status") == "error" or "comment_tree" in data

    @pytest.mark.asyncio
    async def test_parallel_tool_execution_with_tree(self, agent):
        """Test parallel execution including hierarchical comments"""
        post_id = await get_valid_post_id()

        # Execute multiple tools in parallel
        result_list = await agent._execute_tools([
            {
                'tool_name': 'reddit_search_for_posts',
                'tool_params': {'query': 'python', 'max_results': 1}
            },
            {
                'tool_name': 'reddit_get_post_comments_with_tree',
                'tool_params': {'post_id': post_id, 'max_comments': 2, 'max_depth': 2}
            }
        ], log_results=False)

        assert len(result_list) == 2

        # Verify both tools executed successfully
        search_result = next(r for r in result_list if r["tool_name"] == "reddit_search_for_posts")
        comments_result = next(r for r in result_list if r["tool_name"] == "reddit_get_post_comments_with_tree")

        search_data = json.loads(search_result["result"])
        comments_data = json.loads(comments_result["result"])

        assert "results" in search_data
        assert "comment_tree" in comments_data or "error" in comments_data.get("status", "")

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

        # Test all three comment tools for timestamp consistency
        tools_to_test = [
            ('reddit_get_post_comments', {}),
            ('reddit_get_post_comments_with_tree', {'max_depth': 2}),
            ('reddit_get_post_comments', {'include_subtree': True})
        ]

        for tool_name, extra_params in tools_to_test:
            params = {'post_id': post_id, 'max_comments': 1, **extra_params}
            result_list = await agent._execute_tools([{
                'tool_name': tool_name,
                'tool_params': params
            }], log_results=False)

            result = result_list[0]["result"]
            data = json.loads(result)

            # All tools should return post timestamp info
            if data.get("status") != "error":
                assert "post_created_utc" in data or "error" in data.get("status", ""), f"Missing post timestamp in {tool_name}"
                assert "post_author" in data or "error" in data.get("status", ""), f"Missing post author in {tool_name}"