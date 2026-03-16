import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { BookOpen, Award, Link2, ChevronDown, ChevronUp } from 'lucide-react';
import type { ResearchReport } from '../pages/types';
import { ScoreRing, ProgressBar } from './ui';

export default function ReportViewer({ report }: { report: ResearchReport }) {
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const [showAllCitations, setShowAllCitations] = useState(false);

  const toggleSection = (title: string) =>
    setExpandedSection(prev => prev === title ? null : title);

  const displayedCitations = showAllCitations
    ? report.citations
    : report.citations.slice(0, 8);

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-4xl mx-auto px-6 py-6 space-y-6">

        {/* Report header */}
        <div className="card p-6 space-y-4">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: 'rgba(59,130,246,0.15)' }}>
              <BookOpen size={22} color="#60a5fa" />
            </div>
            <div className="flex-1 min-w-0">
              <h1 className="font-display text-xl leading-tight mb-2"
                style={{ color: 'var(--text-primary)' }}>
                {report.title}
              </h1>
              <div className="flex flex-wrap gap-3 text-xs" style={{ color: 'var(--text-secondary)' }}>
                <span>Generated {new Date(report.generated_at).toLocaleString()}</span>
                <span>·</span>
                <span>{report.sections.length} sections</span>
                <span>·</span>
                <span>{report.citations.length} citations</span>
                <span>·</span>
                <span>{report.total_evidence_used} evidence pieces</span>
                <span>·</span>
                <span>{report.iteration_count} iteration{report.iteration_count > 1 ? 's' : ''}</span>
              </div>
            </div>
          </div>

          {/* Quality metrics */}
          <div className="flex items-center gap-6 pt-4 border-t" style={{ borderColor: 'var(--border)' }}>
            <ScoreRing score={report.quality_score} label="Quality" size={64} />
            <div className="flex-1 space-y-2">
              <ProgressBar
                value={report.quality_score}
                label="Overall Quality Score"
              />
              <ProgressBar
                value={Math.min(report.citations.length / 10, 1)}
                label="Citation Density"
              />
              <ProgressBar
                value={Math.min(
                  report.sections.reduce((a, s) => a + s.content.split(' ').length, 0) / 2000,
                  1
                )}
                label="Report Completeness"
              />
            </div>
          </div>
        </div>

        {/* Sections */}
        <div className="space-y-3">
          {report.sections.map((section) => {
            const isExpanded = expandedSection === section.title || section.title === 'Abstract';
            const wordCount = section.content.split(' ').length;

            return (
              <div key={section.title} className="card overflow-hidden">
                <button
                  onClick={() => toggleSection(section.title)}
                  className="w-full flex items-center justify-between px-5 py-4 text-left transition-colors"
                  style={{
                    background: isExpanded ? 'rgba(59,130,246,0.05)' : 'transparent',
                  }}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-1.5 h-5 rounded-full"
                      style={{ background: isExpanded ? '#3b82f6' : 'var(--border-active)' }} />
                    <span className="font-medium text-sm" style={{ color: 'var(--text-primary)' }}>
                      {section.title}
                    </span>
                    {section.citations.length > 0 && (
                      <span className="text-xs px-2 py-0.5 rounded-full"
                        style={{ background: 'rgba(59,130,246,0.15)', color: '#93c5fd' }}>
                        {section.citations.length} ref{section.citations.length > 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                      ~{wordCount} words
                    </span>
                    {isExpanded
                      ? <ChevronUp size={14} style={{ color: 'var(--text-muted)' }} />
                      : <ChevronDown size={14} style={{ color: 'var(--text-muted)' }} />}
                  </div>
                </button>

                {isExpanded && (
                  <div className="px-5 pb-5 border-t" style={{ borderColor: 'var(--border)' }}>
                    <div className="pt-4 report-prose">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {section.content}
                      </ReactMarkdown>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Citations */}
        {report.citations.length > 0 && (
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-4">
              <Link2 size={15} style={{ color: '#60a5fa' }} />
              <h3 className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                References ({report.citations.length})
              </h3>
            </div>
            <div className="space-y-2">
              {displayedCitations.map((citation) => (
                <div key={citation.citation_id}
                  className="flex items-start gap-3 py-2 px-3 rounded-lg"
                  style={{ background: 'var(--bg-elevated)' }}>
                  <span className="text-xs font-mono px-1.5 py-0.5 rounded shrink-0 mt-0.5"
                    style={{
                      background: 'rgba(59,130,246,0.2)',
                      color: '#93c5fd',
                      minWidth: 28,
                      textAlign: 'center',
                    }}>
                    [{citation.number}]
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm truncate" style={{ color: 'var(--text-primary)' }}>
                      {citation.source}
                    </p>
                    <div className="flex gap-3 text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                      {citation.page && <span>p. {citation.page}</span>}
                      <span>relevance: {Math.round(citation.relevance * 100)}%</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            {report.citations.length > 8 && (
              <button
                onClick={() => setShowAllCitations(!showAllCitations)}
                className="mt-3 text-xs"
                style={{ color: '#60a5fa' }}
              >
                {showAllCitations
                  ? '↑ Show fewer'
                  : `↓ Show ${report.citations.length - 8} more`}
              </button>
            )}
          </div>
        )}

        {/* Quality award */}
        {report.quality_score >= 0.8 && (
          <div className="card p-4 flex items-center gap-3"
            style={{ borderColor: 'rgba(245,158,11,0.3)', background: 'rgba(245,158,11,0.05)' }}>
            <Award size={20} color="#f59e0b" />
            <div>
              <p className="text-sm font-medium" style={{ color: '#fcd34d' }}>
                High Quality Report
              </p>
              <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                Quality score {Math.round(report.quality_score * 100)}/100 — comprehensive evidence coverage
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
