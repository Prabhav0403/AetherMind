import { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { Terminal, CheckCircle, AlertCircle, Download, BarChart3 } from 'lucide-react';
import { researchApi, createResearchSSE } from '../api';
import type { AgentActivityLog, SessionStatusResponse } from './types';
import { AgentBadge, StatusBadge, ProgressBar, Spinner, EmptyState } from '../components/ui';
import ReportViewer from '../components/ReportViewer';

export default function MonitorPage() {
  const { id } = useParams<{ id: string }>();
  const [session, setSession] = useState<SessionStatusResponse | null>(null);
  const [logs, setLogs] = useState<AgentActivityLog[]>([]);
  const [coverage, setCoverage] = useState(0);
  const [activeTab, setActiveTab] = useState<'logs' | 'report'>('logs');
  const [loading, setLoading] = useState(true);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval>>();

  // Scroll logs to bottom
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Initial load + SSE
  useEffect(() => {
    if (!id) return;

    const fetchStatus = async () => {
      try {
        const s = await researchApi.getStatus(id);
        setSession(s);
        if (s.activity_log) setLogs(s.activity_log);
        if (s.coverage_score !== undefined) setCoverage(s.coverage_score);
        if (s.status === 'completed' && s.report) setActiveTab('report');
        setLoading(false);
      } catch {
        setLoading(false);
      }
    };

    fetchStatus();

    // SSE for real-time updates
    const cleanup = createResearchSSE(id, (type, data) => {
      if (type === 'agent_activity') {
        const log = data as unknown as AgentActivityLog;
        setLogs(prev => {
          const exists = prev.some(l => l.log_id === log.log_id);
          if (exists) return prev;
          return [...prev, log];
        });
      }
      if (type === 'status_update') {
        setCoverage((data.coverage as number) ?? 0);
        // Poll for full status
        fetchStatus();
      }
      if (type === 'complete') {
        fetchStatus();
        if (data.has_report) setActiveTab('report');
      }
    });

    // Fallback polling every 3s
    pollRef.current = setInterval(fetchStatus, 3000);

    return () => {
      cleanup();
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [id]);

  // Stop polling when done
  useEffect(() => {
    if (session?.status === 'completed' || session?.status === 'failed') {
      if (pollRef.current) clearInterval(pollRef.current);
    }
  }, [session?.status]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner size={32} />
      </div>
    );
  }

  if (!session) {
    return (
      <EmptyState
        icon={<AlertCircle size={24} />}
        title="Session not found"
        description="This research session doesn't exist or has expired."
      />
    );
  }

  const isRunning = !['completed', 'failed'].includes(session.status);
  const progress = session.current_iteration / session.max_iterations;

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="border-b px-6 py-4 flex items-center justify-between shrink-0"
        style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}>
        <div className="flex-1 min-w-0 mr-4">
          <div className="flex items-center gap-3 mb-1">
            <StatusBadge status={session.status} />
            <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
              {id?.slice(0, 8)}
            </span>
          </div>
          <h1 className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>
            {session.activity_log?.[0]?.details?.query as string
              || 'Research in progress...'}
          </h1>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {/* Iteration indicator */}
          <div className="text-center px-3 py-1.5 rounded-lg"
            style={{ background: 'var(--bg-elevated)' }}>
            <div className="text-xs" style={{ color: 'var(--text-muted)' }}>Iteration</div>
            <div className="text-sm font-semibold tabular-nums" style={{ color: 'var(--text-primary)' }}>
              {session.current_iteration}/{session.max_iterations}
            </div>
          </div>

          {/* Coverage */}
          <div className="text-center px-3 py-1.5 rounded-lg"
            style={{ background: 'var(--bg-elevated)' }}>
            <div className="text-xs" style={{ color: 'var(--text-muted)' }}>Coverage</div>
            <div className="text-sm font-semibold tabular-nums"
              style={{ color: coverage >= 0.75 ? '#10b981' : '#f59e0b' }}>
              {Math.round(coverage * 100)}%
            </div>
          </div>

          {/* Export button */}
          {session.status === 'completed' && (
            <a
              href={researchApi.exportPDF(id!)}
              download
              className="btn-secondary text-xs"
            >
              <Download size={13} />
              Export
            </a>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className="px-6 py-2 border-b" style={{ borderColor: 'var(--border)' }}>
        <ProgressBar value={progress} label={`Pipeline progress`} />
      </div>

      {/* Tabs */}
      <div className="flex border-b shrink-0" style={{ borderColor: 'var(--border)' }}>
        {(['logs', 'report'] as const).map(tab => (
          <button key={tab}
            onClick={() => setActiveTab(tab)}
            className="px-5 py-3 text-sm transition-colors capitalize relative"
            style={{ color: activeTab === tab ? '#60a5fa' : 'var(--text-secondary)' }}
            disabled={tab === 'report' && !session.report}
          >
            {tab === 'logs' ? (
              <span className="flex items-center gap-2">
                <Terminal size={13} /> Agent Activity
                {isRunning && <span className="w-1.5 h-1.5 rounded-full bg-blue-400 dot-pulse" />}
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <BarChart3 size={13} /> Research Report
                {session.report && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />}
              </span>
            )}
            {activeTab === tab && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-400" />
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'logs' && (
          <div className="h-full overflow-auto p-4 space-y-2 font-mono text-xs">
            {logs.length === 0 ? (
              <div className="flex items-center gap-2 p-4"
                style={{ color: 'var(--text-muted)' }}>
                <Spinner size={14} />
                <span>Waiting for agent activity...</span>
              </div>
            ) : (
              logs.map((log) => (
                <LogEntry key={log.log_id} log={log} />
              ))
            )}
            <div ref={logsEndRef} />
          </div>
        )}

        {activeTab === 'report' && session.report && (
          <ReportViewer report={session.report} />
        )}
      </div>
    </div>
  );
}

function LogEntry({ log }: { log: AgentActivityLog }) {
  const isError = log.status === 'failed';
  const isComplete = log.status === 'completed';

  return (
    <div className="log-item flex items-start gap-3 px-3 py-2.5 rounded-lg"
      style={{
        background: isError ? 'rgba(244,63,94,0.05)' : 'var(--bg-elevated)',
        borderLeft: `2px solid ${
          isError ? '#f43f5e' :
          isComplete ? '#10b981' :
          log.status === 'running' ? '#3b82f6' : 'var(--border)'
        }`,
      }}>

      {/* Icon */}
      <div className="shrink-0 mt-0.5">
        {isError ? (
          <AlertCircle size={13} color="#f43f5e" />
        ) : isComplete ? (
          <CheckCircle size={13} color="#10b981" />
        ) : (
          <Spinner size={13} />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5 flex-wrap">
          <AgentBadge agent={log.agent} size="xs" />
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
            iter {log.iteration} · {new Date(log.timestamp).toLocaleTimeString()}
          </span>
        </div>
        <p style={{ color: isError ? '#fb7185' : 'var(--text-primary)' }}
          className="leading-relaxed">
          {log.message}
        </p>
        {log.details && (
          <details className="mt-1">
            <summary className="cursor-pointer text-xs" style={{ color: 'var(--text-muted)' }}>
              details
            </summary>
            <pre className="mt-1 text-xs overflow-auto p-2 rounded"
              style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', maxHeight: 120 }}>
              {JSON.stringify(log.details, null, 2)}
            </pre>
          </details>
        )}
      </div>
    </div>
  );
}
