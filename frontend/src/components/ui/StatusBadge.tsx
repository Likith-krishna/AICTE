import { clsx } from 'clsx';

const STAGE_COLORS: Record<string, string> = {
  DRAFT: 'badge-neutral',
  SUBMITTED: 'badge-info',
  PAYMENT_VERIFIED: 'badge-info',
  UNDER_SCRUTINY: 'badge-warning',
  SCRUTINY_CLEAR: 'badge-success',
  DEFICIENCY_NOTED: 'badge-error',
  AWAITING_INSTITUTION_RESPONSE: 'badge-warning',
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
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const colorClass = STAGE_COLORS[status] || 'badge-neutral';
  const label = status.replace(/_/g, ' ');

  return (
    <span className={clsx(colorClass, className)}>
      {label}
    </span>
  );
}
