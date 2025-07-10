# Development Knowledge Base

## Async/Sync Architecture

**Current Pattern:**
- **Tools (Reddit API)**: async (AsyncPRAW, parallel execution)
- **LLM calls**: async (rate limiting integration with openlimit)
- **UI/Console**: sync (Rich rendering)

**Why LLM became async:** openlimit integration for 30K TPM limits. Could be sync but keeping async avoids refactor churn.

**Rule:** async where I/O bound (Reddit, OpenAI), sync for CPU work (rendering, data processing).

## Comment Filtering Strategy

**Adaptive Comment Filtering:** Uses percentile-based thresholds instead of fixed scores (80th percentile default).

**Two-Pass System:**
- First pass: Collect all comment scores across entire post
- Second pass: Filter using calculated threshold with ancestor preservation
- `_calculate_score_threshold()` dynamically sets quality bar based on post's score distribution

**Ancestor Preservation:**
- High-scoring nested comments preserve their entire parent chain
- `_has_high_scoring_descendant()` catches valuable deep comments
- Maintains Reddit's tree structure while focusing on quality content
- Prevents losing context when child comment is more valuable than parent

**Token Efficiency:**
- Dramatically reduces token usage by focusing on quality over quantity
- Adapts to each post's unique score distribution
- Eliminates noise from heavily downvoted or spam comments

## Reddit API Patterns

**AsyncPRAW Choice:** Enables parallel post+comment fetching. Massive performance gain vs sync.

**Tool Execution:**
- Single tool: immediate execution with logging
- Multiple tools: parallel execution with consolidated results
- Error isolation: one tool failure doesn't break others

**Comment Trees:** Recursive structure preserved, configurable depth limits for performance.

## LLM Integration

**JSON Retry Pattern:** OpenAI occasionally returns malformed JSON. 2-attempt retry with fallback prevents crashes.

**Model Selection:** gpt-4.1 for quality, not gpt-4o (user constraint). Rate limiting critical for this model.

**Prompt Architecture:**
- Separate files in `prompts.py` for maintainability
- Context injection points for research data
- Fallback responses for all prompts

## State Management

**Research Data as JSON:** Enables easy serialization, pattern matching for tool results, and flexible data inspection.

**Key Patterns:**
- `search_*`: Reddit search results
- `comments_*`: Post comment data
- Tool results stored immediately for error recovery

## Configuration Philosophy

**Centralized config.py:** All defaults in one place. Environment variables for secrets only.

**Validation:** `validate_config()` checks credentials before startup. Clear error messages.

**Hierarchy:** Code defaults → config.py → env vars → user params

## UI/Console Patterns

**Rich Integration:** All output through Rich for consistent formatting. No raw prints except errors.

**Color Semantics:**
- TOOL: blue (tool execution)
- SEARCH: yellow (search queries)
- POST: cyan (post processing)
- WARNING: yellow (attention needed)
- ERROR: red (failures)

**Dashboard Pattern:** Side-by-side tool execution table + detailed results. Scales with terminal width.

## Tool Result Normalization

**Unified Format:** All tools return `{"tool_name": str, "result": str, "index": int}` for consistent processing.

**Storage Keys:** `{mode}_{tool_name}_{iteration}_{index}` pattern enables easy lookup and debugging.

## Error Handling Strategies

**Graceful Degradation:**
- JSON parse errors → fallback responses
- Tool failures → continue with partial data
- Rate limits → auto-summarization
- Network errors → retry with exponential backoff

**No Silent Failures:** All errors logged with context. User always knows what went wrong.

## Performance Optimizations

**Parallel Tool Execution:** asyncio.gather() for multiple Reddit API calls. 3-5x faster than sequential.

**Token-Aware Prompts:** Summarization prevents expensive retries from oversized requests.

**Comment Depth Limits:** Prevents infinite recursion in deep comment threads.

## Debugging Patterns

**Async Stack Traces:** Use `console.print_exception()` from Rich for readable async errors.

**Research Data Inspection:** JSON storage enables easy debugging of tool results.

**Token Estimation:** `estimate_prompt_tokens()` for pre-flight size checks.

## Testing Philosophy

**Integration > Unit:** Reddit API and OpenAI integration more valuable than isolated unit tests.

**Config Validation:** `validate_config()` catches 90% of setup issues.

**Manual Testing:** `test_parallel.py` for end-to-end validation with real APIs.

## Development Patterns

