#!/usr/bin/env python3

"""
Test script for async parallel tool execution
Run this outside Jupyter to avoid event loop conflicts
"""

import sys
import os
sys.path.append('/home/jash404/agents/reddit_consensus')

from reddit_consensus.recommender import AutonomousRedditConsensus

def main():
    print("🚀 Testing Async Parallel Tool Execution")
    print("=" * 60)

    # Create recommender
    agent = AutonomousRedditConsensus()

    # Test query
    query = "Best cafes in the adelaide hills"
    print(f"Query: {query}")
    print("-" * 60)

    try:
        # Run the query
        result = agent.process_query(query)

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
    main()