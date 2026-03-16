import { NavLink } from 'react-router-dom';
import { Search, FileText, BookOpen, Activity, BarChart3, Settings } from 'lucide-react';
import { clsx } from 'clsx';

const NAV_ITEMS = [
  { to: '/',          icon: Search,    label: 'Research' },
  { to: '/documents', icon: FileText,  label: 'Documents' },
  { to: '/sessions',  icon: BookOpen,  label: 'Sessions' },
  { to: '/monitor',   icon: Activity,  label: 'Live Monitor' },
  { to: '/evaluate',  icon: BarChart3, label: 'Evaluate' },
];

export default function Sidebar() {
  return (
    <aside className="w-56 flex flex-col border-r shrink-0"
      style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)', height: '100vh' }}>

      {/* Logo */}
      <div className="px-5 py-6 border-b" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center text-base"
            style={{ background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)' }}>
            <img src="/ragpic.svg" alt="AetherMind" className="w-full h-full object-contain" />
          </div>
          <div>
            <div className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
              AetherMind
            </div>
            <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
              Research Assistant
            </div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => clsx(
              'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150',
              isActive
                ? 'font-medium'
                : 'hover:opacity-100',
            )}
            style={({ isActive }) => ({
              background: isActive ? 'rgba(59,130,246,0.12)' : 'transparent',
              color: isActive ? '#60a5fa' : 'var(--text-secondary)',
              borderLeft: isActive ? '2px solid #3b82f6' : '2px solid transparent',
            })}
          >
            <Icon size={15} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t" style={{ borderColor: 'var(--border)' }}>
        <div className="text-xs space-y-0.5" style={{ color: 'var(--text-muted)' }}>
          <p className="font-medium" style={{ color: 'var(--text-secondary)' }}>
            AetherMind v1.0
          </p>
          <p>Planner · Researcher</p>
          <p>Analyst · Writer</p>
        </div>
      </div>
    </aside>
  );
}
