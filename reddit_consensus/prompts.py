"""
Prompt templates for the Reddit Consensus system.
Centralizes all LLM prompts for better maintainability.
"""


def get_reasoning_prompt(tools_description: str, original_query: str, research_data_keys: list, reasoning_steps_count: int, context: str) -> str:
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
- CRITICAL: Get comments from promising posts to analyze how users perceive the OP's recommendations
- Analyze comment sentiment: Are users agreeing, disagreeing, or adding better alternatives?
- Look for patterns: Multiple users mentioning the same places/products indicates strong consensus
- Pay attention to upvoted comments - these represent community-validated opinions
- Evaluate if commenters are locals/experts or just casual visitors (local knowledge is more valuable)
- Only proceed with recommendations that have genuine positive community feedback
- Focus on finding specific product names, brands, or experiences that users love
- At least collect 5 strong sources of information.
- Once you have enough Reddit recommendations and user opinions, finalize

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
            "tool_name": "reddit_search_for_posts", 
            "tool_params": {{"query": "search query 2"}}
        }},
        {{
            "tool_name": "reddit_get_post_comments",
            "tool_params": {{"post_id": "post_id_here"}}
        }}
    ],
    "reasoning": "why you're using these tools together"
}}

For finishing:
{{
    "action": "finalize",
    "reasoning": "why you're done"
}}"""


def get_draft_recommendations_prompt(original_query: str, research_data: dict, reasoning_steps: list) -> str:
    """Generate the draft recommendations prompt."""
    return f"""Based on your Reddit research so far, create 3 draft recommendations for the user.

Original Query: {original_query}

Reddit Research: {research_data}

Research Process: {reasoning_steps}

Create 3 draft recommendations based on what you've found. These will be critiqued next.

Return JSON array with objects containing:
- name: Specific recommendation name
- description: Brief description
- reasoning: Why this seems good from Reddit research"""


def get_critique_prompt(original_query: str, context: str) -> str:
    """Generate the critique turn prompt."""
    return f"""You have generated draft recommendations. Now critically analyze them by searching for potential issues or negative feedback.

Original Query: {original_query}

{context}

Your task is to search for criticism, negative experiences, or issues with your draft recommendations. Look for:
- Negative reviews or complaints
- Issues mentioned by Reddit users
- Alternative viewpoints
- Potential problems or downsides

Search for discussions that might contradict or provide balance to your recommendations.

Respond in JSON format.

For single tool use:
{{
    "action": "use_tool",
    "tool_name": "reddit_search_for_posts",
    "tool_params": {{"query": "specific search query"}},
    "reasoning": "why you're searching for criticism"
}}

For multiple tools (RECOMMENDED - critique all recommendations simultaneously):
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


def get_final_recommendations_prompt(original_query: str, research_data: dict, draft_recommendations: list) -> str:
    """Generate the final recommendations prompt."""
    return f"""Based on your Reddit research AND critique findings, create 3 balanced recommendations for the user.

Original Query: {original_query}

Initial Reddit Research: {research_data}

Draft Recommendations: {draft_recommendations}

Critique Research: [Include any critique findings from additional research]

Requirements:
- Create 3 final recommendations based on ALL research (initial + critique)
- Include both positive aspects AND any discovered issues/criticisms
- Show balanced perspective from Reddit community
- Base everything on real Reddit comments and posts you found
- Be honest about any limitations or negative feedback discovered

Return JSON array with objects containing:
- name: Specific recommendation name (from Reddit)
- description: What it is and why Reddit users recommend it
- pros: What Reddit users love about it
- cons: Any issues, criticisms, or downsides found (if any)
- reasoning: Overall assessment based on Reddit community feedback
- reddit_sources: Array of Reddit post URLs that supported this recommendation"""
