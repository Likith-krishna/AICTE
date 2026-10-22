import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, FileText, ClipboardCheck, Shield, Bell, BarChart3,
  BookOpen, Users, Settings, ChevronLeft, ChevronRight, Building2
} from 'lucide-react';
import { useAuth } from '@/lib/auth';
import type { RoleName } from '@/types/api';
import { APPLICATION_ROLES } from '@/lib/labels';

interface NavItem {
  label: string;
  path: string;
  icon: React.ReactNode;
  roles?: RoleName[];
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', path: '/', icon: <LayoutDashboard size={18} /> },
  { label: 'Applications', path: '/applications', icon: <FileText size={18} />, roles: [...APPLICATION_ROLES] },
  { label: 'Institutions', path: '/institutions', icon: <Building2 size={18} />, roles: ['system_admin', 'regional_officer', 'regional_coordinator', 'bureau_officer', 'scrutiny_officer', 'competent_authority'] },
  { label: 'Scrutiny', path: '/scrutiny', icon: <ClipboardCheck size={18} />, roles: ['scrutiny_officer', 'regional_officer', 'regional_coordinator', 'bureau_officer'] },
  { label: 'Compliance', path: '/compliance', icon: <Shield size={18} /> },
  { label: 'Notifications', path: '/notifications', icon: <Bell size={18} /> },
  { label: 'Reports', path: '/reports', icon: <BarChart3 size={18} />, roles: ['bureau_officer', 'regional_coordinator', 'competent_authority', 'system_admin'] },
  { label: 'Rules', path: '/rules', icon: <BookOpen size={18} />, roles: ['rule_admin', 'system_admin', 'audit_reviewer'] },
  { label: 'Users', path: '/users', icon: <Users size={18} />, roles: ['system_admin'] },
  { label: 'Audit Log', path: '/audit', icon: <Settings size={18} />, roles: ['system_admin', 'audit_reviewer'] },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const { user } = useAuth();

  const visibleItems = NAV_ITEMS.filter(item =>
    !item.roles || item.roles.includes(user?.role as RoleName)
  );

  return (
    <aside
      className={`fixed left-0 top-0 h-screen z-30 flex flex-col transition-all duration-200 ${
        collapsed ? 'w-16' : 'w-60'
      }`}
      style={{ backgroundColor: 'var(--color-sidebar-bg)' }}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 h-16 border-b border-white/10">
        <div className="w-8 h-8 rounded bg-ink-slate flex items-center justify-center text-white font-bold text-sm shrink-0">
          FG
        </div>
        {!collapsed && (
          <div className="overflow-hidden">
            <div className="text-sm font-semibold" style={{ color: 'var(--color-sidebar-text)' }}>
              FlowGuard
            </div>
            <div className="text-[10px] opacity-60" style={{ color: 'var(--color-sidebar-text)' }}>
              AICTE Workflow
            </div>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 py-2 overflow-y-auto">
        {visibleItems.map(item => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 mx-2 px-3 py-2.5 rounded text-sm transition-colors ${
                isActive
                  ? 'text-white font-medium'
                  : 'text-white/70 hover:text-white'
              }`
            }
            style={({ isActive }) => ({
              backgroundColor: isActive ? 'var(--color-sidebar-active)' : undefined,
            })}
            title={collapsed ? item.label : undefined}
          >
            <span className="shrink-0">{item.icon}</span>
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Collapse Toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-center h-10 border-t border-white/10 text-white/60 hover:text-white transition-colors"
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>
    </aside>
  );
}
