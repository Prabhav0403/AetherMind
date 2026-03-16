"""
Research Orchestrator: Coordinates all agents in the iterative refinement loop.
Manages session state and implements stopping criteria.
"""

import asyncio
import logging
from typing import Dict, Optional, AsyncGenerator
from datetime import datetime
import json

from config import settings
from models.schemas import (
    ResearchSession,
    ResearchStatus,
    AgentType,
    AgentStatus,
    ResearchRequest,
    EvaluationMetrics
)

from agents.planner import PlannerAgent
from agents.researcher import ResearcherAgent
from agents.analyst import AnalystAgent
from agents.writer import WriterAgent
from core.vector_store import VectorStore

logger = logging.getLogger(__name__)


class ResearchOrchestrator:

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

        self.planner = PlannerAgent()
        self.researcher = ResearcherAgent(vector_store)
        self.analyst = AnalystAgent()
        self.writer = WriterAgent()

        self.sessions: Dict[str, ResearchSession] = {}

    # ─────────────────────────────────────────────

    def create_session(self, request: ResearchRequest) -> ResearchSession:
        """Create new research session."""
        session = ResearchSession(
            query=request.query,
            max_iterations=request.max_iterations
        )

        self.sessions[session.research_id] = session
        return session

    # ─────────────────────────────────────────────

    def get_session(self, research_id: str) -> Optional[ResearchSession]:
        return self.sessions.get(research_id)

    # ─────────────────────────────────────────────
    # Retry helper for LLM rate limits
    # ─────────────────────────────────────────────

    async def _run_with_retry(self, coro, retries=3, delay=5):

        for attempt in range(retries):

            try:
                return await coro

            except Exception as e:

                if "429" in str(e) and attempt < retries - 1:

                    wait = delay * (attempt + 1)

                    logger.warning(
                        f"Rate limit hit. Retrying in {wait}s..."
                    )

                    await asyncio.sleep(wait)

                else:
                    raise

    # ─────────────────────────────────────────────
    # Main pipeline
    # ─────────────────────────────────────────────

    async def run_research(self, session: ResearchSession) -> ResearchSession:

        session.status = ResearchStatus.PLANNING

        try:

            logger.info(
                f"[{session.research_id[:8]}] Starting research: {session.query}"
            )

            # ───────────────── Planning Phase ─────────────────

            await self._run_with_retry(
                self.planner.run(session)
            )

            session.status = ResearchStatus.RESEARCHING

            # ───────────────── Iterative Loop ─────────────────

            for iteration in range(1, session.max_iterations + 1):

                session.current_iteration = iteration

                logger.info(
                    f"[{session.research_id[:8]}] Iteration "
                    f"{iteration}/{session.max_iterations}"
                )

                if iteration == 1:
                    target_subtasks = session.plan.subtasks
                else:
                    target_subtasks = [
                        t for t in session.plan.subtasks
                        if not t.completed
                    ]

                # ───── Researcher

                if target_subtasks:

                    await self._run_with_retry(
                        self.researcher.run(
                            session,
                            subtasks=target_subtasks
                        )
                    )

                logger.info(
                    f"[{session.research_id[:8]}] Evidence collected: "
                    f"{len(session.evidence_collected)}"
                )

                if not session.evidence_collected:

                    logger.warning(
                        f"[{session.research_id[:8]}] "
                        "No evidence retrieved. Stopping early."
                    )

                    break

                # ───── Analyst

                session.status = ResearchStatus.ANALYZING

                analysis = await self._run_with_retry(
                    self.analyst.run(session)
                )

                logger.info(
                    f"[{session.research_id[:8]}] "
                    f"coverage={analysis.coverage_score:.2f} "
                    f"confidence={analysis.confidence_score:.2f}"
                )

                # ───── Stop conditions

                if self._should_stop(session, analysis):

                    logger.info(
                        f"[{session.research_id[:8]}] "
                        "Stopping research loop"
                    )

                    break

                # ───── Refinement

                if (
                    iteration < session.max_iterations
                    and analysis.gaps
                ):

                    session.status = ResearchStatus.REFINING

                    session.add_log(
                        AgentType.ORCHESTRATOR,
                        AgentStatus.RUNNING,
                        f"Coverage {analysis.coverage_score:.2f} below "
                        f"threshold. Refining with {len(analysis.gaps)} gaps.",
                        {"gaps": analysis.gaps}
                    )

                    await self._run_with_retry(
                        self.planner.refine_plan(
                            session,
                            analysis.gaps
                        )
                    )

            # ───────────────── Writing Phase ─────────────────

            session.status = ResearchStatus.WRITING

            await self._run_with_retry(
                self.writer.run(session)
            )

            session.status = ResearchStatus.COMPLETED

            session.completed_at = datetime.utcnow()

            logger.info(
                f"[{session.research_id[:8]}] "
                f"Research complete. Quality={session.report.quality_score:.2f}"
            )

        except Exception as e:

            logger.error(
                f"[{session.research_id[:8]}] Research failed: {e}",
                exc_info=True
            )

            session.status = ResearchStatus.FAILED
            session.error = str(e)

            session.add_log(
                AgentType.ORCHESTRATOR,
                AgentStatus.FAILED,
                f"Research pipeline failed: {str(e)}"
            )

        return session

    # ─────────────────────────────────────────────
    # Stop conditions
    # ─────────────────────────────────────────────

    def _should_stop(self, session: ResearchSession, analysis):

        if session.current_iteration >= session.max_iterations:
            return True

        if (
            analysis.coverage_score >= settings.COVERAGE_THRESHOLD
            and analysis.confidence_score
            >= settings.ANALYST_CONFIDENCE_THRESHOLD
        ):
            return True

        if not session.evidence_collected:
            return True

        return False

    # ─────────────────────────────────────────────
    # SSE Streaming
    # ─────────────────────────────────────────────

    async def stream_progress(
        self,
        session: ResearchSession
    ) -> AsyncGenerator[str, None]:

        last_log_index = 0

        while session.status not in [
            ResearchStatus.COMPLETED,
            ResearchStatus.FAILED
        ]:

            new_logs = session.activity_log[last_log_index:]

            for log in new_logs:

                event_data = {
                    "type": "agent_activity",
                    "data": {
                        "agent": log.agent.value,
                        "status": log.status.value,
                        "message": log.message,
                        "iteration": log.iteration,
                        "timestamp": log.timestamp.isoformat(),
                        "details": log.details
                    }
                }

                yield f"data: {json.dumps(event_data)}\n\n"

            last_log_index += len(new_logs)

            status_event = {
                "type": "status_update",
                "data": {
                    "research_id": session.research_id,
                    "status": session.status.value,
                    "iteration": session.current_iteration,
                    "coverage": (
                        session.analysis_history[-1].coverage_score
                        if session.analysis_history else 0
                    ),
                    "evidence_count": len(session.evidence_collected)
                }
            }

            yield f"data: {json.dumps(status_event)}\n\n"

            await asyncio.sleep(1.5)

        completion_event = {
            "type": "complete",
            "data": {
                "research_id": session.research_id,
                "status": session.status.value,
                "has_report": session.report is not None,
                "quality_score": (
                    session.report.quality_score
                    if session.report else 0
                )
            }
        }

        yield f"data: {json.dumps(completion_event)}\n\n"

    # ─────────────────────────────────────────────
    # Evaluation
    # ─────────────────────────────────────────────

    def compute_evaluation_metrics(
        self,
        session: ResearchSession
    ) -> EvaluationMetrics:

        if not session.report:
            raise ValueError("No report available")

        analysis = (
            session.analysis_history[-1]
            if session.analysis_history else None
        )

        total_words = sum(
            len(s.content.split())
            for s in session.report.sections
        )

        cited_sections = sum(
            1 for s in session.report.sections
            if s.citations
        ) / max(len(session.report.sections), 1)

        hallucination_rate = 1.0 - (
            analysis.confidence_score if analysis else 0.5
        )

        coverage = analysis.coverage_score if analysis else 0.5

        overall = (
            coverage * 0.3 +
            (1 - hallucination_rate) * 0.3 +
            cited_sections * 0.2 +
            min(total_words / 2000, 1.0) * 0.2
        )

        return EvaluationMetrics(
            research_id=session.research_id,
            factual_accuracy=analysis.confidence_score if analysis else 0.5,
            coverage_score=coverage,
            citation_correctness=cited_sections,
            hallucination_rate=round(hallucination_rate, 3),
            response_completeness=min(total_words / 2000, 1.0),
            overall_score=round(overall, 3),
            iterations_used=session.current_iteration,
            evidence_pieces=len(session.evidence_collected),
            report_length_words=total_words
        )