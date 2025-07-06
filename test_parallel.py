#!/usr/bin/env python3

"""
Test script for async parallel tool execution
Run this outside Jupyter to avoid event loop conflicts
"""

import sys
import os
import asyncio

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from reddit_consensus.recommender import AutonomousRedditConsensus
from reddit_consensus.colors import print_colored

async def main():
    print_colored("TEST", "Testing Async Parallel Tool Execution")
    print("=" * 60)

    # Create recommender
    agent = AutonomousRedditConsensus()

    # Test query
    query = "best wine bars in adelaide"

    try:
        # Run the query
        result = await agent.process_query(query)

        print("\n" + "=" * 60)
        print_colored("SUCCESS", "Parallel execution completed")
        print(f"Total steps: {result['steps']}")
        print(f"Recommendations found: {len(result['recommendations'])}")

        # Show results
        agent.print_results()

    except Exception as e:
        print_colored("ERROR", f"\n{e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())