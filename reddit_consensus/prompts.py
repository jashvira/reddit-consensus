"""
Prompt templates for the Reddit Consensus system.
Centralizes all LLM prompts for better maintainability.
"""

from .config import (
    DEFAULT_MAX_DEPTH,
    DEFAULT_RECOMMENDATION_COUNT,
)


def get_reasoning_prompt(
    tools_description: str,
    original_query: str,
    research_data_keys: list,
    reasoning_steps_count: int,
    context: str,
) -> str:
    """Generate the main reasoning turn prompt."""
    return f"""You are a Reddit consensus agent that finds great suggestions by analyzing Reddit discussions. Your goal is to discover what Reddit users are actually recommending and loving.

Available tools:
{tools_description}

Current state:
- Query: {original_query}
- Previous searches: {research_data_keys}
- Steps taken: {reasoning_steps_count}

Context: {context}

Instructions:
- Search Reddit for posts where people discuss, recommend, or ask about similar items/experiences
- Look for posts with good engagement (upvotes, comments) as they indicate quality discussions
- CRITICAL: Get comments from promising posts to analyze how users perceive the OP's insights
- Analyze comment sentiment: Are users agreeing, disagreeing, or adding better alternatives?
- Look for patterns: Multiple users mentioning the same places/products indicates strong consensus
- Pay attention to upvoted comments - these represent community-validated opinions
- Evaluate if commenters are locals/experts or just casual visitors (local knowledge is more valuable)
- Only proceed with insights that have genuine positive community feedback
- Focus on finding specific product names, brands, or experiences that users love
- Explore diverse sources: don't stop after finding a few popular posts, cast a wide net across different threads and time periods
- At least collect 5 strong sources of information before finalizing
- Once you have comprehensive Reddit consensus from multiple diverse sources, finalize

AVOID REPETITION: Don't search for the same or nearly identical terms repeatedly. If a search returns irrelevant results, try different keywords or angles. Repeating failed searches wastes tokens and provides no new information.

Respond in JSON format.

For single tool use:
{{
    "action": "use_tool",
    "tool_name": "reddit_search_for_posts",
    "tool_params": {{"query": "specific search query"}},
    "reasoning": "why you're using this tool"
}}

For multiple tools (RECOMMENDED - much faster):
{{
    "action": "use_tools",
    "tools": [
        {{
            "tool_name": "reddit_search_for_posts",
            "tool_params": {{"query": "search query 1"}}
        }},
        {{
            "tool_name": "reddit_get_post_comments",
            "tool_params": {{"post_id": "post_id_here"}}
        }},
        {{
            "tool_name": "reddit_get_post_comments",
            "tool_params": {{"post_id": "post_id_here", "max_depth": {DEFAULT_MAX_DEPTH}}}
        }}
    ],
    "reasoning": "why you're using these tools together"
}}

For finishing:
{{
    "action": "finalize",
    "reasoning": "why you have enough information to make insights"
}}"""


def get_draft_recommendations_prompt(
    original_query: str,
    research_data: dict,
    reasoning_steps: list,
    recommendation_count: int = DEFAULT_RECOMMENDATION_COUNT,
) -> str:
    """Generate the draft insights prompt."""
    return f"""Based on your Reddit research so far, create {recommendation_count} draft insights for the user.

Original Query: {original_query}

Reddit Research: {research_data}

Research Process: {reasoning_steps}

Create {recommendation_count} draft insights based on what you've found. These will be critiqued next.

Focus on nuanced insights that capture different use cases or contexts, not just the most mentioned options.

Return JSON object with:
{{
    "recommendations": [
        {{
            "name": "Specific insight name",
            "description": "Brief description",
            "reasoning": "Why this seems good from Reddit research"
        }}
    ]
}}"""


