"""
Writer Agent: Synthesizes validated evidence into a structured, well-cited
research report with academic formatting.
"""
from typing import List, Dict
import re
from agents.base_agent import BaseAgent
from config import settings
from models.schemas import (
    AgentType, AgentStatus, ResearchSession,
    Evidence, ResearchReport, ReportSection, Citation
)


WRITER_SYSTEM_PROMPT = """You are an expert academic research writer and synthesizer.
Your role is to produce structured, coherent, well-cited research reports from 
evidence collected by research agents.

Your writing is:
- Clear, precise, and academically rigorous
- Well-organized with logical narrative flow
- Properly cited with inline references [1], [2], etc.
- Free of speculation — every claim is grounded in the evidence provided
- Comprehensive yet concise

Always respond with valid JSON matching the requested schema exactly."""


class WriterAgent(BaseAgent):
    """Synthesizes research evidence into structured reports."""

    def __init__(self):
        super().__init__(AgentType.WRITER, settings.WRITER_MODEL)

    async def run(self, session: ResearchSession, **kwargs) -> ResearchReport:
        """Generate the full research report."""
        self.log(session, AgentStatus.RUNNING,
                 f"Synthesizing report from {len(session.evidence_collected)} "
                 f"evidence pieces across {len(session.plan.subtasks)} subtasks")

        # Build citation registry
        citations = self._build_citation_registry(session.evidence_collected)

        # Generate each report section
        sections = await self._generate_sections(session, citations)

        # Compute quality score
        quality = self._compute_quality_score(session, sections, citations)

        report = ResearchReport(
            research_id=session.research_id,
            title=await self._generate_title(session.query),
            abstract=sections[0].content if sections else "",
            sections=sections,
            citations=citations,
            quality_score=quality,
            iteration_count=session.current_iteration,
            total_evidence_used=len(session.evidence_collected),
            metadata={
                "query": session.query,
                "subtask_count": len(session.plan.subtasks),
                "report_style": kwargs.get("report_style", "academic"),
            }
        )

        session.report = report

        self.log(session, AgentStatus.COMPLETED,
                 f"Report generated: {len(sections)} sections, "
                 f"{len(citations)} citations, quality={quality:.2f}",
                 {"quality": quality, "sections": [s.title for s in sections],
                  "citations": len(citations)})

        return report

    async def _generate_title(self, query: str) -> str:
        """Generate a formal report title from the query."""
        prompt = f"""Generate a formal, academic-style research report title for this query:
"{query}"

The title should be specific, informative, and professional.
Respond with ONLY the title text, no quotes or extra text."""
        try:
            return (await self.invoke_llm(prompt)).strip().strip('"\'')
        except Exception:
            return f"Research Report: {query[:80]}"

    async def _generate_sections(self, session: ResearchSession,
                                   citations: List[Citation]) -> List[ReportSection]:
        """Generate all report sections based on the plan structure."""
        sections = []
        plan = session.plan
        evidence = session.evidence_collected

        # Build citation lookup for inline use
        citation_map = {c.citation_id: f"[{c.number}]" for c in citations}
        source_to_num = {c.source: c.number for c in citations}

        # Format evidence grouped by subtask
        evidence_text = self._format_evidence_for_writing(evidence, citations)

        last_analysis = (session.analysis_history[-1]
                         if session.analysis_history else None)

        for section_title in plan.report_structure:
            section = await self._generate_section(
                section_title=section_title,
                query=session.query,
                objective=plan.objective,
                scope=plan.scope,
                subtasks=plan.subtasks,
                evidence_text=evidence_text,
                analysis_critique=last_analysis.critique if last_analysis else "",
                all_sections_so_far=[s.title for s in sections],
                citations=citations,
                report_style=session.research_id  # pass through style
            )
            sections.append(section)

        return sections

    async def _generate_section(self, section_title: str, query: str,
                                  objective: str, scope: str,
                                  subtasks, evidence_text: str,
                                  analysis_critique: str,
                                  all_sections_so_far: List[str],
                                  citations: List[Citation],
                                  report_style: str = "academic") -> ReportSection:
        """Generate a single report section."""

        subtask_titles = ", ".join(t.title for t in subtasks)
        citation_list = "\n".join(
            f"[{c.number}] {c.source}" for c in citations
        )

        prompt = f"""Write the "{section_title}" section of a research report.

RESEARCH QUERY: {query}
OBJECTIVE: {objective}
SCOPE: {scope}
COVERED SUBTASKS: {subtask_titles}

EVIDENCE BASE:
{evidence_text[:6000]}

AVAILABLE CITATIONS:
{citation_list}

ANALYST CRITIQUE: {analysis_critique}

SECTIONS ALREADY WRITTEN: {', '.join(all_sections_so_far) or 'None (this is first)'}

Write a comprehensive, well-structured "{section_title}" section.
Requirements:
- Use inline citations in format [1], [2], etc. whenever referencing specific information
- For "Abstract": 200-250 word overview of the entire report
- For "References": List ALL cited sources in numbered format
- For other sections: 300-600 words with clear paragraph structure
- Do NOT use markdown headers inside the content (the section title is handled separately)
- Ground every factual claim in the evidence provided
- If information is insufficient for a section, note this honestly

Respond with ONLY valid JSON:
{{
  "content": "Full section content with inline citations like [1], [2]",
  "citations_used": [1, 2, 3]
}}"""

        try:
            response = await self.invoke_llm(prompt, WRITER_SYSTEM_PROMPT)
            data = self.parse_json_response(response)
            content = data.get("content", "")
            citations_used = [str(n) for n in data.get("citations_used", [])]
        except Exception as e:
            self.logger.warning(f"Section generation failed for {section_title}: {e}")
            content = f"This section could not be generated due to insufficient evidence. Additional research may be needed."
            citations_used = []

        return ReportSection(
            title=section_title,
            content=content,
            citations=citations_used,
        )

    def _build_citation_registry(self, evidence: List[Evidence]) -> List[Citation]:
        """Build a deduplicated citation registry from all evidence."""
        seen_sources: Dict[str, Citation] = {}
        citation_number = 1

        for e in evidence:
            source_key = e.source_doc
            if source_key not in seen_sources:
                seen_sources[source_key] = Citation(
                    citation_id=e.evidence_id,
                    number=citation_number,
                    source=e.source_doc,
                    doc_id=e.metadata.get("doc_id", ""),
                    chunk_id=e.source_chunk_id,
                    page=e.page_number,
                    relevance=e.relevance_score,
                )
                citation_number += 1

        return list(seen_sources.values())

    def _format_evidence_for_writing(self, evidence: List[Evidence],
                                      citations: List[Citation]) -> str:
        """Format evidence with citation numbers for the writer."""
        source_to_num = {c.source: c.number for c in citations}
        lines = []

        for e in evidence:
            num = source_to_num.get(e.source_doc, "?")
            lines.append(
                f"[Source {num}: {e.source_doc}] "
                f"(relevance: {e.relevance_score:.2f})\n"
                f"{e.content}"
            )

        return "\n\n---\n\n".join(lines)

    def _compute_quality_score(self, session: ResearchSession,
                                sections: List[ReportSection],
                                citations: List[Citation]) -> float:
        """Compute overall report quality score."""
        scores = []

        # Coverage from last analysis
        if session.analysis_history:
            last = session.analysis_history[-1]
            scores.append(last.coverage_score * 0.4)
            scores.append(last.confidence_score * 0.2)
        else:
            scores.append(0.5 * 0.4)
            scores.append(0.5 * 0.2)

        # Section completeness
        expected_sections = len(session.plan.report_structure)
        actual_sections = len(sections)
        section_score = min(actual_sections / max(expected_sections, 1), 1.0)
        scores.append(section_score * 0.2)

        # Citation density
        total_content_words = sum(
            len(s.content.split()) for s in sections
        )
        citation_density = min(len(citations) / max(total_content_words / 100, 1), 1.0)
        scores.append(citation_density * 0.2)

        return round(sum(scores), 3)
