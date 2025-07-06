# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a hobby MVP for a taste-driven recommendation system. It suggests gear, food, drinks, venues, media, etc. using an autonomous agent that searches the web and Reddit for current information.

## Development Environment

- Python 3.11+ required
- Dependencies managed via `uv` (see `pyproject.toml`)
- Primary development in Jupyter notebooks

### Common Commands

```bash
# Install dependencies
uv sync

# Start Jupyter
jupyter notebook

# Run the main recommender agent
jupyter execute agent.ipynb
```

## Architecture

Simple autonomous agent pattern:

1. **Query Processing**: Agent receives user query
2. **Autonomous Research**: Agent searches Reddit using available tools
3. **Synthesis**: Generates recommendations from search results

### Key Files

- `recommender.py`: Main agent class
- `agent_state.py`: State tracking 
- `tools.py`: Reddit tools
- `agent.ipynb`: Testing interface

## Usage

```python
from recommender import AutonomousTastefulRecommender

agent = AutonomousTastefulRecommender()
result = agent.process_query("I need a good hiking backpack under $200")
agent.print_results()
```

## Requirements

- `OPENAI_API_KEY`: OpenAI API access
- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`: Reddit API

Get API keys:
- OpenAI: https://platform.openai.com/
- Reddit: https://www.reddit.com/prefs/apps/