import { Bell, LogOut, User as UserIcon } from 'lucide-react';
import { useAuth } from '@/lib/auth';

const ROLE_LABELS: Record<string, string> = {
  institution_applicant: 'Institution',
  institution_signatory: 'Signatory',
  regional_officer: 'Regional Officer',
  scrutiny_officer: 'Scrutiny Officer',
  regional_coordinator: 'Regional Coordinator',
  bureau_officer: 'Bureau Officer',
  evc_coordinator: 'EVC Coordinator',
  evc_member: 'EVC Member',
  sac_shc_member: 'SAC/SHC',
  competent_authority: 'Authority',
  compliance_officer: 'Compliance',
  system_admin: 'Admin',
  rule_admin: 'Rule Admin',
  audit_reviewer: 'Auditor',
};

export function Header() {
  const { user, logout } = useAuth();

  return (
    <header
      className="h-16 flex items-center justify-between px-6 border-b"
      style={{
        backgroundColor: 'var(--color-header-bg)',
        borderColor: 'var(--color-header-border)',
      }}
    >
      <div>
        <h1 className="text-lg font-semibold text-ink-charcoal">AICTE FlowGuard</h1>
      </div>

      <div className="flex items-center gap-4">
        <button className="btn-ghost btn-sm relative" title="Notifications">
          <Bell size={18} />
        </button>

        <div className="flex items-center gap-3 pl-4 border-l border-brand-border">
          <div className="w-8 h-8 rounded-full bg-ink-slate flex items-center justify-center">
            <UserIcon size={14} className="text-white" />
          </div>
          <div className="hidden sm:block">
            <div className="text-sm font-medium text-ink-charcoal">{user?.full_name}</div>
            <div className="text-xs text-brand-text-muted">
              {ROLE_LABELS[user?.role || ''] || user?.role}
            </div>
          </div>
          <button
            onClick={logout}
            className="btn-ghost btn-sm text-brand-text-muted hover:text-status-error"
            title="Sign out"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </header>
  );
}
