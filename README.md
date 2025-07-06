# Reddit Consensus

An autonomous AI agent that provides tasteful recommendations by analyzing Reddit discussions and community feedback.

## Features

- **Elegant Console UI**: Clean side-by-side dashboard with responsive layout
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
import asyncio
from reddit_consensus.recommender import AutonomousRedditConsensus

async def main():
    agent = AutonomousRedditConsensus()
    result = await agent.process_query("Best cafes in Adelaide Hills")
    agent.print_results()

asyncio.run(main())
```

## Requirements

- Python 3.11+
- OpenAI API key (`OPENAI_API_KEY`)
- Reddit API credentials (`REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`)
- Dependencies managed via `uv sync`