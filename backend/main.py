"""
FastAPI application — main entry point for the Agentic RAG Research Assistant.
"""
import asyncio
import os
import logging
import uuid
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from sse_starlette.sse import EventSourceResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

from config import settings
from models.schemas import (
    ResearchRequest, ResearchResponse, SessionStatusResponse,
    DocumentUploadResponse, DocumentInfo, EvaluationMetrics,
    ResearchStatus, ResearchReport
)
from core.vector_store import VectorStore
from core.document_processor import DocumentProcessor
from core.orchestrator import ResearchOrchestrator

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger("main")

# ── App Initialization ─────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Autonomous Multi-Agent Framework Using Agentic RAG for "
                "Iterative Knowledge Synthesis and Report Generation",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Dependency Injection ───────────────────────────────────────────────────────
vector_store: Optional[VectorStore] = None
doc_processor: Optional[DocumentProcessor] = None
orchestrator: Optional[ResearchOrchestrator] = None


@app.on_event("startup")
async def startup_event():
    global vector_store, doc_processor, orchestrator
    logger.info("Initializing Agentic RAG system...")

    vector_store = VectorStore()
    doc_processor = DocumentProcessor(vector_store)
    orchestrator = ResearchOrchestrator(vector_store)

    logger.info(
        f"System ready. Vector DB: {settings.VECTOR_DB}, "
        f"LLM: {settings.LLM_PROVIDER}, "
        f"Embeddings: {settings.EMBEDDING_PROVIDER}"
    )


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "vector_db": settings.VECTOR_DB,
        "llm_provider": settings.LLM_PROVIDER,
        "indexed_chunks": vector_store.get_document_count() if vector_store else 0,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── Document Ingestion ─────────────────────────────────────────────────────────

