import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Clock, ChevronRight, Search } from 'lucide-react';
import { researchApi } from '../api';
import { StatusBadge, EmptyState, Spinner } from '../components/ui';

interface SessionSummary {
  research_id: string;
  query: string;
  status: string;
  current_iteration: number;
  evidence_count: number;
  has_report: boolean;
  created_at: string;
}

export default function SessionsPage() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    const load = async () => {
      try {
        const data = await researchApi.list() as unknown as SessionSummary[];
        setSessions(data);
      } catch {
        /* ignore */
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const filtered = sessions.filter(s =>
    s.query.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="h-screen flex flex-col">
      <div className="border-b px-6 py-5"
        style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}>
        <div className="flex items-center justify-between mb-4">
          <h1 className="font-display text-xl" style={{ color: 'var(--text-primary)' }}>
            Research Sessions
          </h1>
          <span className="text-xs px-2.5 py-1 rounded-full"
            style={{ background: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}>
            {sessions.length} total
          </span>
        </div>
        <div className="relative">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2"
            style={{ color: 'var(--text-muted)' }} />
          <input
            value={filter}
            onChange={e => setFilter(e.target.value)}
            placeholder="Search sessions..."
            className="input-field pl-8 py-2 text-xs"
          />
        </div>
      </div>

      <div className="flex-1 overflow-auto px-6 py-5">
        {loading ? (
          <div className="flex justify-center py-12"><Spinner size={24} /></div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={<BookOpen size={22} />}
            title={filter ? 'No matching sessions' : 'No research sessions yet'}
            description={filter ? 'Try a different search term' : 'Start a research query to see sessions here'}
            action={
              !filter && (
                <button onClick={() => navigate('/')} className="btn-primary text-xs">
                  Start Research
                </button>
              )
            }
          />
        ) : (
          <div className="space-y-2">
            {filtered.map(session => (
              <button
                key={session.research_id}
                onClick={() => navigate(`/monitor/${session.research_id}`)}
                className="w-full card text-left px-5 py-4 flex items-start gap-4 transition-all duration-150 hover:border-opacity-80"
                style={{ borderColor: 'var(--border)' }}
                onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--border-active)')}
                onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
              >
                {/* Status dot */}
                <div className="mt-1">
                  <StatusBadge status={session.status} />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium line-clamp-2 mb-2"
                    style={{ color: 'var(--text-primary)' }}>
                    {session.query}
                  </p>
                  <div className="flex flex-wrap gap-3 text-xs"
                    style={{ color: 'var(--text-muted)' }}>
                    <span className="flex items-center gap-1">
                      <Clock size={10} />
                      {new Date(session.created_at).toLocaleString()}
                    </span>
                    <span>iter {session.current_iteration}</span>
                    <span>{session.evidence_count} evidence pieces</span>
                    {session.has_report && (
                      <span style={{ color: '#34d399' }}>✓ Report ready</span>
                    )}
                  </div>
                </div>

                <ChevronRight size={14} style={{ color: 'var(--text-muted)' }} className="mt-1 shrink-0" />
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
