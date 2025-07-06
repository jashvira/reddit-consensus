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

async def main():
    print("🚀 Testing Async Parallel Tool Execution")
    print("=" * 60)

    # Create recommender
    agent = AutonomousRedditConsensus()

    # Test query
    query = "Best cafes in the adelaide hills"

    try:
        # Run the query
        result = await agent.process_query(query)

        print("\n" + "=" * 60)
        print("✅ SUCCESS! Parallel execution completed")
        print(f"Total steps: {result['steps']}")
        print(f"Recommendations found: {len(result['recommendations'])}")

        # Show results
        agent.print_results()

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())