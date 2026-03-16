"""
Analyst Agent: Evaluates retrieved evidence, detects gaps and contradictions,
scores coverage, and drives the iterative refinement loop.

Inspired by Self-RAG and CRITIC frameworks.
"""
from typing import List
from agents.base_agent import BaseAgent
from config import settings
from models.schemas import (
    AgentType, AgentStatus, ResearchSession,
    Evidence, AnalysisResult, ResearchPlan
)


ANALYST_SYSTEM_PROMPT = """You are a rigorous research quality analyst and critic.
Your role is to evaluate retrieved evidence with extreme precision, identify gaps,
detect contradictions, and ensure research completeness before report generation.

You operate with the critical mindset of a peer reviewer:
- Question every claim: is it well-supported?
- Identify what's missing: what dimensions aren't covered?
- Flag contradictions: where do sources disagree?
- Score objectively: coverage and confidence metrics

Always respond with valid JSON matching the requested schema exactly."""


class AnalystAgent(BaseAgent):
    """Evaluates research quality and drives iterative refinement."""

    def __init__(self):
        super().__init__(AgentType.ANALYST, settings.ANALYST_MODEL)

    async def run(self, session: ResearchSession, **kwargs) -> AnalysisResult:
        """Analyze collected evidence and produce quality assessment."""
        self.log(session, AgentStatus.RUNNING,
                 f"Analyzing {len(session.evidence_collected)} evidence pieces "
                 f"(iteration {session.current_iteration})")

        iteration = session.current_iteration
        result = await self._evaluate_coverage(session)
        session.analysis_history.append(result)

        sufficient = (
            result.coverage_score >= settings.COVERAGE_THRESHOLD
            and result.confidence_score >= settings.ANALYST_CONFIDENCE_THRESHOLD
            and iteration >= session.max_iterations
            or (result.coverage_score >= 0.9 and result.confidence_score >= 0.9)
        )
        result.sufficient = sufficient

        self.log(
            session, AgentStatus.COMPLETED,
            f"Analysis complete: coverage={result.coverage_score:.2f}, "
            f"confidence={result.confidence_score:.2f}, "
            f"gaps={len(result.gaps)}, sufficient={sufficient}",
            {
                "coverage": result.coverage_score,
                "confidence": result.confidence_score,
                "gaps": result.gaps,
                "contradictions": result.contradictions,
                "sufficient": sufficient,
            }
        )
        return result

    async def _evaluate_coverage(self, session: ResearchSession) -> AnalysisResult:
        """Perform deep analysis of evidence quality and coverage."""
        plan = session.plan
        evidence = session.evidence_collected

        # Build subtask coverage map
        subtask_evidence: dict = {}
        for e in evidence:
            sid = e.subtask_id or "general"
            if sid not in subtask_evidence:
                subtask_evidence[sid] = []
            subtask_evidence[sid].append(e)

        # Format evidence for LLM
        evidence_summary = self._format_evidence_summary(evidence[:30])

        subtasks_text = "\n".join([
            f"- [{t.task_id[:8]}] {t.title}: {t.description}"
            for t in plan.subtasks
        ])

        report_sections = "\n".join(f"- {s}" for s in plan.report_structure)

        # Previous gaps for context
        prev_gaps = ""
        if session.analysis_history:
            prev = session.analysis_history[-1]
            prev_gaps = f"\nPrevious iteration gaps:\n" + "\n".join(
                f"- {g}" for g in prev.gaps
            )

        prompt = f"""Critically evaluate the research evidence collected for this query.

RESEARCH QUERY: "{session.query}"
RESEARCH OBJECTIVE: {plan.objective}
CURRENT ITERATION: {session.current_iteration}/{session.max_iterations}

REQUIRED SUBTASKS:
{subtasks_text}

REQUIRED REPORT SECTIONS:
{report_sections}

COLLECTED EVIDENCE ({len(evidence)} pieces):
{evidence_summary}
{prev_gaps}

Perform a rigorous quality assessment:

1. COVERAGE SCORE (0.0-1.0): How completely does the evidence cover ALL required subtasks?
   - 0.0-0.3: Very incomplete, major topics missing
   - 0.4-0.6: Partial coverage, significant gaps
   - 0.7-0.85: Good coverage, minor gaps
   - 0.86-1.0: Comprehensive, ready for final report

2. CONFIDENCE SCORE (0.0-1.0): How reliable and consistent is the evidence?

3. GAPS: List specific missing information needed for each uncovered subtask.

4. CONTRADICTIONS: List any conflicting claims found in the evidence.

5. ADDITIONAL QUERIES: If coverage < 0.85, provide 3-5 specific search queries 
   to fill the most critical gaps.

6. PER-SUBTASK COVERAGE: Estimate coverage (0.0-1.0) for each subtask by its task_id.

Respond with ONLY valid JSON:
{{
  "coverage_score": 0.72,
  "confidence_score": 0.80,
  "critique": "Brief overall assessment of the evidence quality",
  "gaps": [
    "Specific missing information 1",
    "Specific missing information 2"
  ],
  "contradictions": [
    "Source A claims X but source B claims Y"
  ],
  "additional_queries": [
    "specific targeted search query 1",
    "specific targeted search query 2"
  ],
  "subtask_coverage": {{
    "task_id_here": 0.8
  }}
}}"""

        response = await self.invoke_llm(prompt, ANALYST_SYSTEM_PROMPT)
        data = self.parse_json_response(response)

        return AnalysisResult(
            coverage_score=float(data.get("coverage_score", 0.5)),
            confidence_score=float(data.get("confidence_score", 0.5)),
            gaps=data.get("gaps", []),
            contradictions=data.get("contradictions", []),
            additional_queries=data.get("additional_queries", []),
            subtask_coverage=data.get("subtask_coverage", {}),
            critique=data.get("critique", ""),
            sufficient=False,  # Set by caller
            iteration=session.current_iteration,
        )

    def _format_evidence_summary(self, evidence: List[Evidence]) -> str:
        """Format evidence list into a compact summary for the LLM."""
        if not evidence:
            return "No evidence collected yet."

        lines = []
        for i, e in enumerate(evidence, 1):
            lines.append(
                f"[E{i}] Source: {e.source_doc} | "
                f"Relevance: {e.relevance_score:.2f} | "
                f"Subtask: {e.subtask_id[:8] if e.subtask_id else 'N/A'}\n"
                f"Content: {e.content[:300]}..."
            )
        return "\n\n".join(lines)

    async def generate_gap_queries(self, session: ResearchSession,
                                    gaps: List[str]) -> List[str]:
        """Generate targeted search queries to fill identified knowledge gaps."""
        if not gaps:
            return []

        prompt = f"""For the research query "{session.query}", generate targeted search 
queries to fill these specific knowledge gaps:

{chr(10).join(f"- {g}" for g in gaps)}

Generate 2-3 precise search queries per gap. Queries should be specific enough
to retrieve highly relevant documents.

Respond with ONLY valid JSON:
{{
  "queries": ["query1", "query2", "query3", "query4"]
}}"""

        try:
            response = await self.invoke_llm(prompt, ANALYST_SYSTEM_PROMPT)
            data = self.parse_json_response(response)
            return data.get("queries", [])
        except Exception:
            return gaps[:5]  # Use gap descriptions as fallback queries
