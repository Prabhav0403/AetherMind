"""
Planner Agent: Decomposes complex research queries into structured subtasks
and generates a comprehensive research roadmap.
"""
import json
from typing import List
from agents.base_agent import BaseAgent
from config import settings
from models.schemas import (
    AgentType, AgentStatus, ResearchSession,
    ResearchPlan, ResearchSubtask
)


PLANNER_SYSTEM_PROMPT = """You are an expert research planning AI. Your role is to analyze 
complex research queries and decompose them into structured, actionable subtasks that can 
be executed by a team of specialized research agents.

You excel at:
- Identifying the core dimensions of a research question
- Breaking topics into logical, non-overlapping subtasks
- Generating precise search queries for each subtask  
- Defining the ideal report structure for the findings
- Estimating research complexity and required iterations

Always respond with valid JSON matching the requested schema exactly."""


class PlannerAgent(BaseAgent):
    """Decomposes user queries into research plans with subtasks."""

    def __init__(self):
        super().__init__(AgentType.PLANNER, settings.PLANNER_MODEL)

    async def run(self, session: ResearchSession, **kwargs) -> ResearchPlan:
        """Generate a comprehensive research plan for the given query."""
        self.log(session, AgentStatus.RUNNING,
                 "Analyzing query and creating research plan...",
                 {"query": session.query})

        plan = await self._generate_plan(session.query, session.query)
        session.plan = plan

        self.log(session, AgentStatus.COMPLETED,
                 f"Research plan created with {len(plan.subtasks)} subtasks",
                 {"subtask_count": len(plan.subtasks),
                  "report_sections": plan.report_structure})
        return plan

    async def _generate_plan(self, query: str, original_query: str) -> ResearchPlan:
        """Generate the research plan via LLM."""
        prompt = f"""Analyze this research query and create a detailed research plan.

RESEARCH QUERY: {query}

Create a comprehensive plan with:
1. A clear research objective
2. Scope definition (what is and isn't covered)
3. 4-7 specific subtasks, each with 2-3 targeted search queries
4. A structured report outline (section titles)
5. Estimated number of research iterations needed (1-5)

Respond with ONLY valid JSON in this exact format:
{{
  "objective": "Clear one-sentence statement of what will be researched",
  "scope": "Brief description of scope and boundaries",
  "subtasks": [
    {{
      "title": "Subtask title",
      "description": "What to research in this subtask",
      "search_queries": ["query1", "query2", "query3"],
      "priority": 1
    }}
  ],
  "report_structure": [
    "Abstract",
    "Introduction", 
    "Literature Review",
    "Methodology / Approaches",
    "Key Findings",
    "Analysis & Discussion",
    "Conclusion",
    "References"
  ],
  "estimated_iterations": 3
}}

Ensure subtasks cover ALL major aspects of the query with no significant gaps."""

        response = await self.invoke_llm(prompt, PLANNER_SYSTEM_PROMPT)
        data = self.parse_json_response(response)

        subtasks = [
            ResearchSubtask(
                title=t["title"],
                description=t["description"],
                search_queries=t.get("search_queries", []),
                priority=t.get("priority", 1),
            )
            for t in data.get("subtasks", [])
        ]

        return ResearchPlan(
            original_query=original_query,
            objective=data.get("objective", query),
            scope=data.get("scope", ""),
            subtasks=subtasks,
            report_structure=data.get("report_structure", [
                "Abstract", "Introduction", "Key Findings",
                "Analysis", "Conclusion", "References"
            ]),
            estimated_iterations=data.get("estimated_iterations", 3),
        )

    async def refine_plan(self, session: ResearchSession,
                          gaps: List[str]) -> List[ResearchSubtask]:
        """Generate additional subtasks to address identified gaps."""
        self.log(session, AgentStatus.RUNNING,
                 f"Refining plan to address {len(gaps)} identified gaps")

        prompt = f"""The research on "{session.query}" has identified these knowledge gaps:

GAPS:
{chr(10).join(f"- {g}" for g in gaps)}

Current subtasks already completed:
{chr(10).join(f"- {t.title}: {t.description}" for t in session.plan.subtasks)}

Generate 2-4 NEW subtasks specifically targeting these gaps. Each subtask must address 
gaps not already covered.

Respond with ONLY valid JSON:
{{
  "new_subtasks": [
    {{
      "title": "Gap-filling subtask title",
      "description": "Specific description of what to find",
      "search_queries": ["precise query 1", "precise query 2"],
      "priority": 1
    }}
  ]
}}"""

        response = await self.invoke_llm(prompt, PLANNER_SYSTEM_PROMPT)
        data = self.parse_json_response(response)

        new_subtasks = [
            ResearchSubtask(
                title=t["title"],
                description=t["description"],
                search_queries=t.get("search_queries", []),
                priority=t.get("priority", 1),
            )
            for t in data.get("new_subtasks", [])
        ]

        # Append to session plan
        if session.plan:
            session.plan.subtasks.extend(new_subtasks)

        self.log(session, AgentStatus.COMPLETED,
                 f"Added {len(new_subtasks)} gap-filling subtasks")
        return new_subtasks
