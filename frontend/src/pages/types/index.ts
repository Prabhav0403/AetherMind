// ─── Enums ─────────────────────────────────────────────────────────────────────

export type AgentType = 'planner' | 'researcher' | 'analyst' | 'writer' | 'orchestrator';
export type AgentStatus = 'idle' | 'running' | 'completed' | 'failed' | 'waiting';
export type ResearchStatus =
  | 'pending' | 'planning' | 'researching'
  | 'analyzing' | 'writing' | 'refining'
  | 'completed' | 'failed';
export type DocumentStatus = 'pending' | 'processing' | 'indexed' | 'failed';

// ─── Document Types ─────────────────────────────────────────────────────────────

export interface DocumentInfo {
  doc_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: DocumentStatus;
  chunk_count: number;
  uploaded_at: string;
  indexed_at?: string;
  error?: string;
}

export interface DocumentUploadResponse {
  doc_id: string;
  filename: string;
  status: string;
  message: string;
}

// ─── Agent / Research Types ─────────────────────────────────────────────────────

export interface AgentActivityLog {
  log_id: string;
  research_id: string;
  agent: AgentType;
  status: AgentStatus;
  message: string;
  details?: Record<string, unknown>;
  timestamp: string;
  iteration: number;
}

export interface ResearchSubtask {
  task_id: string;
  title: string;
  description: string;
  search_queries: string[];
  priority: number;
  completed: boolean;
  evidence_count: number;
}

export interface ResearchPlan {
  plan_id: string;
  original_query: string;
  objective: string;
  scope: string;
  subtasks: ResearchSubtask[];
  report_structure: string[];
  estimated_iterations: number;
}

export interface AnalysisResult {
  coverage_score: number;
  confidence_score: number;
  gaps: string[];
  contradictions: string[];
  additional_queries: string[];
  subtask_coverage: Record<string, number>;
  critique: string;
  sufficient: boolean;
  iteration: number;
}

export interface Citation {
  citation_id: string;
  number: number;
  source: string;
  doc_id: string;
  chunk_id: string;
  page?: number;
  relevance: number;
}

export interface ReportSection {
  title: string;
  content: string;
  citations: string[];
}

export interface ResearchReport {
  report_id: string;
  research_id: string;
  title: string;
  abstract: string;
  sections: ReportSection[];
  citations: Citation[];
  metadata: Record<string, unknown>;
  generated_at: string;
  quality_score: number;
  iteration_count: number;
  total_evidence_used: number;
}

// ─── API Response Types ─────────────────────────────────────────────────────────

export interface ResearchRequest {
  query: string;
  max_iterations: number;
  target_coverage: number;
  report_style: string;
  use_documents?: string[];
}

export interface ResearchResponse {
  research_id: string;
  status: ResearchStatus;
  message: string;
}

export interface SessionStatusResponse {
  research_id: string;
  status: ResearchStatus;
  current_iteration: number;
  max_iterations: number;
  coverage_score?: number;
  activity_log: AgentActivityLog[];
  report?: ResearchReport;
  error?: string;
}

export interface EvaluationMetrics {
  research_id: string;
  factual_accuracy: number;
  coverage_score: number;
  citation_correctness: number;
  hallucination_rate: number;
  response_completeness: number;
  overall_score: number;
  iterations_used: number;
  evidence_pieces: number;
  report_length_words: number;
}

export interface SystemStats {
  total_documents: number;
  indexed_chunks: number;
  active_sessions: number;
  vector_db: string;
  embedding_model: string;
  llm_provider: string;
  chunk_size: number;
  chunk_overlap: number;
  max_iterations: number;
  coverage_threshold: number;
}

// ─── SSE Event Types ────────────────────────────────────────────────────────────

export type SSEEventType = 'agent_activity' | 'status_update' | 'complete';

export interface SSEEvent {
  type: SSEEventType;
  data: Record<string, unknown>;
}
