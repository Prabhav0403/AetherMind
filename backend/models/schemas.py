"""
Pydantic schemas for request/response models.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import uuid


# ─── Enums ────────────────────────────────────────────────────────────────────

class AgentType(str, Enum):
    PLANNER = "planner"
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    WRITER = "writer"
    ORCHESTRATOR = "orchestrator"


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING = "waiting"


class ResearchStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RESEARCHING = "researching"
    ANALYZING = "analyzing"
    WRITING = "writing"
    REFINING = "refining"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


# ─── Document Models ───────────────────────────────────────────────────────────

class DocumentChunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_id: str
    content: str
    metadata: Dict[str, Any] = {}
    relevance_score: Optional[float] = None
    page_number: Optional[int] = None


class DocumentInfo(BaseModel):
    doc_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    file_type: str
    file_size: int
    status: DocumentStatus = DocumentStatus.PENDING
    chunk_count: int = 0
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    indexed_at: Optional[datetime] = None
    error: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    doc_id: str
    filename: str
    status: DocumentStatus
    message: str


# ─── Agent Models ──────────────────────────────────────────────────────────────

class ResearchSubtask(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    search_queries: List[str] = []
    priority: int = 1
    completed: bool = False
    evidence_count: int = 0


class ResearchPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_query: str
    objective: str
    scope: str
    subtasks: List[ResearchSubtask]
    report_structure: List[str]
    estimated_iterations: int = 3
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Evidence(BaseModel):
    evidence_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    source_doc: str
    source_chunk_id: str
    relevance_score: float
    subtask_id: Optional[str] = None
    page_number: Optional[int] = None
    metadata: Dict[str, Any] = {}


class AnalysisResult(BaseModel):
    coverage_score: float  # 0.0 - 1.0
    confidence_score: float  # 0.0 - 1.0
    gaps: List[str] = []
    contradictions: List[str] = []
    additional_queries: List[str] = []
    subtask_coverage: Dict[str, float] = {}
    critique: str
    sufficient: bool = False
    iteration: int = 1


class Citation(BaseModel):
    citation_id: str
    number: int
    source: str
    doc_id: str
    chunk_id: str
    page: Optional[int] = None
    relevance: float


class ReportSection(BaseModel):
    title: str
    content: str
    citations: List[str] = []


class ResearchReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    research_id: str
    title: str
    abstract: str
    sections: List[ReportSection]
    citations: List[Citation]
    metadata: Dict[str, Any] = {}
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    quality_score: float = 0.0
    iteration_count: int = 1
    total_evidence_used: int = 0


# ─── Orchestration Models ──────────────────────────────────────────────────────

class AgentActivityLog(BaseModel):
    log_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    research_id: str
    agent: AgentType
    status: AgentStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    iteration: int = 1


class ResearchSession(BaseModel):
    research_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str
    status: ResearchStatus = ResearchStatus.PENDING
    current_iteration: int = 0
    max_iterations: int = 5
    plan: Optional[ResearchPlan] = None
    evidence_collected: List[Evidence] = []
    analysis_history: List[AnalysisResult] = []
    report: Optional[ResearchReport] = None
    activity_log: List[AgentActivityLog] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    def add_log(self, agent: AgentType, status: AgentStatus, message: str,
                details: Optional[Dict[str, Any]] = None):
        self.activity_log.append(AgentActivityLog(
            research_id=self.research_id,
            agent=agent,
            status=status,
            message=message,
            details=details,
            iteration=self.current_iteration
        ))


# ─── API Request/Response Models ──────────────────────────────────────────────

class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=10, max_length=2000,
                       description="Research question or topic")
    max_iterations: int = Field(default=3, ge=1, le=10)
    target_coverage: float = Field(default=0.75, ge=0.1, le=1.0)
    report_style: str = Field(default="academic",
                              description="academic | business | technical")
    use_documents: Optional[List[str]] = Field(
        default=None, description="Specific document IDs to use, None = all")


class ResearchResponse(BaseModel):
    research_id: str
    status: ResearchStatus
    message: str


class SessionStatusResponse(BaseModel):
    research_id: str
    status: ResearchStatus
    current_iteration: int
    max_iterations: int
    coverage_score: Optional[float] = None
    activity_log: List[AgentActivityLog]
    report: Optional[ResearchReport] = None
    error: Optional[str] = None


class EvaluationMetrics(BaseModel):
    research_id: str
    factual_accuracy: float
    coverage_score: float
    citation_correctness: float
    hallucination_rate: float
    response_completeness: float
    overall_score: float
    iterations_used: int
    evidence_pieces: int
    report_length_words: int
