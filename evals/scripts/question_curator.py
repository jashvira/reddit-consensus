#!/usr/bin/env python3
"""
Question Curator - Generate evaluation questions from Reddit discussions
using a 2-pass approach: cheap keyword extraction + quality question generation.
"""

import os
import asyncio
import pandas as pd
import json
import argparse
import re
import random
from pathlib import Path
from typing import Dict, List, Any
from openai import AsyncOpenAI
from tqdm import tqdm


class QuestionCurator:
    """
    2-pass question generation:
    1. Extract forbidden keywords (cheap model)
    2. Generate masked questions (quality model)
    """

    def __init__(self, openai_api_key: str = None, max_concurrent: int = 5, max_retries: int = 3, base_delay: float = 1.0):
        """Initialize with AsyncOpenAI client."""
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key required")

        self.client = AsyncOpenAI(api_key=api_key)
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.max_retries = max_retries
        self.base_delay = base_delay

        # Model configuration
        self.cheap_model = "gpt-4.1-mini"      # For keyword extraction
        self.quality_model = "gpt-4.1-mini"         # For question generation & screening

        # Pricing per 1M tokens (from OpenAI pricing page)
        self.pricing = {
            "gpt-4.1-mini": {"input": 0.150, "output": 0.600},  # per 1M tokens
            "o4-mini-2025-04-16": {"input": 1.10, "output": 4.40}  # per 1M tokens
        }

    def format_content(self, post_data: Dict[str, Any]) -> str:
        """Format post and comments into readable text."""
        content_parts = []

        # Add post content
        content_parts.append(f"POST TITLE: {post_data['title']}")
        content_parts.append(f"POST BODY: {post_data['selftext']}")

        # Add top comments
        comments = post_data.get('comments', [])
        if comments is not None and len(comments) > 0:
            content_parts.append("\nTOP COMMENTS:")
            for i, comment in enumerate(comments[:10], 1):
                if isinstance(comment, dict):
                    body = comment.get('body', '')[:200]  # Limit comment length
                    content_parts.append(f"{i}. {body}")
                else:
                    content_parts.append(f"{i}. {str(comment)[:200]}")

        return "\n".join(content_parts)

    async def retry_on_rate_limit(self, api_call_func, *args, **kwargs):
        """Retry API calls with exponential backoff on rate limit errors."""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                result = await api_call_func(*args, **kwargs)

                # Log successful retry if this wasn't the first attempt
                if attempt > 0:
                    print(f"DEBUG: ✅ Successfully recovered after {attempt} retries")

                # Return result with retry metadata
                return result, attempt

            except Exception as e:
                last_exception = e
                error_str = str(e)

                # Check if this is a rate limit error
                if "rate limit" not in error_str.lower() and "429" not in error_str:
                    # Not a rate limit error, re-raise immediately
                    raise e

                if attempt == self.max_retries:
                    # Last attempt failed, re-raise
                    print(f"DEBUG: ❌ Failed after {self.max_retries + 1} attempts, giving up")
                    raise e

                # Parse wait time from error message
                wait_time = None
                # Look for patterns like "Please try again in 198ms" or "Please try again in 1.5s"
                ms_match = re.search(r'try again in (\d+)ms', error_str)
                s_match = re.search(r'try again in ([\d.]+)s', error_str)

                if ms_match:
                    wait_time = int(ms_match.group(1)) / 1000.0
                elif s_match:
                    wait_time = float(s_match.group(1))
                else:
                    # Use exponential backoff with jitter
                    wait_time = self.base_delay * (2 ** attempt) + random.uniform(0, 1)

                print(f"DEBUG: ⏳ Rate limit hit (attempt {attempt + 1}/{self.max_retries + 1}), waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)

        # Should never reach here, but just in case
        raise last_exception

    async def should_reject_post(self, content: str) -> Dict[str, Any]:
        """
        Pre-screening: Determine if post should be rejected for evaluation.
        Cost: ~$0.0001 per call

        Returns: {'reject': bool, 'reason': str}
        """
        prompt = f"""Analyze this Reddit discussion to determine if it would make a good evaluation question for testing an AI model's knowledge and reasoning.

REJECT the post if it has ANY of these problems:

**AMBIGUOUS/SUBJECTIVE CONTENT:**
- Purely opinion-based discussions with no way to craft a question that is answerable from the discussion
- Highly subjective matters with no concrete right/wrong answers
- Personal preference discussions

**INAPPROPRIATE CONTENT:**
- Personal relationship drama or therapy-seeking
- Medical advice requests (serious health issues)
- Legal advice for specific cases
- Content that's primarily emotional venting

**ACCEPT the post if:**
- Has clear, factual, or procedural knowledge being shared
- Contains concrete advice, explanations, or solutions
- Demonstrates expertise or experience-based insights
- Has clear social and cultural direction
- Would allow testing factual knowledge, reasoning, or problem-solving
- Has substantive discussion with multiple informative responses

Return ONLY:
DECISION: ACCEPT or REJECT
REASON: [one-sentence explanation]

Discussion Content:
{content[:1500]}  # Limit for cost control
"""

        try:
            async with self.semaphore:
                response, retry_count = await self.retry_on_rate_limit(
                    self.client.chat.completions.create,
                    model=self.quality_model,  # Use quality model for screening
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=150
                )

            response_text = response.choices[0].message.content.strip()

            # Get actual usage data
            usage = response.usage
            cost = (usage.prompt_tokens * self.pricing[self.quality_model]["input"] / 1_000_000 +
                   usage.completion_tokens * self.pricing[self.quality_model]["output"] / 1_000_000)

            # Parse response
            reject = True
            reason = "Unknown"

            if "DECISION:" in response_text and "REASON:" in response_text:
                lines = response_text.split("\n")
                for line in lines:
                    if line.startswith("DECISION:"):
                        decision = line.replace("DECISION:", "").strip().upper()
                        reject = decision == "REJECT"
                    elif line.startswith("REASON:"):
                        reason = line.replace("REASON:", "").strip()

            return {
                'reject': reject,
                'reason': reason,
                'cost': cost,
                'input_tokens': usage.prompt_tokens,
                'output_tokens': usage.completion_tokens,
                'retry_count': retry_count
            }

        except Exception as e:
            print(f"DEBUG: Screening failed for model {self.quality_model}: {str(e)}")
            return {'reject': True, 'reason': f'Screening failed: {str(e)}', 'cost': 0.0, 'input_tokens': 0, 'output_tokens': 0, 'retry_count': 0}

    async def extract_forbidden_keywords(self, content: str) -> List[str]:
        """
        Pass 1: Extract specific terms to avoid using cheap model.
        Cost: ~$0.0001 per call
        """
        prompt = f"""Extract the key specific terms, names, brands, technical jargon, and unique phrases from this Reddit discussion that should be avoided when creating an evaluation question.

Focus on:
- Technical terms and jargon
- Specific product/brand/events names
- Unique phrases or slang
- Domain-specific vocabulary
- Proper nouns

Return only a comma-separated list of terms.

Content:
{content}  # Limit content length for cost control
"""

        try:
            async with self.semaphore:
                response, retry_count = await self.retry_on_rate_limit(
                    self.client.chat.completions.create,
                    model=self.cheap_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=200,
                    temperature=0.1
                )

            keywords_text = response.choices[0].message.content.strip()

            # Get actual usage data
            usage = response.usage
            cost = (usage.prompt_tokens * self.pricing[self.cheap_model]["input"] / 1_000_000 +
                   usage.completion_tokens * self.pricing[self.cheap_model]["output"] / 1_000_000)

            # Parse comma-separated list
            keywords = [k.strip() for k in keywords_text.split(',') if k.strip()]
            return {
                'keywords': keywords,
                'cost': cost,
                'input_tokens': usage.prompt_tokens,
                'output_tokens': usage.completion_tokens,
                'retry_count': retry_count
            }

        except Exception:
            return {'keywords': [], 'cost': 0.0, 'input_tokens': 0, 'output_tokens': 0, 'retry_count': 0}

    async def generate_masked_question(self, content: str, forbidden_keywords: List[str], post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pass 2: Generate high-quality question avoiding forbidden terms.
        Also identify which comments contain key insights.
        Cost: ~$0.01 per call
        """
        forbidden_list = ", ".join(forbidden_keywords) if forbidden_keywords else "none"

        prompt = f"""Based on this Reddit discussion, create 1-2 sharp, specific evaluation questions that test the same knowledge discussed, but use completely different vocabulary.

IMPORTANT: These questions will be asked to an AI model with NO CONTEXT about this Reddit discussion. The model will receive only the question you generate as a standalone query. Avoid using "this"/etc to refer to the discussion.

FORBIDDEN TERMS (DO NOT USE): {forbidden_list}

Requirements:
- Questions should be answerable from the discussion content
- Use generic, abstract, or alternative terminology instead of specific terms
- Focus on the underlying concepts, principles, or problems discussed
- Make questions pointed and specific, not vague
- Avoid any words from the forbidden list
- Questions should sound natural, like someone genuinely asking for advice or information

Also identify which specific comments (by number) contain the key insights needed to answer your questions.

Return in this exact format:
QUESTIONS:
[your questions here]

KEY_COMMENTS:
[list comment numbers that contain essential insights, e.g., "1, 3, 5"]

Discussion Content:
{content}
"""

        try:
            async with self.semaphore:
                response, retry_count = await self.retry_on_rate_limit(
                    self.client.chat.completions.create,
                    model=self.quality_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=400
                )

            response_text = response.choices[0].message.content.strip()

            # Get actual usage data
            usage = response.usage
            cost = (usage.prompt_tokens * self.pricing[self.quality_model]["input"] / 1_000_000 +
                   usage.completion_tokens * self.pricing[self.quality_model]["output"] / 1_000_000)

            # Parse the response
            questions = ""
            key_comment_nums = []

            if "QUESTIONS:" in response_text and "KEY_COMMENTS:" in response_text:
                parts = response_text.split("KEY_COMMENTS:")
                questions = parts[0].replace("QUESTIONS:", "").strip()
                key_comments_text = parts[1].strip()

                # Parse comment numbers
                try:
                    key_comment_nums = [int(x.strip()) for x in key_comments_text.split(",") if x.strip().isdigit()]
                except:
                    pass
            else:
                questions = response_text

            # Map comment numbers to actual comment IDs
            key_comment_ids = []
            comments = post_data.get('comments', [])
            if comments is not None and len(comments) > 0 and key_comment_nums:
                for num in key_comment_nums:
                    if 1 <= num <= len(comments):
                        comment = comments[num - 1]
                        if isinstance(comment, dict) and 'id' in comment:
                            key_comment_ids.append(comment['id'])
                        else:
                            key_comment_ids.append(f"comment_{num}")

            return {
                'questions': questions,
                'key_comment_numbers': key_comment_nums,
                'key_comment_ids': key_comment_ids,
                'cost': cost,
                'input_tokens': usage.prompt_tokens,
                'output_tokens': usage.completion_tokens,
                'retry_count': retry_count
            }

        except Exception:
            return {'questions': '', 'key_comment_numbers': [], 'key_comment_ids': [], 'cost': 0.0, 'input_tokens': 0, 'output_tokens': 0, 'retry_count': 0}

    async def generate_direct_question(self, content: str, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate questions directly from content without forbidden word restrictions.
        Cost: ~$0.01 per call
        """
        prompt = f"""Based on this Reddit discussion, create 1-2 sharp, specific evaluation questions that test the knowledge discussed.

IMPORTANT: These questions will be asked to an AI model with NO CONTEXT about this Reddit discussion. The model will receive only the question you generate as a standalone query. Avoid using "this"/etc to refer to the discussion.

You may use specific terms, names, brands, and technical vocabulary from the discussion to create natural, direct questions.

Requirements:
- Questions should be answerable from the discussion content
- Use actual terminology and specific references from the discussion
- Focus on the concrete knowledge, procedures, or problems discussed
- Make questions pointed and specific, not vague
- Questions should sound natural, like someone genuinely asking for advice or information

Also identify which specific comments (by number) contain the key insights needed to answer your questions.

Return in this exact format:
QUESTIONS:
[your questions here]

KEY_COMMENTS:
[list comment numbers that contain essential insights, e.g., "1, 3, 5"]

Discussion Content:
{content}
"""

        try:
            async with self.semaphore:
                response, retry_count = await self.retry_on_rate_limit(
                    self.client.chat.completions.create,
                    model=self.quality_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=400
                )

            response_text = response.choices[0].message.content.strip()

            # Get actual usage data
            usage = response.usage
            cost = (usage.prompt_tokens * self.pricing[self.quality_model]["input"] / 1_000_000 +
                   usage.completion_tokens * self.pricing[self.quality_model]["output"] / 1_000_000)

            # Parse the response
            questions = ""
            key_comment_nums = []

            if "QUESTIONS:" in response_text and "KEY_COMMENTS:" in response_text:
                parts = response_text.split("KEY_COMMENTS:")
                questions = parts[0].replace("QUESTIONS:", "").strip()
                key_comments_text = parts[1].strip()

                # Parse comment numbers
                try:
                    key_comment_nums = [int(x.strip()) for x in key_comments_text.split(",") if x.strip().isdigit()]
                except:
                    pass
            else:
                questions = response_text

            # Map comment numbers to actual comment IDs
            key_comment_ids = []
            comments = post_data.get('comments', [])
            if comments is not None and len(comments) > 0 and key_comment_nums:
                for num in key_comment_nums:
                    if 1 <= num <= len(comments):
                        comment = comments[num - 1]
                        if isinstance(comment, dict) and 'id' in comment:
                            key_comment_ids.append(comment['id'])
                        else:
                            key_comment_ids.append(f"comment_{num}")

            return {
                'questions': questions,
                'key_comment_numbers': key_comment_nums,
                'key_comment_ids': key_comment_ids,
                'cost': cost,
                'input_tokens': usage.prompt_tokens,
                'output_tokens': usage.completion_tokens,
                'retry_count': retry_count
            }

        except Exception:
            return {'questions': '', 'key_comment_numbers': [], 'key_comment_ids': [], 'cost': 0.0, 'input_tokens': 0, 'output_tokens': 0, 'retry_count': 0}

    async def curate_question(self, post_data: Dict[str, Any], no_masking: bool = False) -> Dict[str, Any]:
        """
        Main orchestrator: 2-pass (no_masking) or 3-pass (masking) question curation with screening.

        Args:
            post_data: Reddit post data
            no_masking: If True, skip keyword extraction and allow direct questions

        Returns:
            {
                'source_post_id': str,
                'subreddit': str,
                'original_title': str,
                'original_body': str,
                'accepted': bool,
                'rejection_reason': str (if rejected),
                'questions': List[str] (if accepted),
                'forbidden_keywords': List[str] or None (if accepted),
                'key_comment_ids': List[str] (if accepted),
                'masking_mode': bool,
                'metrics': {'total_cost': float, 'total_tokens': int, 'total_retries': int, 'passes_used': int}
            }
        """
        # Format the content
        content = self.format_content(post_data)

        base_result = {
            'source_post_id': post_data.get('id', 'unknown'),
            'subreddit': post_data.get('subreddit', 'unknown'),
            'original_title': post_data.get('title', ''),
            'original_body': post_data.get('selftext', ''),
        }

        # Pass 0: Pre-screening
        screening_result = await self.should_reject_post(content)
        
        if screening_result['reject']:
            # Post rejected - return early
            return {
                **base_result,
                'accepted': False,
                'rejection_reason': screening_result['reason'],
                'questions': None,
                'forbidden_keywords': None,
                'key_comment_ids': None,
                'masking_mode': not no_masking,
                'metrics': {
                    'total_cost': screening_result['cost'],
                    'total_tokens': screening_result['input_tokens'] + screening_result['output_tokens'],
                    'total_retries': screening_result.get('retry_count', 0),
                    'passes_used': 1
                }
            }

        if no_masking:
            # Skip keyword extraction for no-masking mode
            keyword_result = {'keywords': [], 'cost': 0.0, 'input_tokens': 0, 'output_tokens': 0, 'retry_count': 0}
            forbidden_keywords = []
            
            # Pass 1 (2-pass mode): Generate direct question
            question_result = await self.generate_direct_question(content, post_data)
        else:
            # Pass 1: Extract forbidden keywords
            keyword_result = await self.extract_forbidden_keywords(content)
            forbidden_keywords = keyword_result['keywords']

            # Pass 2: Generate masked question
            question_result = await self.generate_masked_question(content, forbidden_keywords, post_data)

        # Calculate totals
        total_cost = screening_result['cost'] + keyword_result['cost'] + question_result['cost']
        total_tokens = (screening_result['input_tokens'] + screening_result['output_tokens'] + 
                       keyword_result['input_tokens'] + keyword_result['output_tokens'] +
                       question_result['input_tokens'] + question_result['output_tokens'])
        total_retries = (screening_result.get('retry_count', 0) + 
                        keyword_result.get('retry_count', 0) + 
                        question_result.get('retry_count', 0))

        # Parse questions into array format
        questions_text = question_result['questions']
        questions_array = []
        if questions_text:
            import re
            # Split by numbered pattern: "1. ", "2. ", etc.
            parts = re.split(r'\d+\.\s+', questions_text)[1:]  # Skip empty first part
            questions_array = [q.strip().rstrip('?') + '?' for q in parts if q.strip()]

        return {
            **base_result,
            'accepted': True,
            'rejection_reason': None,
            'questions': questions_array,
            'forbidden_keywords': forbidden_keywords if not no_masking else None,
            'key_comment_ids': question_result['key_comment_ids'],
            'masking_mode': not no_masking,
            'metrics': {
                'total_cost': total_cost,
                'total_tokens': total_tokens,
                'total_retries': total_retries,
                'passes_used': 2 if no_masking else 3
            }
        }


async def process_multiple_posts(posts: List[Dict[str, Any]], max_concurrent: int = 5, max_retries: int = 3, no_masking: bool = False) -> List[Dict[str, Any]]:
    """Process multiple posts concurrently with progress tracking."""
    curator = QuestionCurator(max_concurrent=max_concurrent, max_retries=max_retries)

    # Process all posts concurrently with progress bar
    tasks = [curator.curate_question(post, no_masking=no_masking) for post in posts]
    results = []
    for future in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Processing posts"):
        try:
            result = await future
            results.append(result)
        except Exception as e:
            results.append(e)  # Same as return_exceptions=True

    # Handle any exceptions
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append({
                'source_post_id': posts[i].get('id', 'unknown'),
                'subreddit': posts[i].get('subreddit', 'unknown'),
                'original_title': posts[i].get('title', ''),
                'original_body': posts[i].get('selftext', ''),
                'accepted': False,
                'rejection_reason': f'Processing error: {str(result)}',
                'questions': None,
                'forbidden_keywords': None,
                'key_comment_ids': None,
                'masking_mode': not no_masking,
                'metrics': {
                    'total_cost': 0.0,
                    'total_tokens': 0,
                    'total_retries': 0,
                    'passes_used': 0
                }
            })
        else:
            processed_results.append(result)

    return processed_results


async def screen_posts_only(posts: List[Dict[str, Any]], max_concurrent: int = 5, max_retries: int = 3) -> List[Dict[str, Any]]:
    """Screen posts for accept/reject only, without expensive question generation."""
    curator = QuestionCurator(max_concurrent=max_concurrent, max_retries=max_retries)

    # Process all posts concurrently with progress bar
    tasks = []
    for post in posts:
        content = curator.format_content(post)
        tasks.append(curator.should_reject_post(content))

    results = []
    for future in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Screening posts"):
        result = await future
        results.append(result)

    # Format results
    processed_results = []
    for i, result in enumerate(results):
        post = posts[i]
        processed_results.append({
            'post_id': post.get('id', 'unknown'),
            'subreddit': post.get('subreddit', 'unknown'),
            'title': post.get('title', '')[:100],
            'rejected': result['reject'],
            'reason': result['reason'],
            'cost': result['cost']
        })

    return processed_results


async def process_parquet_dataset(input_path: str, output_path: str, max_concurrent: int = 5, start_idx: int = 0, max_posts: int = None, screen_only: bool = False, max_retries: int = 3, no_masking: bool = False):
    """Process Reddit posts from parquet file and save curated questions."""

    # Load data
    print(f"Loading data from {input_path}...")
    df = pd.read_parquet(input_path)
    print(f"Loaded {len(df)} posts")

    # Slice based on parameters
    if max_posts:
        end_idx = min(start_idx + max_posts, len(df))
    else:
        end_idx = len(df)

    df_subset = df.iloc[start_idx:end_idx]
    posts = df_subset.to_dict('records')

    print(f"Processing posts {start_idx} to {end_idx-1} ({len(posts)} posts)")

    if screen_only:
        # Only run screening
        print(f"Starting screening with {max_concurrent} concurrent requests...")
        results = await screen_posts_only(posts, max_concurrent=max_concurrent, max_retries=max_retries)

        # Calculate stats
        accepted = sum(1 for r in results if not r['rejected'])
        rejected = len(results) - accepted
        total_cost = sum(r['cost'] for r in results)

        # Calculate retry statistics for screening
        total_retries = sum(r.get('retry_count', 0) for r in results)
        posts_with_retries = sum(1 for r in results if r.get('retry_count', 0) > 0)

        print(f"\nScreening complete:")
        print(f"  Accepted: {accepted}")
        print(f"  Rejected: {rejected}")
        print(f"  Total cost: ${total_cost:.4f}")
        print(f"  Total retries: {total_retries}")
        print(f"  Posts requiring retries: {posts_with_retries}")
        print(f"  Avg cost per post: ${total_cost/len(results):.4f}")

    else:
        # Full processing
        print(f"Starting processing with {max_concurrent} concurrent requests...")
        results = await process_multiple_posts(posts, max_concurrent=max_concurrent, max_retries=max_retries, no_masking=no_masking)

        # Calculate stats
        accepted = sum(1 for r in results if r['accepted'])
        rejected = len(results) - accepted
        total_cost = sum(r['metrics']['total_cost'] for r in results)
        total_tokens = sum(r['metrics']['total_tokens'] for r in results)

        # Calculate retry statistics
        total_retries = sum(r['metrics']['total_retries'] for r in results)
        posts_with_retries = sum(1 for r in results if r['metrics']['total_retries'] > 0)

        print(f"\nProcessing complete:")
        print(f"  Accepted: {accepted}")
        print(f"  Rejected: {rejected}")
        print(f"  Total cost: ${total_cost:.4f}")
        print(f"  Total tokens: {total_tokens:,}")
        print(f"  Total retries: {total_retries}")
        print(f"  Posts requiring retries: {posts_with_retries}")
        print(f"  Avg cost per post: ${total_cost/len(results):.4f}")
        print(f"  Avg tokens per post: {total_tokens/len(results):.0f}")

    # Save results
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"Results saved to {output_path}")
    return results


async def main():
    """Process parquet dataset with command line arguments."""
    parser = argparse.ArgumentParser(description='Process Reddit posts for question curation')
    parser.add_argument('--input', default='evals/processed/reddit_2016_filtered_2.parquet', help='Input parquet file')
    parser.add_argument('--output', default='evals/processed/curated_questions_2.json', help='Output JSON file')
    parser.add_argument('--max-concurrent', type=int, default=5, help='Max concurrent requests')
    parser.add_argument('--start-idx', type=int, default=0, help='Start index')
    parser.add_argument('--max-posts', type=int, help='Max posts to process')
    parser.add_argument('--screen-only', action='store_true', help='Only run screening (accept/reject) without question generation')
    parser.add_argument('--max-retries', type=int, default=3, help='Max retries for rate limited requests')
    parser.add_argument('--no-masking', action='store_true', help='Skip keyword extraction, allow direct questions using original terms')

    args = parser.parse_args()

    await process_parquet_dataset(
        input_path=args.input,
        output_path=args.output,
        max_concurrent=args.max_concurrent,
        start_idx=args.start_idx,
        max_posts=args.max_posts,
        screen_only=args.screen_only,
        max_retries=args.max_retries,
        no_masking=args.no_masking
    )


if __name__ == "__main__":
    asyncio.run(main())