/** Shared display labels. Role codes mirror backend app/core/roles.py. */
export const ROLE_LABELS: Record<string, string> = {
  institution_applicant: 'Institution Applicant',
  institution_signatory: 'Authorised Signatory',
  regional_officer: 'Regional Officer',
  scrutiny_officer: 'Scrutiny Officer',
  regional_coordinator: 'Regional Coordinator',
  bureau_officer: 'Regulation Bureau Officer',
  evc_coordinator: 'EVC Coordinator',
  evc_member: 'EVC Member',
  sac_shc_member: 'SAC/SHC Committee Member',
  competent_authority: 'Competent Authority',
  compliance_officer: 'Compliance Officer',
  system_admin: 'System Administrator',
  rule_admin: 'Rule Administrator',
  audit_reviewer: 'Audit Reviewer',
  system: 'System (automatic)',
};

export const ROUTE_LABELS: Record<string, string> = {
  FULL: 'Scrutiny + EVC',
  SCRUTINY_ONLY: 'Scrutiny only',
  SELF_DISCLOSURE: 'Self-disclosure',
};

/** Roles that may read application content (backend enforces the same rule). */
export const APPLICATION_ROLES = [
  'institution_applicant', 'institution_signatory', 'regional_officer', 'scrutiny_officer',
  'regional_coordinator', 'bureau_officer', 'evc_coordinator', 'evc_member', 'sac_shc_member',
  'competent_authority', 'compliance_officer', 'audit_reviewer',
] as const;

export function roleLabel(role: string | null | undefined): string {
  if (!role) return '—';
  return ROLE_LABELS[role] ?? role.replace(/_/g, ' ');
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return '—';
  if (seconds < 60) return `${Math.max(0, Math.round(seconds))}s`;
  const m = Math.floor(seconds / 60);
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 48) return `${h}h ${m % 60}m`;
  const d = Math.floor(h / 24);
  return `${d}d ${h % 24}h`;
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}