def get_critique_prompt(original_query: str, context: str) -> str:
    """Generate the critique turn prompt."""
    return f"""You have generated draft insights. Now critically analyze them by searching for potential issues or negative feedback.

Original Query: {original_query}

{context}

Your task is to search for criticism, negative experiences, or issues with your draft insights. Look for:
- Negative reviews or complaints
- Issues mentioned by Reddit users
- Alternative viewpoints
- Potential problems or downsides
- Context-specific limitations (e.g., good for X but not Y)

Search for discussions that contradict or provide nuance. Note: If the query has limited criticism potential (e.g., factual questions, non-controversial topics), do a basic search but don't force extensive critique - some topics simply don't have significant negative angles.

CRITICAL: Avoid repeating identical or nearly identical searches. Check the context above for your previous search attempts - if you see the same search terms already tried, DO NOT repeat them. If previous searches returned irrelevant results, this is a clear signal that criticism doesn't exist on Reddit for this topic. Stop searching and finalize instead of wasting tokens on repetitive failed searches.

Before searching, look at what you already tried. If you've already searched similar terms, either try completely different keywords or finalize if no relevant criticism exists.

Respond in JSON format.

For single tool use:
{{
    "action": "use_tool",
    "tool_name": "reddit_search_for_posts",
    "tool_params": {{"query": "specific search query"}},
    "reasoning": "why you're searching for criticism"
}}

For multiple tools (RECOMMENDED - critique all insights simultaneously):
{{
    "action": "use_tools",
    "tools": [
        {{
            "tool_name": "reddit_search_for_posts",
            "tool_params": {{"query": "criticism search 1"}}
        }},
        {{
            "tool_name": "reddit_search_for_posts",
            "tool_params": {{"query": "criticism search 2"}}
        }},
        {{
            "tool_name": "reddit_get_post_comments",
            "tool_params": {{"post_id": "post_id_here"}}
        }}
    ],
    "reasoning": "why you're using these tools together for critique"
}}

For finishing critique:
{{
    "action": "finalize",
    "reasoning": "why you're done with critique"
}}"""


def get_final_recommendations_prompt(
    original_query: str,
    research_data: dict,
    draft_recommendations: list,
    recommendation_count: int = DEFAULT_RECOMMENDATION_COUNT,
) -> str:
    """Generate the final insights prompt."""
    return f"""Based on your Reddit research AND critique findings, create {recommendation_count} balanced insights for the user.

Original Query: {original_query}

Initial Reddit Research: {research_data}

Draft Insights: {draft_recommendations}

Critique Research: [Include any critique findings from additional research]

Requirements:
- Create {recommendation_count} final insights based on ALL research (initial + critique)
- Include both positive aspects AND any discovered issues/criticisms
- Show balanced perspective from Reddit community
- Base everything on real Reddit comments and posts you found
- Be honest about any limitations or negative feedback discovered
- Explain when each insight works best and when it might not be ideal
- Be complete, but tight in your framing

Return JSON object with:
{{
    "recommendations": [
        {{
            "name": "Specific insight name (from Reddit)",
            "description": "What it is and why Reddit users recommend it",
            "pros": "What Reddit users love about it",
            "cons": "Any issues, criticisms, or downsides found (if any)",
            "reasoning": "Overall assessment based on Reddit community feedback",
            "reddit_sources": ["Array of Reddit post URLs that supported this insight"]
        }}
    ],
    "additional_notes": "Any additional context, general advice, warnings, or observations that applies broadly but doesn't fit into specific insights. Include things like: general trends you noticed, timing considerations, budget advice, common mistakes to avoid, or alternative approaches that came up during research."
}}"""


def get_search_results_summary_prompt(search_data: str) -> str:
    """Generate prompt for summarizing Reddit search results."""
    return f"""Summarize these Reddit search results, extracting key patterns and themes.

Search Results Data:
{search_data}

Instructions:
- Identify the most frequently mentioned products/places/services
- Note common themes and trends across posts
- Highlight posts with high engagement (upvotes, comments)
- Extract specific names, brands, and insights
- Keep summary under 200 words

Return a concise summary focusing on actionable insights and consensus patterns."""


def get_comments_summary_prompt(comments_data: str) -> str:
    """Generate prompt for summarizing Reddit comment analysis."""
    return f"""Summarize these Reddit comments, focusing on community consensus and sentiment.

Comments Data:
{comments_data}

Instructions:
- Identify consensus vs disagreement patterns
- Extract highly upvoted insights and community consensus
- Note expert vs casual opinions (look for detailed explanations)
- Highlight specific product/service endorsements
- Flag any warnings or negative experiences
- Keep summary under 200 words

Return a concise analysis of community sentiment and key takeaways."""


def get_research_data_summary_prompt(original_query: str, full_data: str) -> str:
    """Generate prompt for overall research data synthesis."""
    return f"""CRITICAL: Compress this Reddit research data into essential insights for: "{original_query}"

Full Research Data:
{full_data}

COMPRESSION REQUIREMENTS:
- Extract ONLY the strongest insights with clear community support
- List specific product/service names, brands, places that are repeatedly mentioned
- Include key consensus patterns (pricing, timing, warnings)
- Preserve specific Reddit post URLs/sources that validate insights
- Remove redundant information and focus on actionable insights
- MAXIMUM 800 words - prioritize quality over quantity

Format as structured bullet points for maximum information density:

**Top Recommendations:**
- [Specific name]: [Why Reddit users recommend it]

**Community Consensus:**
- [Key patterns/themes across multiple posts]

**Warnings/Issues:**
- [Any significant negative feedback]

**Sources:**
- [Key Reddit post URLs that support findings]

Focus on direct answers to the original query with specific, actionable information."""
