import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from openai import OpenAI

from agent_state import AgentState
from tools import RedditSearchForPostsTool, RedditGetCommentsTool
from prompts import get_reasoning_prompt, get_draft_recommendations_prompt, get_critique_prompt, get_final_recommendations_prompt

# Global model configuration
MODEL_NAME = "gpt-4.1"


class AutonomousRedditConsensus:
    """Autonomous agent for Reddit consensus-driven recommendations"""

    def __init__(self, api_key: Optional[str] = None):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.state = AgentState()
        self.tools = {
            "reddit_search_for_posts": RedditSearchForPostsTool(),
            "reddit_get_post_comments": RedditGetCommentsTool(),
        }
        self.max_iterations = 20

    # ===== UTILITY METHODS =====

    def _get_tools_description(self) -> str:
        """Get available tools description"""
        return "\n".join(
            [f"- {tool.name()}: {tool.description()}" for tool in self.tools.values()]
        )

    def _call_llm_with_retry(self, prompt: str, fallback_result: Any) -> Any:
        """Call LLM with retry logic for JSON parsing"""
        for attempt in range(2):
            try:
                response = self.client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                )

                content = response.choices[0].message.content.strip()

                # Remove any markdown code blocks if present
                if content.startswith('```json'):
                    content = content[7:-3].strip()
                elif content.startswith('```'):
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

    # ===== REASONING TURNS =====

    async def _reasoning_turn_async(self, context: str) -> Dict[str, Any]:
        """Execute one reasoning turn asynchronously"""
        prompt = get_reasoning_prompt(
            tools_description=self._get_tools_description(),
            original_query=self.state.original_query,
            research_data_keys=list(self.state.research_data.keys()),
            reasoning_steps_count=len(self.state.reasoning_steps),
            context=context
        )

        fallback_result = {"action": "finalize", "reasoning": "JSON parse error, finalizing"}
        parsed = self._call_llm_with_retry(prompt, fallback_result)

        if not isinstance(parsed, dict) or "action" not in parsed:
            print(f"Invalid response format: {parsed}")
            return {"action": "finalize", "reasoning": "Invalid response format"}
        return parsed

    def _reasoning_turn(self, context: str) -> Dict[str, Any]:
        """Execute one reasoning turn (sync wrapper)"""
        return asyncio.run(self._reasoning_turn_async(context))

    async def _critique_turn_async(self, context: str) -> Dict[str, Any]:
        """Execute one critique reasoning turn asynchronously"""
        prompt = get_critique_prompt(
            original_query=self.state.original_query,
            context=context
        )

        fallback_result = {"action": "finalize", "reasoning": "JSON parse error, finalizing"}
        parsed = self._call_llm_with_retry(prompt, fallback_result)

        if not isinstance(parsed, dict) or "action" not in parsed:
            print(f"Invalid response format: {parsed}")
            return {"action": "finalize", "reasoning": "Invalid response format"}
        return parsed

    def _critique_turn(self, context: str) -> Dict[str, Any]:
        """Execute one critique reasoning turn (sync wrapper)"""
        return asyncio.run(self._critique_turn_async(context))

    # ===== TOOL EXECUTION =====

    def _execute_tool(self, tool_name: str, params: Dict[str, Any]) -> str:
        """Execute a tool"""
        if tool_name not in self.tools:
            return f"Tool {tool_name} not found"

        try:
            return self.tools[tool_name].execute(**params)
        except Exception as e:
            return f"Error: {str(e)}"

    async def _execute_tool_async(self, tool_name: str, params: Dict[str, Any]) -> str:
        """Execute a tool asynchronously"""
        if tool_name not in self.tools:
            return f"Tool {tool_name} not found"

        try:
            return await self.tools[tool_name].execute_async(**params)
        except Exception as e:
            return f"Error: {str(e)}"

    async def _execute_tools_parallel(self, tool_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute multiple tools in parallel"""
        tasks = []
        for i, tool_request in enumerate(tool_requests):
            tool_name = tool_request.get("tool_name")
            params = tool_request.get("tool_params", {})

            # Create async task for each tool
            task = self._execute_tool_async(tool_name, params)
            tasks.append((i, tool_name, params, task))

        # Execute all tasks in parallel
        results = []
        completed_tasks = await asyncio.gather(*[task for _, _, _, task in tasks], return_exceptions=True)

        # Process results and maintain order
        for i, (original_index, tool_name, params, _) in enumerate(tasks):
            result = completed_tasks[i]
            if isinstance(result, Exception):
                result = f"Error: {str(result)}"

            results.append({
                "tool_name": tool_name,
                "tool_params": params,
                "result": result,
                "index": original_index
            })

        return sorted(results, key=lambda x: x["index"])

    def _execute_and_log_tool(self, tool_name: str, params: Dict[str, Any]) -> str:
        """Execute a tool and log the activity with formatted output"""
        print(f"🔧 Using: {tool_name}")

        # Log tool-specific information
        if tool_name == "reddit_search_for_posts":
            print(f"🔍 Search: {params.get('query', 'N/A')}")
        elif tool_name == "reddit_get_post_comments":
            post_id = params.get('post_id', 'N/A')
            post_title = self._find_post_title(post_id)
            print(f"📖 Post: {post_title[:80]}...")

        # Execute the tool
        result = self._execute_tool(tool_name, params)

        # Show readable summary of results
        self._log_tool_results(tool_name, result)

        return result

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

    def _log_tool_results(self, tool_name: str, result: str):
        """Log tool execution results in a readable format"""
        try:
            result_data = json.loads(result)
            if tool_name == "reddit_search_for_posts" and "results" in result_data:
                print(f"   Found {len(result_data['results'])} posts:")
                for post in result_data['results'][:3]:  # Show first 3
                    print(f"   • {post.get('title', 'No title')[:80]}...")
            elif tool_name == "reddit_get_post_comments" and "comments" in result_data:
                print(f"   Found {len(result_data['comments'])} comments")
                if result_data.get('post_title'):
                    print(f"   Post: {result_data['post_title'][:80]}...")
        except (json.JSONDecodeError, KeyError):
            pass

    def _generate_draft_recommendations(self) -> List[Dict]:
        """Generate draft recommendations for critique"""
        prompt = get_draft_recommendations_prompt(
            original_query=self.state.original_query,
            research_data=self.state.research_data,
            reasoning_steps=self.state.reasoning_steps
        )

        fallback_result = [{"name": "Error", "description": "Could not parse draft recommendations", "reasoning": "JSON parsing failed"}]
        return self._call_llm_with_retry(prompt, fallback_result)

    # ===== RECOMMENDATION GENERATION =====

    def _generate_final_recommendations(self) -> List[Dict]:
        """Generate final recommendations incorporating critique findings"""
        prompt = get_final_recommendations_prompt(
            original_query=self.state.original_query,
            research_data=self.state.research_data,
            draft_recommendations=self.state.draft_recommendations
        )

        fallback_result = [{"name": "Error", "description": "Could not parse recommendations", "reasoning": "JSON parsing failed"}]
        return self._call_llm_with_retry(prompt, fallback_result)

    # ===== PROCESSING PHASES =====

    def _run_research_phase(self) -> str:
        """Run the initial research phase"""
        return asyncio.run(self._run_research_phase_async())

    async def _run_research_phase_async(self) -> str:
        """Run the initial research phase asynchronously"""
        context = f"User query: {self.state.original_query}"

        for i in range(self.max_iterations):
            print(f"\n Iteration {i + 1}")

            decision = await self._reasoning_turn_async(context)
            self.state.add_reasoning_step(decision.get("reasoning", ""))

            if decision.get("action") == "use_tool":
                # Single tool execution
                tool_name = decision.get("tool_name")
                params = decision.get("tool_params", {})

                result = self._execute_and_log_tool(tool_name, params)
                self.state.add_research_data(tool_name, result)
                context += f"\n\nTool {tool_name}: {result}"

            elif decision.get("action") == "use_tools":
                # Multiple tools execution in parallel
                tool_requests = decision.get("tools", [])
                print(f"🔧 Using {len(tool_requests)} tools in parallel")

                # Execute tools in parallel
                results = await self._execute_tools_parallel(tool_requests)

                # Log and store results
                for tool_result in results:
                    tool_name = tool_result["tool_name"]
                    params = tool_result["tool_params"]
                    result = tool_result["result"]

                    # Log with tool-specific formatting
                    print(f"   ✅ {tool_name}: ", end="")
                    if tool_name == "reddit_search_for_posts":
                        print(f"'{params.get('query', 'N/A')}'")
                    elif tool_name == "reddit_get_post_comments":
                        post_id = params.get('post_id', 'N/A')
                        post_title = self._find_post_title(post_id)
                        print(f"'{post_title[:50]}...'")
                    else:
                        print("completed")

                    # Log tool results
                    self._log_tool_results(tool_name, result)

                    # Store results
                    self.state.add_research_data(f"{tool_name}_{i}_{tool_result['index']}", result)
                    context += f"\n\nTool {tool_name}: {result}"

            else:  # finalize
                print(" Finalizing initial research")
                break

        return context

    def _run_critique_phase(self):
        """Run the critique research phase"""
        asyncio.run(self._run_critique_phase_async())

    async def _run_critique_phase_async(self):
        """Run the critique research phase asynchronously"""
        print("\n Critiquing recommendations...")
        critique_context = f"Draft recommendations: {self.state.draft_recommendations}"

        for i in range(self.max_iterations):
            print(f"\n Critique Iteration {i + 1}")

            decision = await self._critique_turn_async(critique_context)
            self.state.add_reasoning_step(decision.get("reasoning", ""))

            if decision.get("action") == "use_tool":
                # Single tool execution
                tool_name = decision.get("tool_name")
                params = decision.get("tool_params", {})

                # Add critique prefix to search queries for clarity
                if tool_name == "reddit_search_for_posts":
                    print(f"🔧 Using: {tool_name}")
                    print(f"🔍 Critique Search: {params.get('query', 'N/A')}")
                    result = self._execute_tool(tool_name, params)
                    self._log_tool_results(tool_name, result)
                else:
                    # For comments, use standard logging (no duplicate post title)
                    result = self._execute_and_log_tool(tool_name, params)

                self.state.add_research_data(f"critique_{tool_name}_{i}", result)
                critique_context += f"\n\nCritique Tool {tool_name}: {result}"

            elif decision.get("action") == "use_tools":
                # Multiple tools execution in parallel for critique
                tool_requests = decision.get("tools", [])
                print(f"🔧 Critiquing with {len(tool_requests)} tools in parallel")

                # Execute tools in parallel
                results = await self._execute_tools_parallel(tool_requests)

                # Log and store results
                for tool_result in results:
                    tool_name = tool_result["tool_name"]
                    params = tool_result["tool_params"]
                    result = tool_result["result"]

                    # Log with critique-specific formatting
                    print(f"   🔍 Critique {tool_name}: ", end="")
                    if tool_name == "reddit_search_for_posts":
                        print(f"'{params.get('query', 'N/A')}'")
                    elif tool_name == "reddit_get_post_comments":
                        post_id = params.get('post_id', 'N/A')
                        post_title = self._find_post_title(post_id)
                        print(f"'{post_title[:50]}...'")
                    else:
                        print("completed")

                    # Log tool results
                    self._log_tool_results(tool_name, result)

                    # Store results
                    self.state.add_research_data(f"critique_{tool_name}_{i}_{tool_result['index']}", result)
                    critique_context += f"\n\nCritique Tool {tool_name}: {result}"

            else:  # finalize critique
                print(" Finalizing critique")
                break

    def _finalize_recommendations(self):
        """Generate and store final recommendations"""
        print("\n Generating final recommendations...")
        self.state.final_recommendations = self._generate_final_recommendations()
        self.state.completed = True

    def process_query(self, user_query: str) -> Dict[str, Any]:
        """Main processing method - orchestrates the full recommendation pipeline"""
        print(f"Processing: {user_query[:100]}...")
        print("=" * 50)

        # Setup
        self.state.original_query = user_query

        # Phase 1: Initial Research
        self._run_research_phase()

        # Phase 2: Generate Draft Recommendations
        print("\n Generating draft recommendations...")
        self.state.draft_recommendations = self._generate_draft_recommendations()

        # Phase 3: Critique Research
        self._run_critique_phase()

        # Phase 4: Final Recommendations
        self._finalize_recommendations()

        return {
            "recommendations": self.state.final_recommendations,
            "steps": len(self.state.reasoning_steps),
        }

    # ===== OUTPUT METHODS =====

    def print_results(self):
        """Print formatted results"""
        print("\n" + "=" * 50)
        print(" RECOMMENDATIONS")
        print("=" * 50)

        for i, rec in enumerate(self.state.final_recommendations, 1):
            print(f"\n{i}. {rec.get('name', 'Recommendation')}")
            print(f"   {rec.get('description', '')}")
            if rec.get("pros"):
                print(f"   ✅ Pros: {rec['pros']}")
            if rec.get("cons"):
                print(f"   ❌ Cons: {rec['cons']}")
            if rec.get("reasoning"):
                print(f"   💡 {rec['reasoning']}")
            if rec.get("reddit_sources"):
                print(f"   🔗 Sources: {', '.join(rec['reddit_sources'])}")

        print(f"\n Process: {len(self.state.reasoning_steps)} steps")
