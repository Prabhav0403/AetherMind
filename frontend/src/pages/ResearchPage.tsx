import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, ChevronRight, Sliders, Zap } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { researchApi } from '../api';
import { Spinner } from '../components/ui';

const EXAMPLE_QUERIES = [
  'What are the key advances and limitations of Retrieval-Augmented Generation systems?',
  'How do multi-agent AI frameworks improve complex reasoning tasks?',
  'Compare transformer-based language models for knowledge-intensive NLP tasks',
  'What is the state of the art in autonomous research agents and knowledge synthesis?',
];

export default function ResearchPage() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [maxIterations, setMaxIterations] = useState(3);
  const [targetCoverage, setTargetCoverage] = useState(0.75);
  const [reportStyle, setReportStyle] = useState('academic');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!query.trim() || query.length < 10) {
      toast.error('Please enter a research question (min 10 characters)');
      return;
    }

    setLoading(true);
    try {
      const response = await researchApi.start({
        query: query.trim(),
        max_iterations: maxIterations,
        target_coverage: targetCoverage,
        report_style: reportStyle,
      });
      toast.success('Research session started!');
      navigate(`/monitor/${response.research_id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to start research';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid-bg flex flex-col">
      {/* Header */}
      <div className="border-b px-8 py-6"
        style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}>
        <h1 className="font-display text-2xl font-normal" style={{ color: 'var(--text-primary)' }}>
          Research Query
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
          Ask a complex research question. Agents will plan, retrieve, analyze, and synthesize a report.
        </p>
      </div>

      <div className="flex-1 overflow-auto px-8 py-8 max-w-3xl mx-auto w-full">

        {/* Hero input */}
        <div className="card p-6 space-y-4 mb-6" style={{ borderColor: 'rgba(59,130,246,0.2)' }}>
          <div className="flex items-start gap-3">
            <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
              style={{ background: 'rgba(59,130,246,0.15)' }}>
              <Search size={16} color="#60a5fa" />
            </div>
            <div className="flex-1">
              <label className="block text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
                RESEARCH QUESTION
              </label>
              <textarea
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="What would you like the agents to research?"
                rows={4}
                className="input-field resize-none"
                style={{ fontSize: '15px', lineHeight: '1.6' }}
                onKeyDown={e => {
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit();
                }}
              />
              <div className="flex justify-between mt-1.5">
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  {query.length}/2000 · Ctrl+Enter to submit
                </span>
                <span className="text-xs" style={{ color: query.length >= 10 ? 'var(--accent-emerald)' : 'var(--text-muted)' }}>
                  {query.length >= 10 ? '✓ Ready' : `${10 - query.length} more chars needed`}
                </span>
              </div>
            </div>
          </div>

          {/* Advanced settings toggle */}
          {/* Free provider notice */}
          <div className="flex items-center gap-2 text-xs px-3 py-2 rounded-lg"
            style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)' }}>
            <span style={{ color: '#34d399' }}>✦</span>
            <span style={{ color: 'var(--text-secondary)' }}>
              Using <strong style={{ color: '#34d399' }}>free-tier</strong> models (Groq / Cerebras) — no credit card required.
              Upload documents first for best results.
            </span>
          </div>

          <button
            className="flex items-center gap-1.5 text-xs transition-colors"
            style={{ color: showAdvanced ? '#60a5fa' : 'var(--text-muted)' }}
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            <Sliders size={12} />
            Advanced Settings
            <ChevronRight size={12}
              className="transition-transform"
              style={{ transform: showAdvanced ? 'rotate(90deg)' : 'none' }} />
          </button>

          {showAdvanced && (
            <div className="grid grid-cols-3 gap-4 pt-2 border-t" style={{ borderColor: 'var(--border)' }}>
              <div>
                <label className="block text-xs mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                  Max Iterations
                </label>
                <select
                  value={maxIterations}
                  onChange={e => setMaxIterations(Number(e.target.value))}
                  className="input-field text-xs py-2"
                >
                  {[1,2,3,4,5].map(n => (
                    <option key={n} value={n}>{n} iteration{n > 1 ? 's' : ''}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                  Target Coverage
                </label>
                <select
                  value={targetCoverage}
                  onChange={e => setTargetCoverage(Number(e.target.value))}
                  className="input-field text-xs py-2"
                >
                  <option value={0.5}>50% — Fast</option>
                  <option value={0.65}>65% — Standard</option>
                  <option value={0.75}>75% — Thorough</option>
                  <option value={0.85}>85% — Deep</option>
                  <option value={0.95}>95% — Exhaustive</option>
                </select>
              </div>
              <div>
                <label className="block text-xs mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                  Report Style
                </label>
                <select
                  value={reportStyle}
                  onChange={e => setReportStyle(e.target.value)}
                  className="input-field text-xs py-2"
                >
                  <option value="academic">Academic</option>
                  <option value="business">Business</option>
                  <option value="technical">Technical</option>
                </select>
              </div>
            </div>
          )}

          <button
            onClick={handleSubmit}
            disabled={loading || query.length < 10}
            className="btn-primary w-full justify-center py-3"
          >
            {loading ? <Spinner size={16} /> : <Zap size={16} />}
            {loading ? 'Initializing Agents...' : 'Start Research'}
          </button>
        </div>

        {/* Example queries */}
        <div>
          <h3 className="text-xs font-medium mb-3 uppercase tracking-wider"
            style={{ color: 'var(--text-muted)' }}>
            Example Research Questions
          </h3>
          <div className="space-y-2">
            {EXAMPLE_QUERIES.map((q, i) => (
              <button
                key={i}
                onClick={() => setQuery(q)}
                className="w-full text-left px-4 py-3 rounded-xl text-sm transition-all duration-150 border"
                style={{
                  background: 'var(--bg-card)',
                  borderColor: 'var(--border)',
                  color: 'var(--text-secondary)',
                }}
                onMouseEnter={e => {
                  (e.target as HTMLElement).style.borderColor = 'rgba(59,130,246,0.3)';
                  (e.target as HTMLElement).style.color = 'var(--text-primary)';
                }}
                onMouseLeave={e => {
                  (e.target as HTMLElement).style.borderColor = 'var(--border)';
                  (e.target as HTMLElement).style.color = 'var(--text-secondary)';
                }}
              >
                <span className="text-xs mr-2" style={{ color: 'var(--text-muted)' }}>↗</span>
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* Agent pipeline diagram */}
        <div className="mt-8 card p-5">
          <h3 className="text-xs font-medium uppercase tracking-wider mb-4"
            style={{ color: 'var(--text-muted)' }}>
            Agent Pipeline
          </h3>
          <div className="flex items-center gap-2 flex-wrap">
            {[
              { emoji: '🗺', label: 'Planner', color: '#8b5cf6', desc: 'Task decomposition' },
              { emoji: '🔍', label: 'Researcher', color: '#3b82f6', desc: 'Evidence retrieval' },
              { emoji: '🔬', label: 'Analyst', color: '#f59e0b', desc: 'Gap detection' },
              { emoji: '✍️', label: 'Writer', color: '#10b981', desc: 'Report synthesis' },
            ].map((agent, i, arr) => (
              <div key={agent.label} className="flex items-center gap-2">
                <div className="text-center">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center text-lg mb-1"
                    style={{ background: `${agent.color}22`, border: `1px solid ${agent.color}44` }}>
                    {agent.emoji}
                  </div>
                  <div className="text-xs font-medium" style={{ color: agent.color }}>
                    {agent.label}
                  </div>
                  <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    {agent.desc}
                  </div>
                </div>
                {i < arr.length - 1 && (
                  <ChevronRight size={14} style={{ color: 'var(--text-muted)' }} className="mb-4" />
                )}
              </div>
            ))}
            <div className="flex items-center gap-2 ml-2">
              <div className="w-px h-8 mx-1" style={{ background: 'var(--border)' }} />
              <div className="text-center">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center text-lg mb-1"
                  style={{ background: '#f59e0b22', border: '1px solid #f59e0b44' }}>
                  🔁
                </div>
                <div className="text-xs font-medium" style={{ color: '#f59e0b' }}>Loop</div>
                <div className="text-xs" style={{ color: 'var(--text-muted)' }}>Until coverage met</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
