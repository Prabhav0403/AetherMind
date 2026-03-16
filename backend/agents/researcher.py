"""
Researcher Agent: Performs semantic vector search with query expansion and
multi-hop retrieval to gather evidence for each subtask.
"""
from typing import List, Optional
from agents.base_agent import BaseAgent
from config import settings
from models.schemas import (
    AgentType, AgentStatus, ResearchSession,
    ResearchSubtask, Evidence, ResearchPlan
)


RESEARCHER_SYSTEM_PROMPT = """You are a specialized research evidence retrieval AI.
Your role is to extract the most relevant, accurate, and comprehensive evidence 
from retrieved document chunks to answer specific research questions.

You focus on:
- Identifying key facts, statistics, and insights from document chunks
- Extracting exact relevant passages with proper attribution
- Performing query expansion to maximize recall
- Scoring evidence by relevance and informativeness

Always respond with valid JSON matching the requested schema exactly."""


class ResearcherAgent(BaseAgent):
    """Retrieves and extracts evidence from the vector knowledge base."""

    def __init__(self, vector_store=None):
        super().__init__(AgentType.RESEARCHER, settings.RESEARCHER_MODEL)
        self.vector_store = vector_store

    def set_vector_store(self, vector_store):
        self.vector_store = vector_store

    async def run(self, session: ResearchSession, **kwargs) -> List[Evidence]:
        """Execute retrieval for all pending subtasks."""
        if not session.plan:
            raise ValueError("No research plan found. Run PlannerAgent first.")

        subtasks = kwargs.get("subtasks", session.plan.subtasks)
        all_evidence: List[Evidence] = []

        self.log(session, AgentStatus.RUNNING,
                 f"Starting evidence retrieval for {len(subtasks)} subtasks")

        for subtask in subtasks:
            evidence = await self._retrieve_for_subtask(session, subtask)
            all_evidence.extend(evidence)
            subtask.evidence_count = len(evidence)
            subtask.completed = True

        # Deduplicate evidence
        seen = set()
        unique_evidence = []
        for e in all_evidence:
            key = e.source_chunk_id
            if key not in seen:
                seen.add(key)
                unique_evidence.append(e)

        session.evidence_collected.extend(unique_evidence)

        self.log(session, AgentStatus.COMPLETED,
                 f"Retrieved {len(unique_evidence)} unique evidence pieces",
                 {"total_raw": len(all_evidence),
                  "after_dedup": len(unique_evidence)})

        return unique_evidence

    async def _retrieve_for_subtask(self, session: ResearchSession,
                                     subtask: ResearchSubtask) -> List[Evidence]:
        """Retrieve evidence for a single subtask using all its search queries."""
        all_chunks = []

        # Expand queries before retrieval
        expanded_queries = await self._expand_queries(
            subtask.search_queries, session.query
        )

        for query in expanded_queries:
            if not self.vector_store:
                continue
            chunks = await self.vector_store.similarity_search(
                query,
                k=settings.TOP_K_RETRIEVAL,
                filter_doc_ids=getattr(session, 'use_documents', None)
            )
            all_chunks.extend(chunks)

        if not all_chunks:
            self.log(session, AgentStatus.WAITING,
                     f"No documents found for subtask: {subtask.title}")
            return []

        # Score and rank evidence
        evidence_list = await self._score_and_extract(
            all_chunks, subtask, session.query
        )

        # Keep top-k by relevance
        evidence_list.sort(key=lambda e: e.relevance_score, reverse=True)
        return evidence_list[:settings.RERANK_TOP_K * 2]

    async def _expand_queries(self, original_queries: List[str],
                               main_query: str) -> List[str]:
        """Expand queries to improve recall via LLM-based reformulation."""
        if not original_queries:
            return [main_query]

        prompt = f"""Given these search queries for researching "{main_query}":

{chr(10).join(f"- {q}" for q in original_queries)}

Generate 2-3 alternative phrasings for each query to improve search recall.
Include synonyms, related terms, and different angles on the same topic.

Respond with ONLY valid JSON:
{{
  "expanded_queries": ["query1", "query2", "query3", "query4", "query5"]
}}

Limit to maximum 8 total queries."""

        try:
            response = await self.invoke_llm(prompt, RESEARCHER_SYSTEM_PROMPT)
            data = self.parse_json_response(response)
            expanded = data.get("expanded_queries", original_queries)
            # Combine original + expanded, limit total
            all_queries = list(set(original_queries + expanded))
            return all_queries[:8]
        except Exception as e:
            self.logger.warning(f"Query expansion failed: {e}, using originals")
            return original_queries

    async def _score_and_extract(self, chunks: list, subtask: ResearchSubtask,
                                   main_query: str) -> List[Evidence]:
        """Score chunks and extract structured evidence."""
        if not chunks:
            return []

        # Format chunks for LLM scoring
        chunk_text = "\n\n".join([
            f"[CHUNK {i+1}] Source: {c.get('source', 'Unknown')} | "
            f"Score: {c.get('score', 0):.3f}\n{c.get('content', '')}"
            for i, c in enumerate(chunks[:15])  # Limit to 15 for context
        ])

        prompt = f"""Research task: "{subtask.title}"
Description: {subtask.description}
Main query: "{main_query}"

Retrieved document chunks:
{chunk_text}

Extract the most relevant evidence pieces. For each chunk that contains useful information:
1. Assess its relevance (0.0 - 1.0) to the subtask
2. Extract the key factual content

Respond with ONLY valid JSON:
{{
  "evidence": [
    {{
      "chunk_index": 1,
      "relevance_score": 0.9,
      "key_content": "The extracted/paraphrased key information from this chunk"
    }}
  ]
}}

Only include chunks with relevance_score >= 0.4. Maximum 10 evidence items."""

        try:
            response = await self.invoke_llm(prompt, RESEARCHER_SYSTEM_PROMPT)
            data = self.parse_json_response(response)

            evidence_list = []
            for item in data.get("evidence", []):
                idx = item.get("chunk_index", 1) - 1
                if 0 <= idx < len(chunks):
                    chunk = chunks[idx]
                    evidence_list.append(Evidence(
                        content=item.get("key_content", chunk.get("content", "")),
                        source_doc=chunk.get("source", "Unknown"),
                        source_chunk_id=chunk.get("chunk_id", f"chunk_{idx}"),
                        relevance_score=float(item.get("relevance_score", 0.5)),
                        subtask_id=subtask.task_id,
                        page_number=chunk.get("page_number"),
                        metadata=chunk.get("metadata", {}),
                    ))
            return evidence_list

        except Exception as e:
            self.logger.warning(f"Evidence extraction LLM call failed: {e}")
            # Fallback: convert chunks directly
            return [
                Evidence(
                    content=c.get("content", "")[:1000],
                    source_doc=c.get("source", "Unknown"),
                    source_chunk_id=c.get("chunk_id", f"chunk_{i}"),
                    relevance_score=float(c.get("score", 0.5)),
                    subtask_id=subtask.task_id,
                    page_number=c.get("page_number"),
                )
                for i, c in enumerate(chunks[:10])
                if c.get("score", 0) >= settings.MIN_RELEVANCE_SCORE
            ]
