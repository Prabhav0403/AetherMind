import axios from 'axios';
import type {
  DocumentInfo, DocumentUploadResponse, ResearchRequest,
  ResearchResponse, SessionStatusResponse, ResearchReport,
  EvaluationMetrics, SystemStats,
} from '../pages/types';

const BASE_URL = '/api';

const api = axios.create({ baseURL: BASE_URL });

// ─── Documents ──────────────────────────────────────────────────────────────────

export const documentsApi = {
  upload: async (file: File): Promise<DocumentUploadResponse> => {
    const form = new FormData();
    form.append('file', file);
    const { data } = await api.post('/documents/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  list: async (): Promise<DocumentInfo[]> => {
    const { data } = await api.get('/documents');
    return data;
  },

  get: async (docId: string): Promise<DocumentInfo> => {
    const { data } = await api.get(`/documents/${docId}`);
    return data;
  },

  delete: async (docId: string): Promise<{ deleted_chunks: number }> => {
    const { data } = await api.delete(`/documents/${docId}`);
    return data;
  },
};

// ─── Research ───────────────────────────────────────────────────────────────────

export const researchApi = {
  start: async (request: ResearchRequest): Promise<ResearchResponse> => {
    const { data } = await api.post('/research/start', request)
    return data
  },

  getStatus: async (researchId: string): Promise<SessionStatusResponse> => {
    const { data } = await api.get(`/research/${researchId}/status`)
    return data
  },

  getReport: async (researchId: string): Promise<ResearchReport> => {
    const { data } = await api.get(`/research/${researchId}/report`)
    return data
  },

  exportPDF: (researchId: string): string =>
    `${BASE_URL}/research/${researchId}/report/pdf`,

  evaluate: async (researchId: string): Promise<EvaluationMetrics> => {
    const { data } = await api.get(`/research/${researchId}/evaluate`)
    return data
  },

  list: async (): Promise<SessionStatusResponse[]> => {
    const { data } = await api.get('/research')
    return data
  },
}
// ─── System ─────────────────────────────────────────────────────────────────────

export const systemApi = {
  health: async () => {
    const { data } = await api.get('/health', { baseURL: '' });
    return data;
  },

  stats: async (): Promise<SystemStats> => {
    const { data } = await api.get('/system/stats');
    return data;
  },
};

// ─── SSE Helper ─────────────────────────────────────────────────────────────────

export function createResearchSSE(
  researchId: string,
  onEvent: (type: string, data: Record<string, unknown>) => void,
  onError?: (e: Event) => void,
): () => void {
  const es = new EventSource(`/api/research/${researchId}/stream`);

  es.onmessage = (event) => {
    try {
      const parsed = JSON.parse(event.data);
      onEvent(parsed.type, parsed.data);
    } catch {
      // ignore parse errors
    }
  };

  if (onError) es.onerror = onError;

  return () => es.close();
}