**Comment Filtering Evolution:**
- Started with chronological comment processing (leads to token bloat)
- Evolved to score-based filtering with hierarchical preservation
- Human-like approach: focus on upvoted, community-validated content
- Lesson: Quality over quantity - sample efficiently rather than process everything

**LLM Integration Evolution:**
- Removed complex rate limiting and summarization layers
- Simplified to direct OpenAI client calls with basic JSON retry
- Focus on efficient data sampling rather than post-processing compression
- Pattern: prevent problems at source rather than fix them downstream

**Prompt Design Philosophy:**
- Concise summaries (200-300 word limits)
- Focus on actionable insights vs raw data
- Include consensus patterns and community sentiment
- Preserve specific names, brands, recommendations

**Comment Filtering Architecture:**
- `DEFAULT_ADAPTIVE_PERCENTILE`: Percentile threshold for filtering (default: 80)
- `DEFAULT_SORT_BY_SCORE`: Enable/disable score-based sorting (default: True)
- `_calculate_score_threshold()`: Dynamic threshold based on score distribution
- `_has_high_scoring_descendant()`: Ancestor preservation logic
- `_build_comment_tree()`: Recursive filtering with hierarchical structure
- Pattern: Adaptive quality thresholds + ancestor preservation = efficient token usage

**Scaling Comment Processing:**
- Adjust `adaptive_percentile` for different quality levels (25, 50, 80)
- Higher percentiles for noisy posts, lower for niche communities  
- Adaptive filtering responds to each post's unique score patterns
- Filtering applied at all tree levels, not just top-level comments

## File Structure

**Core Architecture Files:**
- `recommender.py`: Main agent implementation with research phases
- `config.py`: Centralized configuration including comment filtering options
- `prompts.py`: LLM prompt templates for different phases
- `tools.py`: Async Reddit API integration with smart comment filtering
- `agent_state.py`: State management for research progress
- `colors.py`: Rich console UI formatting and display

**Key Implementation Details:**
- `tools.py`: Contains adaptive filtering logic in `_calculate_score_threshold()` and `_has_high_scoring_descendant()`
- `reddit_get_post_comments()`: Supports `adaptive_filtering` and `sort_by_score` parameters
- Two-pass filtering: collect all scores → calculate threshold → filter with ancestor preservation
- `rate_limiter.py`: **REMOVED** - complexity eliminated in favor of simple filtering
- Simplified LLM calls with basic JSON retry logic (no complex rate limiting)

**Remember:** Update DEVELOPMENT.md when significant architecture changes are made.

## Evaluation Dataset Generation Pipeline

### Data Acquisition Strategy

**Historical Reddit Data (2016):**
- Source: Hugging Face `fddemarco/pushshift-reddit` and `fddemarco/pushshift-reddit-comments`
- Selection: February 2016 (latest available with both posts and comments)
- Scale: ~22GB raw data → ~50MB filtered dataset

**Subreddit Discovery:**
- **API Search**: Used `reddit.subreddits.search('ask')` instead of `search_by_name()` 
- **Pattern Expansion**: Multiple search terms (`ask`, `askscience`, `askengineers`, etc.)
- **Result**: Found 57 Ask subreddits vs 10 with basic search
- **Key Insight**: Broader search methods reveal more comprehensive results

### Data Filtering Pipeline

**Multi-Stage Filtering Approach:**
1. **Subreddit Filter**: Target high-quality communities (`AskHistorians`, `AskEngineers`, etc.)
2. **Engagement Thresholds**: Score ≥300, comments ≥20 
3. **Content Quality**: Non-empty titles and body text
4. **Deduplication**: Remove posts with identical lowercased titles per subreddit
5. **Token Limits**: Combined content ≤4096 tokens (estimated at chars/3)
6. **Quota Control**: Max 600 posts per subreddit

**Reddit ID Normalization:**
- **Problem**: Comment `link_id` has `t3_` prefix, post `id` doesn't
- **Solution**: Strip `t3_` prefix before joining data
- **Pattern**: `top_comments['link_id'] = top_comments['link_id'].str.replace('t3_', '')`

**Comment Integration Strategy:**
- Top 40 comments per post by score
- Comments stored as nested JSON within post records
- Preserves comment metadata (score, timestamp, author flair)

### Question Curation System

**3-Pass Cost-Optimized Pipeline:**

**Pass 0: Content Screening** (gpt-4o-mini, ~$0.0001)
- **Rejects**: Subjective discussions, poor quality threads, unanswerable questions
- **Criteria**: <3 meaningful comments, opinion-based content, insufficient context
- **ROI**: 50-70% cost savings by filtering unsuitable posts early

