from __future__ import annotations

from app.agents.base import AGENT_TOOL_NAMES, BaseAgent
from app.chat.tools import get_enabled_tools


class PlannerAgent(BaseAgent):
    name = "planner_agent"
    max_iterations = 10  # planners need more steps

    def get_system_prompt(self) -> str:
        return (
            "You are a Task Planner Agent. You decompose complex requests into steps "
            "and execute them methodically.\n\n"
            "Strategy:\n"
            "1. Analyze the user's request and identify all distinct sub-tasks\n"
            "2. Determine the optimal order of execution (some tasks depend on others)\n"
            "3. Execute each step using the available tools\n"
            "4. After each step, assess what you learned and adjust your plan if needed\n"
            "5. Compile all results into a final comprehensive response\n\n"
            "Important:\n"
            "- Start by briefly stating your plan before executing\n"
            "- Report the result of each step as you go\n"
            "- If a step fails, adapt your plan and continue\n"
            "- Provide a clear final summary that addresses the original request\n"
            "- Do not use <think> tags or show your reasoning process"
        )

    def get_tools(self) -> list[dict]:
        # All enabled tools except agent tools (to prevent recursion)
        return [t for t in get_enabled_tools() if t["name"] not in AGENT_TOOL_NAMES]
