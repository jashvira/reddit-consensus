# Reddit Consensus

An autonomous AI agent that provides tasteful recommendations by analyzing Reddit discussions and community feedback.

## Features

- **Async Parallel Tool Execution**: Uses asyncio for fast, concurrent Reddit API calls
- **Two-Phase Research**: Initial research followed by critical analysis
- **Community-Driven**: Analyzes real Reddit discussions and user opinions
- **Balanced Recommendations**: Provides both pros and cons based on community feedback

## Architecture

- **Agent State Management**: Tracks research progress and findings
- **Reddit Tools**: Async tools for searching posts and analyzing comments
- **Prompt Templates**: Centralized prompts for consistent AI interactions
- **Parallel Processing**: Simultaneous tool execution for faster results

## Usage

```python
from reddit_consensus.recommender import AutonomousRedditConsensus

agent = AutonomousRedditConsensus()
result = agent.process_query("Best cafes in Adelaide Hills")
agent.print_results()
```

## Requirements

- Python 3.8+
- OpenAI API key
- Reddit API credentials
- Dependencies listed in pyproject.toml