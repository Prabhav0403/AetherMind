"""
Standalone evaluation script — runs a full research cycle and reports metrics.
Usage:
    python evaluate.py --query "Your research question" --docs path/to/docs/
"""
import asyncio
import argparse
import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from config import settings
from core.vector_store import VectorStore
from core.document_processor import DocumentProcessor
from core.orchestrator import ResearchOrchestrator
from models.schemas import ResearchRequest


async def run_evaluation(
    query: str,
    docs_dir: str | None = None,
    max_iterations: int = 3,
    output_file: str | None = None,
):
    print(f"\n{'='*60}")
    print(f"AGENTIC RAG EVALUATION")
    print(f"{'='*60}")
    print(f"Query: {query}")
    print(f"Max iterations: {max_iterations}")
    print(f"LLM Provider: {settings.LLM_PROVIDER}")
    print(f"Vector DB: {settings.VECTOR_DB}")
    print(f"{'='*60}\n")

    # Initialize system
    print("⚙  Initializing vector store and agents...")
    vector_store = VectorStore()
    doc_processor = DocumentProcessor(vector_store)
    orchestrator = ResearchOrchestrator(vector_store)

    # Ingest documents if provided
    if docs_dir:
        doc_path = Path(docs_dir)
        if doc_path.exists():
            print(f"📚 Ingesting documents from {docs_dir}...")
            files = list(doc_path.glob("**/*"))
            supported = [f for f in files if f.suffix.lower() in
                        settings.ALLOWED_EXTENSIONS and f.is_file()]

            print(f"   Found {len(supported)} supported files")
            for i, f in enumerate(supported, 1):
                print(f"   [{i}/{len(supported)}] {f.name}")
                await doc_processor.process_file(str(f), f.name)

            indexed = sum(
                1 for d in doc_processor.list_documents()
                if d.status == "indexed"
            )
            total_chunks = vector_store.get_document_count()
            print(f"   ✓ {indexed} documents indexed, {total_chunks} total chunks\n")

    # Run research
    print("🚀 Starting research pipeline...\n")
    request = ResearchRequest(
        query=query,
        max_iterations=max_iterations,
        target_coverage=settings.COVERAGE_THRESHOLD,
        report_style="academic",
    )
    session = orchestrator.create_session(request)
    await orchestrator.run_research(session)

    # Results
    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}")
    print(f"Status:          {session.status.value}")
    print(f"Iterations used: {session.current_iteration}/{max_iterations}")
    print(f"Evidence pieces: {len(session.evidence_collected)}")

    if session.analysis_history:
        last = session.analysis_history[-1]
        print(f"Coverage score:  {last.coverage_score:.2%}")
        print(f"Confidence:      {last.confidence_score:.2%}")
        if last.gaps:
            print(f"Remaining gaps:  {len(last.gaps)}")

    if session.report:
        report = session.report
        print(f"\nReport title:    {report.title}")
        print(f"Sections:        {len(report.sections)}")
        print(f"Citations:       {len(report.citations)}")
        print(f"Quality score:   {report.quality_score:.2%}")
        print(f"Word count:      ~{sum(len(s.content.split()) for s in report.sections)}")

        # Compute evaluation metrics
        metrics = orchestrator.compute_evaluation_metrics(session)
        print(f"\n--- Evaluation Metrics ---")
        print(f"Overall score:       {metrics.overall_score:.2%}")
        print(f"Factual accuracy:    {metrics.factual_accuracy:.2%}")
        print(f"Coverage score:      {metrics.coverage_score:.2%}")
        print(f"Citation correctness:{metrics.citation_correctness:.2%}")
        print(f"Hallucination rate:  {metrics.hallucination_rate:.2%}")
        print(f"Completeness:        {metrics.response_completeness:.2%}")

        # Save outputs
        if output_file:
            out = {
                "research_id": session.research_id,
                "query": query,
                "status": session.status.value,
                "metrics": {
                    "overall_score": metrics.overall_score,
                    "coverage_score": metrics.coverage_score,
                    "factual_accuracy": metrics.factual_accuracy,
                    "citation_correctness": metrics.citation_correctness,
                    "hallucination_rate": metrics.hallucination_rate,
                    "response_completeness": metrics.response_completeness,
                    "iterations_used": metrics.iterations_used,
                    "evidence_pieces": metrics.evidence_pieces,
                    "report_length_words": metrics.report_length_words,
                },
                "report": {
                    "title": report.title,
                    "sections": [
                        {"title": s.title, "content": s.content}
                        for s in report.sections
                    ],
                    "citations": [
                        {"number": c.number, "source": c.source, "page": c.page}
                        for c in report.citations
                    ],
                },
            }
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=2, default=str)
            print(f"\n✓ Full report saved to: {output_file}")

    elif session.error:
        print(f"\n⚠  Research failed: {session.error}")

    print(f"\n{'='*60}\n")
    return session


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate the Agentic RAG system on a research query"
    )
    parser.add_argument(
        "--query", "-q",
        required=True,
        help="Research question to investigate"
    )
    parser.add_argument(
        "--docs", "-d",
        default=None,
        help="Path to directory with documents to index"
    )
    parser.add_argument(
        "--iterations", "-i",
        type=int,
        default=3,
        help="Maximum research iterations (default: 3)"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Save results to JSON file"
    )
    args = parser.parse_args()

    asyncio.run(run_evaluation(
        query=args.query,
        docs_dir=args.docs,
        max_iterations=args.iterations,
        output_file=args.output,
    ))


if __name__ == "__main__":
    main()