@app.post("/api/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """Upload and asynchronously index a document."""
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. "
                   f"Allowed: {settings.ALLOWED_EXTENSIONS}"
        )

    # Check file size
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.MAX_FILE_SIZE_MB}MB limit"
        )

    # Save file
    doc_id = str(uuid.uuid4())
    save_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}{ext}")
    with open(save_path, "wb") as f:
        f.write(content)

    # Process asynchronously
    background_tasks.add_task(
        doc_processor.process_file, save_path, file.filename, doc_id
    )

    return DocumentUploadResponse(
        doc_id=doc_id,
        filename=file.filename,
        status="pending",
        message="Document uploaded. Indexing in progress..."
    )


@app.get("/api/documents", response_model=List[DocumentInfo])
async def list_documents():
    """List all indexed documents."""
    return doc_processor.list_documents()


@app.get("/api/documents/{doc_id}", response_model=DocumentInfo)
async def get_document(doc_id: str):
    doc = doc_processor.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    deleted_count = await vector_store.delete_document(doc_id)
    doc = doc_processor.get_document(doc_id)
    if doc:
        doc.status = "deleted"
    return {"deleted_chunks": deleted_count, "doc_id": doc_id}


# ── Research ───────────────────────────────────────────────────────────────────

@app.post("/api/research/start", response_model=ResearchResponse)
async def start_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
):
    """Start an asynchronous research session."""
    session = orchestrator.create_session(request)
    background_tasks.add_task(orchestrator.run_research, session)

    return ResearchResponse(
        research_id=session.research_id,
        status=ResearchStatus.PENDING,
        message="Research started. Use /api/research/{id}/status to poll progress, "
                "or /api/research/{id}/stream for SSE updates."
    )


@app.get("/api/research/{research_id}/status",
         response_model=SessionStatusResponse)
async def get_research_status(research_id: str):
    """Poll research session status."""
    session = orchestrator.get_session(research_id)
    if not session:
        raise HTTPException(status_code=404, detail="Research session not found")

    return SessionStatusResponse(
        research_id=session.research_id,
        status=session.status,
        current_iteration=session.current_iteration,
        max_iterations=session.max_iterations,
        coverage_score=(
            session.analysis_history[-1].coverage_score
            if session.analysis_history else None
        ),
        activity_log=session.activity_log[-20:],  # Last 20 events
        report=session.report,
        error=session.error,
    )


@app.get("/api/research/{research_id}/stream")
async def stream_research_progress(research_id: str):
    """Server-Sent Events stream for real-time agent activity."""
    session = orchestrator.get_session(research_id)
    if not session:
        raise HTTPException(status_code=404, detail="Research session not found")

    return EventSourceResponse(
        orchestrator.stream_progress(session)
    )


@app.get("/api/research/{research_id}/report",
         response_model=ResearchReport)
async def get_research_report(research_id: str):
    """Retrieve the generated research report."""
    session = orchestrator.get_session(research_id)
    if not session:
        raise HTTPException(status_code=404, detail="Research session not found")
    if not session.report:
        raise HTTPException(
            status_code=404,
            detail="Report not ready. Check status endpoint."
        )
    return session.report

""""
@app.get("/api/research/{research_id}/report/markdown")
async def export_report_markdown(research_id: str):
    
    session = orchestrator.get_session(research_id)
    if not session or not session.report:
        raise HTTPException(status_code=404, detail="Report not available")

    report = session.report
    lines = [f"# {report.title}\n"]
    lines.append(f"*Generated: {report.generated_at.isoformat()}*\n")
    lines.append(f"*Quality Score: {report.quality_score:.2f}*\n\n")

    for section in report.sections:
        lines.append(f"## {section.title}\n\n{section.content}\n\n")

    if report.citations:
        lines.append("## References\n\n")
        for c in report.citations:
            page = f", p. {c.page}" if c.page else ""
            lines.append(f"[{c.number}] {c.source}{page}\n")

    content = "\n".join(lines)

    # Save and return
    md_path = os.path.join(settings.REPORTS_DIR, f"{research_id}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)

    return FileResponse(
        md_path,
        media_type="text/markdown",
        filename=f"research_report_{research_id[:8]}.md"
    )"""

@app.get("/api/research/{research_id}/report/pdf")
async def export_report_pdf(research_id: str):
    """Export the report as a PDF file."""
    session = orchestrator.get_session(research_id)

    if not session or not session.report:
        raise HTTPException(status_code=404, detail="Report not available")

    report = session.report

    pdf_path = os.path.join(settings.REPORTS_DIR, f"{research_id}.pdf")

    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph(report.title, styles["Title"]))
    elements.append(Spacer(1, 12))

    # Metadata
    elements.append(
        Paragraph(f"Generated: {report.generated_at.isoformat()}", styles["Normal"])
    )
    elements.append(
        Paragraph(f"Quality Score: {report.quality_score:.2f}", styles["Normal"])
    )
    elements.append(Spacer(1, 20))

    # Sections
    for section in report.sections:
        elements.append(Paragraph(section.title, styles["Heading2"]))
        elements.append(Spacer(1, 10))

        for paragraph in section.content.split("\n"):
            if paragraph.strip():
                elements.append(Paragraph(paragraph, styles["BodyText"]))
                elements.append(Spacer(1, 6))

        elements.append(Spacer(1, 12))

    # References
    if report.citations:
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("References", styles["Heading2"]))
        elements.append(Spacer(1, 10))

        for c in report.citations:
            page = f", p. {c.page}" if c.page else ""
            elements.append(
                Paragraph(f"[{c.number}] {c.source}{page}", styles["BodyText"])
            )

    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    doc.build(elements)

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"research_report_{research_id[:8]}.pdf",
    )

@app.get("/api/research/{research_id}/evaluate",
         response_model=EvaluationMetrics)
async def evaluate_research(research_id: str):
    """Compute evaluation metrics for a completed research session."""
    session = orchestrator.get_session(research_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != ResearchStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Research not completed. Status: {session.status}"
        )
    return orchestrator.compute_evaluation_metrics(session)


@app.get("/api/research")
async def list_research_sessions():
    """List all research sessions."""
    sessions = []
    for session in orchestrator.sessions.values():
        sessions.append({
            "research_id": session.research_id,
            "query": session.query[:100],
            "status": session.status.value,
            "current_iteration": session.current_iteration,
            "evidence_count": len(session.evidence_collected),
            "has_report": session.report is not None,
            "created_at": session.created_at.isoformat(),
        })
    return sorted(sessions, key=lambda x: x["created_at"], reverse=True)


# ── System ─────────────────────────────────────────────────────────────────────

@app.get("/api/system/stats")
async def system_stats():
    """System statistics."""
    return {
        "total_documents": len(doc_processor.list_documents()),
        "indexed_chunks": vector_store.get_document_count(),
        "active_sessions": len(orchestrator.sessions),
        "vector_db": settings.VECTOR_DB,
        "embedding_model": settings.EMBEDDING_MODEL,
        "llm_provider": settings.LLM_PROVIDER,
        "chunk_size": settings.CHUNK_SIZE,
        "chunk_overlap": settings.CHUNK_OVERLAP,
        "max_iterations": settings.MAX_ITERATIONS,
        "coverage_threshold": settings.COVERAGE_THRESHOLD,
    }


# ── Run ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
