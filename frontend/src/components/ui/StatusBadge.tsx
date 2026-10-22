import { clsx } from 'clsx';

const STAGE_COLORS: Record<string, string> = {
  DRAFT: 'badge-neutral',
  SUBMITTED: 'badge-info',
  PAYMENT_VERIFIED: 'badge-info',
  UNDER_SCRUTINY: 'badge-warning',
  SCRUTINY_CLEAR: 'badge-success',
  DEFICIENCY_NOTED: 'badge-error',
  AWAITING_INSTITUTION_RESPONSE: 'badge-warning',
  RESPONSE_RECEIVED: 'badge-info',
  RE_SCRUTINY: 'badge-warning',
  REPORT_SUBMITTED: 'badge-info',
  SHC_COMPLIANCE: 'badge-warning',
  SHC_RECOMMENDATION: 'badge-info',
  SAC_HEARING: 'badge-warning',
  SAC_RECOMMENDATION: 'badge-info',
  SELF_DISCLOSURE_VALIDATED: 'badge-info',
  DEFICIENCY_FREE: 'badge-success',
  DEFICIENCY_DETECTED: 'badge-error',
  EOA_ISSUED: 'badge-success',
  ACTIVE: 'badge-info',
  CLOSED: 'badge-neutral',
  WITHDRAWN: 'badge-neutral',
  NOT_INITIATED: 'badge-warning',
  MOCK_CONFIRMED: 'badge-info',
  EVC_QUEUED: 'badge-info',
  EVC_SCHEDULED: 'badge-info',
  EVC_IN_PROGRESS: 'badge-warning',
  EVC_COMPLETED: 'badge-success',
  PLACED_BEFORE_EC: 'badge-info',
  EC_DECISION: 'badge-warning',
  APPROVED: 'badge-success',
  APPROVED_WITH_CONDITIONS: 'badge-warning',
  REJECTED: 'badge-error',
  FINAL_REJECTION: 'badge-error',
  PENDING: 'badge-warning',
  COMPLETED: 'badge-success',
  OPEN: 'badge-error',
  RESOLVED: 'badge-success',
};

interface StatusBadgeProps {
  status: string;
  label?: string;
  className?: string;
}

export function StatusBadge({ status, label: labelOverride, className }: StatusBadgeProps) {
  const colorClass = STAGE_COLORS[status] || 'badge-neutral';
  const label = labelOverride ?? status.replace(/_/g, ' ');

  return (
    <span className={clsx(colorClass, className)}>
      {label}
    </span>
  );
}
