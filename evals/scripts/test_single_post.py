#!/usr/bin/env python3
"""
Test question curator on a single real Reddit post.
"""

import pandas as pd
import json
import sys
from pathlib import Path
from question_curator import QuestionCurator

def main():
    """Process one real Reddit post and save results."""

    # Load the processed Reddit data
    input_file = "evals/processed/reddit_2016_filtered.parquet"

    try:
        df = pd.read_parquet(input_file)
        print(f"Loaded {len(df)} posts from dataset")
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    # Take the first post
    post_row = df.iloc[309]
    post_data = post_row.to_dict()

    print(f"=== TESTING POST ===")
    print(f"ID: {post_data['id']}")
    print(f"Subreddit: {post_data['subreddit']}")
    print(f"Title: {post_data['title'][:100]}...")
    print(f"Comments: {len(post_data['comments'])}")
    print()

    # Initialize curator and process
    curator = QuestionCurator()
    result = curator.curate_question(post_data)

    # Save result
    output_file = "evals/processed/single_post_result.json"
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)

    # Display result
    print("=== EVALUATION RESULT ===")
    if result['rejected']:
        print("❌ POST REJECTED")
        print("Reason:", result['rejection_reason'])
    else:
        print("✅ POST ACCEPTED")
        print("\n=== GENERATED QUESTIONS ===")
        questions = result['questions'].strip()
        if questions:
            # Split by question marks and clean up
            q_list = [q.strip() + '?' for q in questions.split('?') if q.strip()]
            for i, q in enumerate(q_list, 1):
                print(f"{i}. {q}")
        else:
            print("No questions generated")

        print(f"\nForbidden Keywords: {result['forbidden_keywords']}")
        print(f"Key Comment Numbers: {result['key_comment_numbers']}")
        print(f"Key Comment IDs: {result['key_comment_ids']}")

    print(f"\nEstimated Cost: ${result['cost_estimate']:.4f}")
    print(f"Total Duration: {result['total_duration_ms']}ms")
    print(f"Passes Completed: {result['passes_completed']}")

    print("\n=== PROCESSING LOG ===")
    for log in result['processing_log']:
        status = "✅" if log['success'] else "❌"
        print(f"{status} Pass {log['pass']} ({log['name']}): {log['duration_ms']}ms, ${log['cost_estimate']:.4f}, {log['model']}")
        if log['name'] == 'content_screening':
            print(f"   Decision: {log['output']['decision']}")
            print(f"   Reason: {log['output']['reason']}")
        elif log['name'] == 'keyword_extraction':
            print(f"   Keywords Found: {log['output']['keywords_found']}")
            print(f"   Sample Keywords: {log['output']['keywords'][:5]}")
        elif log['name'] == 'question_generation':
            print(f"   Questions Generated: {log['output']['questions_generated']}")
            print(f"   Key Comments: {log['output']['key_comment_numbers']}")

    print(f"\nResult saved to: {output_file}")

if __name__ == "__main__":
    main()