**Pass 1: Keyword Extraction** (gpt-4o-mini, ~$0.0001) 
- Extract domain-specific terms, technical jargon, brand names
- Build forbidden vocabulary list for masked question generation
- Focus on specific terminology that reveals source discussion

**Pass 2: Question Generation** (gpt-4o, ~$0.01)
- Generate evaluation questions using abstract/generic terminology
- Identify key comment IDs containing essential insights
- Map comment numbers to actual Reddit comment IDs for answer validation

**Smart Cost Allocation:**
- Cheap model for extraction tasks (90% of calls)
- Quality model only for final question crafting
- Total cost: ~$0.01 per accepted question, $0.0001 per rejected

### Rate Limit Handling & Retry Logic

**Intelligent Retry System:**
- **Wait Time Parsing**: Extracts exact wait times from OpenAI error messages (e.g., "Please try again in 198ms")
- **Exponential Backoff**: Fallback strategy when no specific wait time is provided
- **Jitter Addition**: Random component prevents thundering herd effects
- **Selective Retries**: Only retries on rate limit errors (429 status), other errors re-raised immediately

**Implementation Details:**
- `retry_on_rate_limit()` async function wraps all OpenAI API calls
- Configurable `max_retries` (default: 3) and `base_delay` (default: 1.0s)
- Regex parsing for "try again in Xms" and "try again in Xs" patterns
- Applied to all 3 passes: screening, keyword extraction, question generation

**Command Line Options:**
- `--max-retries`: Control retry behavior (default: 3)
- Debug logging shows retry attempts and wait times
- Preserves original error handling for non-rate-limit failures

**Performance Impact:**
- Eliminates manual restarts due to rate limiting
- Respects API-suggested wait times for optimal throughput
- Maintains progress across large dataset processing batches

### Data Processing Optimizations

**Memory Management:**
- **Challenge**: Pandas parquet reading doesn't support chunking
- **Solution**: Load full dataset, apply filters sequentially 
- **Alternative**: Polars for larger datasets if memory constraints persist

**Processing Order:**
1. Filter posts first (massive data reduction)
2. Extract kept post IDs for comment filtering  
3. Process comments only for surviving posts
4. Join and apply final constraints

**Performance Patterns:**
- Early filtering reduces downstream processing by 95%+
- Post-comment joining on filtered datasets vs full join
- Sequential filtering more memory-efficient than complex queries

### Question Generation Techniques

**Abstraction Strategies:**
- **Domain Shifting**: "sourdough starter" → "fermented culture"
- **Conceptual Elevation**: Specific problems → underlying principles  
- **Vocabulary Masking**: Technical terms → generic equivalents
- **Perspective Rotation**: Direct advice → hypothetical scenarios

**Quality Assurance:**
- Forbidden keyword enforcement with semantic similarity checking
- Answerability validation against source content
- Comment targeting for evaluation reference
- Structured output parsing with fallback handling

**Output Format:**
```python
{
    'rejected': False,
    'questions': 'What causes fermented cultures to develop chemical odors?',
    'forbidden_keywords': ['sourdough', 'starter', 'acetone'],
    'key_comment_ids': ['comment1', 'comment2'],
    'key_comment_numbers': [1, 2],
    'source_post_id': 'abc123',
    'cost_estimate': 0.0102
}
```

### Key Learnings

**Data Quality > Quantity:**
- 90 filtered posts from millions of raw posts
- Focus on substantive discussions with expert insights
- Quality thresholds eliminate noise more effectively than post-processing

**Cost Optimization Patterns:**
- Model selection based on task complexity
- Early rejection saves expensive processing
- Structured prompts reduce token usage

**Reddit Data Characteristics:**
- Many posts lack selftext (link/image posts)
- Comment threading requires careful ID management
- Historical data has different quality patterns than current Reddit

**Pipeline Robustness:**
- Graceful handling of missing data (NaN, empty fields)
- Type checking for nested structures (lists vs floats)
- Fallback parsing for LLM response variations

### File Structure

**Evaluation Pipeline:**
- `evals/scripts/process_reddit_data.py`: Main data filtering pipeline
- `evals/scripts/question_curator.py`: 3-pass question generation system
- `evals/scripts/list_ask_subreddits.py`: Subreddit discovery tool
- `evals/datasets/`: Raw data storage and subreddit lists
- `evals/processed/`: Filtered datasets ready for evaluation
- `evals/notebooks/`: Interactive data exploration and processing

**Remember:** Evaluation dataset generation focuses on quality over scale, with cost-efficient LLM usage and robust data processing patterns.