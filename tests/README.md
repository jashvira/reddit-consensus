# Tests

This directory contains the test suite for the Reddit Consensus project.

## Running Tests

From the project root:

```bash
# Run all tests
python -m pytest tests/

# Run with verbose output
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_tools.py

# Run specific test class
python -m pytest tests/test_tools.py::TestRedditTools

# Run specific test
python -m pytest tests/test_tools.py::TestRedditTools::test_search_variations
```

## Test Structure

- `conftest.py` - Shared pytest configuration and fixtures
- `test_tools.py` - Tests for Reddit tools and agent functionality
- `pytest.ini` - Pytest configuration

## Test Categories

**TestRedditCredentials**:
- Reddit API credential validation
- Environment variable handling

**TestRedditTools**:
- Search functionality with various parameters
- Comment retrieval from posts
- Error handling for invalid inputs
- Tool execution through agent interface
- Direct tool function testing

## Requirements

Tests require the following environment variables:
- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET` 
- `REDDIT_USER_AGENT`
- `OPENAI_API_KEY`

## Test Features

- Async testing with proper `@pytest.mark.asyncio` decorators
- Parametrized tests for testing multiple scenarios efficiently
- Shared fixtures to reduce test setup overhead
- Comprehensive error handling validation