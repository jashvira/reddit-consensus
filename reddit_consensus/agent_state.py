from dataclasses import dataclass, field
from typing import List, Dict, Any
from .colors import print_colored


@dataclass
class AgentState:
    """Tracks the agent's reasoning process and gathered information"""

    original_query: str = ""
    research_data: Dict[str, Any] = field(default_factory=dict)
    reasoning_steps: List[str] = field(default_factory=list)
    draft_recommendations: List[Dict] = field(default_factory=list)
    final_recommendations: List[Dict] = field(default_factory=list)
    additional_notes: str = ""
    completed: bool = False

    def add_reasoning_step(self, step: str):
        self.reasoning_steps.append(step)
        print_colored("STEP", step)

    def add_research_data(self, key: str, data: Any):
        self.research_data[key] = data
