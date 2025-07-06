"""
Configuration constants for the Reddit Consensus system.
Centralized configuration for easy maintenance and tuning.
"""

# Comment tree depth configuration
DEFAULT_MAX_DEPTH = 3  # Maximum depth for comment tree traversal
DEFAULT_MAX_COMMENTS = 5  # Maximum number of comments/posts to fetch by default
DEFAULT_REPLACE_MORE_LIMIT = 3  # Limit for replacing "more comments" objects

# Search configuration
DEFAULT_SEARCH_RESULTS = 5  # Default number of search results to return

# UI configuration
DEFAULT_UI_TREE_DISPLAY_DEPTH = 2  # Maximum depth to display in UI tree view
DEFAULT_UI_COMMENT_PREVIEW_LENGTH = 60  # Maximum length for comment preview text
DEFAULT_UI_TITLE_PREVIEW_LENGTH = 40  # Maximum length for title preview text

# Performance configuration
DEFAULT_TIMEOUT_SECONDS = 30  # Default timeout for Reddit API calls
DEFAULT_RETRY_ATTEMPTS = 3  # Number of retry attempts for failed requests

# LLM configuration
DEFAULT_REASONING_STEPS_LIMIT = 10  # Maximum reasoning steps before forcing finalization
DEFAULT_MINIMUM_SOURCES = 5  # Minimum sources to collect before finalizing