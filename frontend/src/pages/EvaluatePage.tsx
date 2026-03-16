import { useState } from 'react';
import { BarChart3, TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { researchApi } from '../api';
import type { EvaluationMetrics } from './types';
import { ScoreRing, ProgressBar, Spinner } from '../components/ui';

export default function EvaluatePage() {
  const [researchId, setResearchId] = useState('');
  const [metrics, setMetrics] = useState<EvaluationMetrics | null>(null);
  const [loading, setLoading] = useState(false);

  const evaluate = async () => {
    if (!researchId.trim()) {
      toast.error('Enter a research session ID');
      return;
    }
    setLoading(true);
    try {
      const data = await researchApi.evaluate(researchId.trim());
      setMetrics(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Evaluation failed';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-screen flex flex-col">
      <div className="border-b px-6 py-5"
        style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}>
        <h1 className="font-display text-xl" style={{ color: 'var(--text-primary)' }}>
          Evaluation Metrics
        </h1>
        <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
          Assess research quality: factual accuracy, coverage, citation correctness, hallucination rate
        </p>
      </div>

      <div className="flex-1 overflow-auto px-6 py-6 max-w-3xl mx-auto w-full">
        {/* Input */}
        <div className="card p-5 mb-6">
          <label className="block text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
            RESEARCH SESSION ID
          </label>
          <div className="flex gap-3">
            <input
              value={researchId}
              onChange={e => setResearchId(e.target.value)}
              placeholder="e.g. f47ac10b-58cc-4372-..."
              className="input-field flex-1"
              onKeyDown={e => e.key === 'Enter' && evaluate()}
            />
            <button onClick={evaluate} disabled={loading} className="btn-primary px-5">
              {loading ? <Spinner size={15} /> : <BarChart3 size={15} />}
              Evaluate
            </button>
          </div>
          <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>
            Copy the research ID from the Monitor page URL bar.
          </p>
        </div>

        {metrics && (
          <div className="space-y-5 animate-fade-in">
            {/* Overall score */}
            <div className="card p-6 text-center">
              <ScoreRing score={metrics.overall_score} label="Overall Score" size={88} />
              <p className="mt-4 text-sm" style={{ color: 'var(--text-secondary)' }}>
                Research session <span className="font-mono text-xs">{metrics.research_id.slice(0, 8)}</span>
              </p>
            </div>

            {/* Detailed metrics */}
            <div className="card p-5 space-y-4">
              <h3 className="text-sm font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
                Detailed Metrics
              </h3>
              <ProgressBar value={metrics.factual_accuracy} label="Factual Accuracy" />
              <ProgressBar value={metrics.coverage_score} label="Topic Coverage" />
              <ProgressBar value={metrics.citation_correctness} label="Citation Correctness" />
              <ProgressBar value={1 - metrics.hallucination_rate} label="Hallucination Resistance" />
              <ProgressBar value={metrics.response_completeness} label="Response Completeness" />
            </div>

            {/* Stats grid */}
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: 'Iterations Used', value: metrics.iterations_used, icon: TrendingUp, color: '#8b5cf6' },
                { label: 'Evidence Pieces', value: metrics.evidence_pieces, icon: CheckCircle, color: '#10b981' },
                { label: 'Report Words', value: metrics.report_length_words.toLocaleString(), icon: BarChart3, color: '#3b82f6' },
              ].map(({ label, value, icon: Icon, color }) => (
                <div key={label} className="card p-4 text-center">
                  <Icon size={18} className="mx-auto mb-2" style={{ color }} />
                  <p className="text-xl font-semibold tabular-nums" style={{ color: 'var(--text-primary)' }}>
                    {value}
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{label}</p>
                </div>
              ))}
            </div>

            {/* Hallucination warning */}
            {metrics.hallucination_rate > 0.3 && (
              <div className="card p-4 flex items-start gap-3"
                style={{ borderColor: 'rgba(245,158,11,0.3)', background: 'rgba(245,158,11,0.05)' }}>
                <AlertTriangle size={16} style={{ color: '#f59e0b' }} className="mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium" style={{ color: '#fcd34d' }}>
                    Elevated Hallucination Risk
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                    Hallucination rate at {Math.round(metrics.hallucination_rate * 100)}%. Consider running
                    additional iterations or uploading more relevant documents.
                  </p>
                </div>
              </div>
            )}

            {/* Comparison note */}
            <div className="card p-5" style={{ borderColor: 'rgba(59,130,246,0.2)' }}>
              <h4 className="text-xs font-medium uppercase tracking-wider mb-3"
                style={{ color: 'var(--text-muted)' }}>
                vs. Traditional Single-Pass RAG
              </h4>
              <div className="space-y-2">
                {[
                  { metric: 'Topic Coverage', agentic: metrics.coverage_score, baseline: 0.45 },
                  { metric: 'Citation Density', agentic: metrics.citation_correctness, baseline: 0.30 },
                  { metric: 'Factual Accuracy', agentic: metrics.factual_accuracy, baseline: 0.60 },
                ].map(({ metric, agentic, baseline }) => (
                  <div key={metric} className="flex items-center gap-3 text-xs">
                    <span className="w-28 shrink-0" style={{ color: 'var(--text-secondary)' }}>
                      {metric}
                    </span>
                    <div className="flex-1 flex items-center gap-2">
                      <div className="flex-1 h-2 rounded-full overflow-hidden"
                        style={{ background: 'var(--bg-elevated)' }}>
                        <div className="h-full rounded-full transition-all duration-700"
                          style={{ width: `${agentic * 100}%`, background: '#3b82f6' }} />
                      </div>
                      <span style={{ color: '#60a5fa', minWidth: 32, textAlign: 'right' }}>
                        {Math.round(agentic * 100)}%
                      </span>
                    </div>
                    <div className="flex-1 flex items-center gap-2">
                      <div className="flex-1 h-2 rounded-full overflow-hidden"
                        style={{ background: 'var(--bg-elevated)' }}>
                        <div className="h-full rounded-full"
                          style={{ width: `${baseline * 100}%`, background: '#4a6785' }} />
                      </div>
                      <span style={{ color: 'var(--text-muted)', minWidth: 32, textAlign: 'right' }}>
                        {Math.round(baseline * 100)}%
                      </span>
                    </div>
                  </div>
                ))}
                <div className="flex justify-end gap-4 text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                  <span><span style={{ color: '#60a5fa' }}>■</span> Agentic RAG</span>
                  <span><span style={{ color: '#4a6785' }}>■</span> Baseline RAG</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
