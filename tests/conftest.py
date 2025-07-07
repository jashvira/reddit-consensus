"""
pytest configuration file
Shared fixtures and settings for all tests
"""

import os
import sys

import pytest

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Global test configuration
pytest_plugins = []


# Async test configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    yield loop
    # Don't close the loop if it's still running
    if not loop.is_closed():
        loop.close()


# Environment setup
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment"""
    # Ensure we're running tests
    os.environ["TESTING"] = "1"

    # Check for required environment variables
    required_env_vars = [
        "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET",
        "REDDIT_USER_AGENT",
        "OPENAI_API_KEY",
    ]

    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        pytest.skip(f"Missing required environment variables: {missing_vars}")

    yield

    # Cleanup
    os.environ.pop("TESTING", None)


# Test data fixtures
@pytest.fixture
def sample_reddit_query():
    """Sample Reddit search query for testing"""
    return "python programming"


@pytest.fixture
def sample_search_params():
    """Sample search parameters"""
    return {"query": "test query", "max_results": 2, "subreddit": "all"}


@pytest.fixture
def sample_comment_params():
    """Sample comment retrieval parameters"""
    return {"post_id": "test_id", "max_comments": 3}
