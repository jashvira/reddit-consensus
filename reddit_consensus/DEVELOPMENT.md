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