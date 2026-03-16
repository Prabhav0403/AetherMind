import React from 'react';
import { clsx } from 'clsx';
import type { AgentType, AgentStatus, ResearchStatus } from '../pages/types';

// ─── Agent Badge ────────────────────────────────────────────────────────────────

const AGENT_ICONS: Record<AgentType, string> = {
  planner:      '🗺',
  researcher:   '🔍',
  analyst:      '🔬',
  writer:       '✍️',
  orchestrator: '⚡',
};

const AGENT_LABELS: Record<AgentType, string> = {
  planner:      'Planner',
  researcher:   'Researcher',
  analyst:      'Analyst',
  writer:       'Writer',
  orchestrator: 'Orchestrator',
};

export function AgentBadge({ agent, size = 'sm' }: {
  agent: AgentType;
  size?: 'xs' | 'sm' | 'md';
}) {
  return (
    <span className={clsx(
      'agent-badge',
      `agent-${agent}`,
      size === 'xs' && 'text-xs px-1.5 py-0.5',
      size === 'md' && 'text-sm px-3 py-1.5',
    )}>
      <span>{AGENT_ICONS[agent]}</span>
      <span>{AGENT_LABELS[agent]}</span>
    </span>
  );
}

// ─── Status Badge ───────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<string, string> = {
  pending:     'Pending',
  planning:    'Planning',
  researching: 'Researching',
  analyzing:   'Analyzing',
  writing:     'Writing',
  refining:    'Refining',
  completed:   'Completed',
  failed:      'Failed',
  idle:        'Idle',
  running:     'Running',
  waiting:     'Waiting',
  indexed:     'Indexed',
  processing:  'Processing',
};

export function StatusBadge({ status }: { status: string }) {
  const isActive = ['planning', 'researching', 'analyzing', 'writing', 'refining', 'running', 'processing'].includes(status);
  const isComplete = ['completed', 'indexed'].includes(status);
  const isFailed = status === 'failed';

  return (
    <span className={clsx(
      'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium',
      isActive && 'status-running',
      isComplete && 'status-completed',
      isFailed && 'status-failed',
      !isActive && !isComplete && !isFailed && 'status-pending',
    )}>
      {isActive && (
        <span className="w-1.5 h-1.5 rounded-full bg-blue-400 dot-pulse" />
      )}
      {isComplete && (
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
      )}
      {isFailed && (
        <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
      )}
      {!isActive && !isComplete && !isFailed && (
        <span className="w-1.5 h-1.5 rounded-full bg-slate-400 opacity-50" />
      )}
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

// ─── Progress Bar ───────────────────────────────────────────────────────────────

export function ProgressBar({ value, max = 1, label }: {
  value: number;
  max?: number;
  label?: string;
}) {
  const pct = Math.min(Math.round((value / max) * 100), 100);
  return (
    <div className="space-y-1">
      {label && (
        <div className="flex justify-between text-xs" style={{ color: 'var(--text-secondary)' }}>
          <span>{label}</span>
          <span>{pct}%</span>
        </div>
      )}
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ─── Score Ring ─────────────────────────────────────────────────────────────────

export function ScoreRing({ score, label, size = 60 }: {
  score: number;
  label: string;
  size?: number;
}) {
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score * circumference);
  const color = score >= 0.8 ? '#10b981' : score >= 0.5 ? '#f59e0b' : '#f43f5e';

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size/2} cy={size/2} r={radius}
          fill="none" stroke="rgba(148,180,212,0.1)" strokeWidth={5} />
        <circle cx={size/2} cy={size/2} r={radius}
          fill="none" stroke={color} strokeWidth={5}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 1s ease-out' }} />
      </svg>
      <div className="text-center -mt-[46px]" style={{ height: size }}>
        <div className="flex items-center justify-center h-full flex-col">
          <span className="text-base font-semibold" style={{ color }}>
            {Math.round(score * 100)}
          </span>
        </div>
      </div>
      <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{label}</span>
    </div>
  );
}

// ─── Empty State ────────────────────────────────────────────────────────────────

export function EmptyState({ icon, title, description, action }: {
  icon: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4"
        style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)' }}>
        {icon}
      </div>
      <h3 className="text-base font-medium mb-1" style={{ color: 'var(--text-primary)' }}>
        {title}
      </h3>
      {description && (
        <p className="text-sm max-w-xs" style={{ color: 'var(--text-secondary)' }}>
          {description}
        </p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

// ─── Spinner ────────────────────────────────────────────────────────────────────

export function Spinner({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      className="animate-spin" style={{ color: 'var(--accent-blue)' }}>
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3"
        strokeDasharray="31.4" strokeDashoffset="10" strokeLinecap="round" />
    </svg>
  );
}
