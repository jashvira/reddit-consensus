<div align="center">

<img src="logo.png" alt="Reddit Consensus Agent" width="120" height="120">

# Reddit Consensus Agent

*An autonomous AI agent that provides tasteful insights by analyzing Reddit discussions and community feedback.*

[![PyPI version](https://badge.fury.io/py/reddit-consensus.svg)](https://badge.fury.io/py/reddit-consensus)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Rich Console](https://img.shields.io/badge/UI-Rich%20Console-orange.svg)](https://github.com/Textualize/rich)

</div>

---

## Features

- **Elegant Console UI**: Clean side-by-side dashboard with responsive layout
- **Async Parallel Tool Execution**: Uses asyncio for fast, concurrent Reddit API calls
- **Two-Phase Research**: Initial research followed by critical analysis
- **Community-Driven**: Analyzes real Reddit discussions and user opinions
- **Balanced Insights**: Provides both pros and cons based on community feedback
- **Configurable AI Models**: Uses `gpt-4.1-mini` by default, but supports other OpenAI models via [`config.py`](reddit_consensus/config.py)

## Architecture

- **Agent State Management**: Tracks research progress and findings
- **Reddit Tools**: Async tools for searching posts and analyzing comments
- **Prompt Templates**: Centralized prompts for consistent AI interactions
- **Parallel Processing**: Simultaneous tool execution for faster results

## Quick Start

### Installation
```bash
# Install from PyPI
pip install reddit-consensus

# Or clone and install from source
git clone https://github.com/jashvira/reddit-consensus.git
cd reddit-consensus
uv sync
```

### Interactive Session (Recommended)
```bash
# If installed from PyPI
ask-reddit

# If running from source
python ask_reddit.py
```

The interactive session will:
1. Check your API keys are set
2. Ask what you'd like insights on
3. Analyze Reddit discussions with elegant dashboard
4. Show balanced insights with pros/cons
5. Offer to answer another query

### Programmatic Usage
```python
import asyncio
from reddit_consensus.recommender import AutonomousRedditConsensus

async def main():
    agent = AutonomousRedditConsensus()
    result = await agent.process_query("Best cafes in Adelaide Hills")
    agent.print_results()

asyncio.run(main())
```

## Setup

### 1. Install Dependencies
```bash
uv sync
```

### 2. API Keys
Set these environment variables:

```bash
export OPENAI_API_KEY="your-openai-api-key"
export REDDIT_CLIENT_ID="your-reddit-client-id"
export REDDIT_CLIENT_SECRET="your-reddit-client-secret"
export REDDIT_USER_AGENT="YourApp/1.0 (by /u/yourusername)"
```

### 3. Get API Keys
- **OpenAI**: https://platform.openai.com/
- **Reddit**: https://www.reddit.com/prefs/apps/ (create "script" app)

## Requirements

- Python 3.11+
- OpenAI API access
- Reddit API credentials