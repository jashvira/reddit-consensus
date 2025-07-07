import asyncio
import json
import os
from typing import Any

from openai import OpenAI

from .agent_state import AgentState
from .colors import (
    console,
    print_colored,
    print_phase_header,
    print_recommendations_table,
    render_dashboard,
)
from .prompts import (
    get_critique_prompt,
    get_draft_recommendations_prompt,
    get_final_recommendations_prompt,
    get_reasoning_prompt,
)
from .tools import reddit_get_post_comments, reddit_search_for_posts


class AutonomousRedditConsensus:
    """Autonomous agent for Reddit consensus-driven recommendations"""

    def __init__(self, api_key: str | None = None, recommendation_count: int = None):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.state = AgentState()

        # Import here to avoid circular imports
        from .config import (
            DEFAULT_MODEL_MAX_TOKENS,
            DEFAULT_MODEL_NAME,
            DEFAULT_RECOMMENDATION_COUNT,
        )

        self.recommendation_count = recommendation_count or DEFAULT_RECOMMENDATION_COUNT

        # Use simple config defaults
        self.model_name = DEFAULT_MODEL_NAME
        self.model_max_tokens = DEFAULT_MODEL_MAX_TOKENS

        # Single tool registry - only async functions
        self.tools = {
            "reddit_search_for_posts": reddit_search_for_posts,
            "reddit_get_post_comments": reddit_get_post_comments,
        }

        self.max_iterations = 10

    # ===== UTILITY METHODS =====

    def _get_tools_description(self) -> str:
        """Get available tools description from function docstrings"""
        descriptions = []
        for name, func in self.tools.items():
            # Extract first line of docstring as description
            if func.__doc__:
                desc = func.__doc__.strip().split("\n")[0]
            else:
                desc = "No description available"
            descriptions.append(f"- {name}: {desc}")
        return "\n".join(descriptions)

    def _call_llm_with_json_retry(self, prompt: str, fallback_result: Any) -> Any:
        """Call LLM with retry logic for JSON parsing"""
        for attempt in range(2):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=self.model_max_tokens,
                )

                content = response.choices[0].message.content.strip()

                # Remove any markdown code blocks if present
                if content.startswith("```json"):
                    content = content[7:-3].strip()
                elif content.startswith("```"):
                    content = content[3:-3].strip()

                parsed = json.loads(content)
                return parsed

            except json.JSONDecodeError as e:
                print(f"JSON parse error (attempt {attempt + 1}): {e}")
                if attempt == 0:
                    print("Retrying...")
                    continue
                else:
                    print(f"Raw response: {response.choices[0].message.content}")
                    return fallback_result
            except Exception as e:
                print(f"LLM call error: {e}")
                return fallback_result

        return fallback_result

    def _log_tool_start(
        self, tool_name: str, params: dict[str, Any], prefix: str = ""
    ) -> None:
        """Log tool execution start with parameters"""
        from .colors import get_friendly_tool_name

        friendly_name = get_friendly_tool_name(tool_name)
        print_colored("TOOL", f"{prefix}Using: {friendly_name}")

        # Log tool-specific information
        if tool_name == "reddit_search_for_posts":
            print_colored("SEARCH", f"{prefix}Search: {params.get('query', 'N/A')}")
        elif tool_name == "reddit_get_post_comments":
            post_id = params.get("post_id", "N/A")
            post_title = self._find_post_title(post_id)
            print_colored("POST", f"{prefix}Post: {post_title[:80]}...")

    def _log_tool_results(self, tool_name: str, result: str, prefix: str = "") -> None:
        """Log tool execution results in a readable format"""
        try:
            result_data = json.loads(result)
            if tool_name == "reddit_search_for_posts" and "results" in result_data:
                print(f"   {prefix}Found {len(result_data['results'])} posts:")
                for post in result_data["results"][:3]:  # Show first 3
                    print(f"   {prefix}• {post.get('title', 'No title')[:80]}...")
            elif tool_name == "reddit_get_post_comments" and "comments" in result_data:
                print(f"   {prefix}Found {len(result_data['comments'])} comments")
                if result_data.get("post_title"):
                    print(f"   {prefix}Post: {result_data['post_title'][:80]}...")
            elif (
                tool_name == "reddit_get_post_comments"
                and "comment_tree" in result_data
            ):
                comment_tree = result_data["comment_tree"]
                total_replies = sum(
                    self._count_replies(comment) for comment in comment_tree
                )
                print(
                    f"   {prefix}Found {len(comment_tree)} comments with {total_replies} replies"
                )
                if result_data.get("post_title"):
                    print(f"   {prefix}Post: {result_data['post_title'][:80]}...")
        except (json.JSONDecodeError, KeyError):
            pass

    def _count_replies(self, comment: dict[str, Any]) -> int:
        """Count total replies in a comment tree"""
        count = len(comment.get("replies", []))
        for reply in comment.get("replies", []):
            count += self._count_replies(reply)
        return count

    def _normalize_tool_requests(
        self, decision: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Normalize single or multiple tool requests to consistent list format"""
        if decision.get("action") == "use_tool":
            return [
                {
                    "tool_name": decision.get("tool_name"),
                    "tool_params": decision.get("tool_params", {}),
                }
            ]
        elif decision.get("action") == "use_tools":
            return decision.get("tools", [])
        else:
            return []

    def _store_tool_results(
        self,
        results: list[dict[str, Any]],
        mode: str,
        iteration: int,
        prefix: str,
        context: str,
    ) -> str:
        """Store tool execution results with consistent key generation"""
        for tool_result in results:
            tool_name = tool_result["tool_name"]
            result = tool_result["result"]

            # Generate consistent storage key
            if len(results) == 1:
                # Single tool execution
                data_key = f"{mode}_{tool_name}_{iteration}"
            else:
                # Multiple tool execution
                data_key = f"{mode}_{tool_name}_{iteration}_{tool_result['index']}"

            self.state.add_research_data(data_key, result)
            context += f"\n\n{prefix}Tool {tool_name}: {result}"

        return context

    # ===== REASONING TURNS =====

    def _reasoning_turn(self, context: str) -> dict[str, Any]:
        """Execute one reasoning turn"""
        prompt = get_reasoning_prompt(
            tools_description=self._get_tools_description(),
            original_query=self.state.original_query,
            research_data_keys=list(self.state.research_data.keys()),
            reasoning_steps_count=len(self.state.reasoning_steps),
            context=context,
        )

        fallback_result = {
            "action": "finalize",
            "reasoning": "JSON parse error, finalizing",
        }
        parsed = self._call_llm_with_json_retry(prompt, fallback_result)

        if not isinstance(parsed, dict) or "action" not in parsed:
            print(f"Invalid response format: {parsed}")
            return {"action": "finalize", "reasoning": "Invalid response format"}
        return parsed

    def _critique_turn(self, context: str) -> dict[str, Any]:
        """Execute one critique reasoning turn"""
        prompt = get_critique_prompt(
            original_query=self.state.original_query, context=context
        )

        fallback_result = {
            "action": "finalize",
            "reasoning": "JSON parse error, finalizing",
        }
        parsed = self._call_llm_with_json_retry(prompt, fallback_result)

        if not isinstance(parsed, dict) or "action" not in parsed:
            print(f"Invalid response format: {parsed}")
            return {"action": "finalize", "reasoning": "Invalid response format"}
        return parsed

    # ===== TOOL EXECUTION =====

    async def _execute_single_tool(self, tool_name: str, params: dict[str, Any]) -> str:
        """Execute a single tool without logging"""
        if tool_name not in self.tools:
            return f"Tool {tool_name} not found"

        try:
            return await self.tools[tool_name](**params)
        except Exception as e:
            return f"Error: {str(e)}"

    async def _execute_tools(
        self,
        tool_requests: list[dict[str, Any]],
        log_results: bool = True,
        prefix: str = "",
    ) -> list[dict[str, Any]]:
        """Execute tools (single or multiple) with optional logging"""
        if log_results and len(tool_requests) > 1:
            print_colored(
                "PARALLEL", f"{prefix}Using {len(tool_requests)} tools in parallel"
            )

        tasks = []
        for i, tool_request in enumerate(tool_requests):
            tool_name = tool_request.get("tool_name")
            params = tool_request.get("tool_params", {})

            # Log individual tool start for single tool execution
            if log_results and len(tool_requests) == 1:
                self._log_tool_start(tool_name, params, prefix)

            # Create async task for each tool
            task = self._execute_single_tool(tool_name, params)
            tasks.append((i, tool_name, params, task))

        # Execute all tasks in parallel
        results = []
        completed_tasks = await asyncio.gather(
            *[task for _, _, _, task in tasks], return_exceptions=True
        )

        # Process results and maintain order
        for i, (original_index, tool_name, params, _) in enumerate(tasks):
            result = completed_tasks[i]
            if isinstance(result, Exception):
                result = f"Error: {str(result)}"

            # Log individual tool completion if requested
            if log_results:
                if len(tool_requests) == 1:
                    # Single tool - just log results
                    self._log_tool_results(tool_name, result, prefix)
                else:
                    # Multiple tools - log completion status and results
                    from .colors import get_friendly_tool_name

                    friendly_name = get_friendly_tool_name(tool_name)
                    console.print(
                        f"   [green][DONE][/green] {prefix}{friendly_name}: ", end=""
                    )
                    if tool_name == "reddit_search_for_posts":
                        console.print(f"'{params.get('query', 'N/A')}'")
                    elif tool_name == "reddit_get_post_comments":
                        post_id = params.get("post_id", "N/A")
                        post_title = self._find_post_title(post_id)
                        console.print(f"'{post_title[:50]}...'")
                    else:
                        console.print("completed")

                    self._log_tool_results(tool_name, result, prefix)

            results.append(
                {
                    "tool_name": tool_name,
                    "tool_params": params,
                    "result": result,
                    "index": original_index,
                }
            )

        return sorted(results, key=lambda x: x["index"])

    def _find_post_title(self, post_id: str) -> str:
        """Find post title from previous search results"""
        for search_result in self.state.research_data.values():
            try:
                search_data = json.loads(search_result)
                if "results" in search_data:  # Reddit search returns "results" key
                    for post in search_data["results"]:
                        if post.get("post_id") == post_id:
                            return post.get("title", "No title")
            except (json.JSONDecodeError, KeyError):
                continue
        return "Unknown Post"

    def _generate_draft_recommendations(self) -> list[dict]:
        """Generate draft recommendations for critique"""
        prompt = get_draft_recommendations_prompt(
            original_query=self.state.original_query,
            research_data=self.state.research_data,
            reasoning_steps=self.state.reasoning_steps,
            recommendation_count=self.recommendation_count,
        )

        fallback_result = {
            "recommendations": [
                {
                    "name": "Error",
                    "description": "Could not parse draft recommendations",
                    "reasoning": "JSON parsing failed",
                }
            ]
        }
        result = self._call_llm_with_json_retry(prompt, fallback_result)

        # Handle both new structure (dict with recommendations) and old structure (list)
        if isinstance(result, dict) and "recommendations" in result:
            return result["recommendations"]
        else:
            # Fallback for old structure or error case
            return result if isinstance(result, list) else []

    # ===== RECOMMENDATION GENERATION =====

    def _generate_final_recommendations(self) -> dict[str, Any]:
        """Generate final recommendations incorporating critique findings"""
        prompt = get_final_recommendations_prompt(
            original_query=self.state.original_query,
            research_data=self.state.research_data,
            draft_recommendations=self.state.draft_recommendations,
            recommendation_count=self.recommendation_count,
        )

        fallback_result = {
            "recommendations": [
                {
                    "name": "Error",
                    "description": "Could not parse recommendations",
                    "reasoning": "JSON parsing failed",
                }
            ],
            "additional_notes": "",
        }
        return self._call_llm_with_json_retry(prompt, fallback_result)

    # ===== PROCESSING PHASES =====

    async def _run_research_phase(self, mode: str = "initial") -> str:
        """Run research phase asynchronously - supports both initial and critique modes"""
        if mode == "initial":
            context = f"User query: {self.state.original_query}"
            reasoning_method = self._reasoning_turn
            prefix = ""
            finalize_msg = "Finalizing initial research"
        else:  # critique mode
            context = f"Draft recommendations: {self.state.draft_recommendations}"
            reasoning_method = self._critique_turn
            prefix = "Critique "
            finalize_msg = "Finalizing critique"

        for i in range(self.max_iterations):
            print(f"\n {prefix}Iteration {i + 1}")

            decision = reasoning_method(context)
            self.state.add_reasoning_step(decision.get("reasoning", ""))

            if decision.get("action") in ["use_tool", "use_tools"]:
                # Normalize to unified tool request format
                tool_requests = self._normalize_tool_requests(decision)

                # Execute tools (single or multiple)
                results = await self._execute_tools(
                    tool_requests, log_results=False, prefix=prefix
                )

                # Show results in elegant dashboard layout
                render_dashboard(results)

                # Store results with unified logic
                context = self._store_tool_results(results, mode, i, prefix, context)

            else:  # finalize
                console.print(f" {finalize_msg}")
                break

        return context

    def _finalize_recommendations(self):
        """Generate and store final recommendations"""
        print_phase_header("Phase 4: Final Recommendations")
        result = self._generate_final_recommendations()

        # Handle both new structure (dict with recommendations + additional_notes) and old structure (list)
        if isinstance(result, dict) and "recommendations" in result:
            self.state.final_recommendations = result["recommendations"]
            self.state.additional_notes = result.get("additional_notes", "")
        else:
            # Fallback for old structure or error case
            self.state.final_recommendations = (
                result if isinstance(result, list) else []
            )
            self.state.additional_notes = ""

        self.state.completed = True

    async def process_query(self, user_query: str) -> dict[str, Any]:
        """Main processing method - orchestrates the full recommendation pipeline"""
        print_phase_header(
            "Reddit Consensus Agent", f"Processing: {user_query[:100]}..."
        )

        # Show current configuration
        print_colored("USING", f"{self.model_name}")

        # Setup
        self.state.original_query = user_query

        # Phase 1: Initial Research
        await self._run_research_phase()

        # Phase 2: Generate Draft Recommendations
        print_phase_header("Phase 2: Draft Recommendations")
        self.state.draft_recommendations = self._generate_draft_recommendations()

        # Phase 3: Critique Research
        print_phase_header("Phase 3: Critical Analysis")
        await self._run_research_phase(mode="critique")

        # Phase 4: Final Recommendations
        self._finalize_recommendations()

        return {
            "recommendations": self.state.final_recommendations,
            "additional_notes": self.state.additional_notes,
            "steps": len(self.state.reasoning_steps),
        }

    # ===== OUTPUT METHODS =====

    def print_results(self):
        """Print formatted results"""
        print_phase_header("Final Recommendations")
        print_recommendations_table(self.state.final_recommendations)

        # Print additional notes if available
        if self.state.additional_notes:
            from .colors import print_additional_notes

            print_additional_notes(self.state.additional_notes)

        console.print(
            f"\n[bold]Process completed in {len(self.state.reasoning_steps)} reasoning steps[/bold]"
        )
