# Production-Ready Agent Engineering: The Real Alpha

**Will Brown's Core Insights from Agent Patterns Lecture**

## Model Selection Strategy

**"Agent" Models (Primary Workhorses):**
- **DeepSeek V3-0324**: The sleeper hit - cheap, reliable, no distillation restrictions, free prefix caching
- **GPT-4.1**: More "agentic", less chatty than GPT-4o - better for tool calling
- **Claude 4 Sonnet + Gemini 2.5 Pro**: Strong all-around, configurable thinking budgets

**"Helper" Models (Mini Agents):**
- GPT-4.1-mini/nano, Gemini 2.5 Flash, Claude 3.5 Haiku
- Mistral Small 3.1 (24B) - permissive license, popular finetuning base
- Qwen 2.5/3 models - "thinking optional", great for finetuning

**Avoid (Proceed with Caution):**
- o3, R1, o4-mini: "Reasoning" models are slow, expensive, prone to overthinking
- Often overkill for most tasks requiring low latency + many tool calls

## The Tool Calling Evolution

**The Painful Truth:** DIY tool calling is fragile and unreliable
- Manual JSON parsing fails constantly
- CoT prompting doesn't solve structured output issues
- Native tool calling (OpenAI format) is the only reliable path

**Structured Output Hierarchy:**
1. **Native OpenAI structured outputs** (pydantic) - gold standard
2. **Instructor library** - works across providers with fallback modes
3. **XML parsing** - surprisingly robust for complex outputs
4. **JSON mode** - basic but widely supported

## ReAct Pattern Reality Check

**Multiple Flavors, Same Core Issues:**
- OpenAI Agents SDK: Clean but vendor lock-in
- HF SmolAgents: Good open-source alternative 
- DSPy ReAct: Powerful but complex
- Letta: First-class memory but hard to eval

**Key Learning:** The framework matters less than understanding the underlying pattern and tool reliability.

## The Evaluation Problem

**Ground Truth is Broken:**
- LLM judges using G-Eval are inconsistent
- Exact string matching is too strict ("$8.1 billion" ≠ "8.1 billion")
- Embedding similarity (0.64 similarity for equivalent answers) shows semantic understanding but needs tuning

**Will's Real Alpha:** Build evaluation that matches your actual use case, not academic benchmarks.

## Production Insights

**State Management Reality:**
- Manual conversation history tracking is error-prone
- OpenAI Responses API handles state automatically but creates vendor lock-in
- Most frameworks don't solve the fundamental state problem

**Tool Chain Complexity:**
The demo search agent shows the real challenge - multiple tool calls, error handling, and maintaining context across a conversation that spans 10+ turns.

**Memory vs Stateless Trade-offs:**
- Stateful agents (Letta) are powerful but hard to debug
- Stateless ReAct patterns are predictable but lose context
- Production systems need hybrid approaches

## The Unspoken Truth

**From the notebook evidence:** Most agent frameworks are demos, not production systems. The real work is in:
1. Reliable structured output parsing
2. Robust error handling across tool chains  
3. Evaluation that matches business logic
4. Model selection based on latency/cost trade-offs, not benchmarks

**Will's Hidden Message:** Focus on the fundamentals (structured outputs, tool reliability, proper evaluation) rather than chasing the latest agent framework. The tools that work in production are often the boring, well-tested ones.