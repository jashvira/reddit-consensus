#!/usr/bin/env python3
"""
pytest test suite for Reddit tools
Streamlined tests with minimal redundancy
"""

import pytest
import json
from reddit_consensus.tools import reddit_search_for_posts, reddit_get_post_comments, _get_reddit_credentials
from reddit_consensus.recommender import AutonomousRedditConsensus


@pytest.fixture
def agent():
    """Shared agent fixture to eliminate boilerplate"""
    return AutonomousRedditConsensus()


def assert_valid_json_response(result: str, min_length: int = 0):
    """Shared assertion for JSON response validation"""
    assert isinstance(result, str)
    data = json.loads(result)
    assert data["status"] == "success"
    if min_length:
        assert len(result) > min_length
    return data


async def get_valid_post_id() -> str:
    """Helper to get a valid post ID for comment testing"""
    result = await reddit_search_for_posts("python", max_results=1)
    data = json.loads(result)
    if data["results"]:
        return data["results"][0]["post_id"]
    pytest.skip("No posts found for comment testing")


class TestRedditCredentials:
    """Test Reddit API credentials"""
    
    def test_get_reddit_credentials_success(self):
        """Test successful credential retrieval"""
        credentials = _get_reddit_credentials()
        assert isinstance(credentials, dict)
        assert all(key in credentials for key in ["client_id", "client_secret", "user_agent"])
        assert all(credentials.values())

    def test_get_reddit_credentials_missing_env(self, monkeypatch):
        """Test error when credentials missing"""
        monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
        monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("REDDIT_USER_AGENT", raising=False)
        
        with pytest.raises(ValueError, match="Reddit API credentials not found"):
            _get_reddit_credentials()


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
            assert all(key in post for key in ["post_id", "title", "score", "url"])

    @pytest.mark.asyncio
    async def test_get_comments(self, agent):
        """Test comment retrieval functionality"""
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

    @pytest.mark.asyncio
    @pytest.mark.parametrize("tool_name,params,expected_error", [
        ("invalid_tool_name", {"query": "test"}, "Tool invalid_tool_name not found"),
        ("reddit_search_for_posts", {}, "Error"),  # Missing required query parameter
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
        assert_valid_json_response(result)
        
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

    def test_agent_creation(self, agent):
        """Test agent creation and tool description"""
        assert isinstance(agent, AutonomousRedditConsensus)
        
        descriptions = agent._get_tools_description()
        assert isinstance(descriptions, str)
        assert "reddit_search_for_posts" in descriptions
        assert "reddit_get_post_comments" in descriptions