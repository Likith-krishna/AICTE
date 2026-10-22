import { Check } from 'lucide-react';
import { clsx } from 'clsx';

const MILESTONE_OF: Record<string, string> = {
  DRAFT: 'draft',
  SUBMITTED: 'submitted', PAYMENT_VERIFIED: 'submitted',
  UNDER_SCRUTINY: 'scrutiny', DEFICIENCY_NOTED: 'scrutiny', AWAITING_INSTITUTION_RESPONSE: 'scrutiny',
  RESPONSE_RECEIVED: 'scrutiny', RE_SCRUTINY: 'scrutiny', SCRUTINY_CLEAR: 'scrutiny',
  SELF_DISCLOSURE_VALIDATED: 'scrutiny', DEFICIENCY_FREE: 'scrutiny', DEFICIENCY_DETECTED: 'scrutiny',
  EVC_QUEUED: 'evc', EVC_SCHEDULED: 'evc', EVC_IN_PROGRESS: 'evc', EVC_COMPLETED: 'evc', REPORT_SUBMITTED: 'evc',
  SHC_COMPLIANCE: 'ec', SHC_RECOMMENDATION: 'ec', PLACED_BEFORE_EC: 'ec', EC_DECISION: 'ec',
  APPROVED: 'outcome', APPROVED_WITH_CONDITIONS: 'outcome', REJECTED: 'outcome', SAC_HEARING: 'outcome',
  SAC_RECOMMENDATION: 'outcome', FINAL_REJECTION: 'outcome', EOA_ISSUED: 'outcome',
};

const ROUTE_MILESTONES: Record<string, [string, string][]> = {
  FULL: [['draft', 'Draft'], ['submitted', 'Submitted'], ['scrutiny', 'Scrutiny'], ['evc', 'EVC'], ['ec', 'Executive Committee'], ['outcome', 'Decision']],
  SCRUTINY_ONLY: [['draft', 'Draft'], ['submitted', 'Submitted'], ['scrutiny', 'Scrutiny'], ['ec', 'Executive Committee'], ['outcome', 'Decision']],
  SELF_DISCLOSURE: [['draft', 'Draft'], ['submitted', 'Submitted'], ['scrutiny', 'Officer review'], ['outcome', 'Decision']],
};

/** Coarse milestone bar for the application's workflow route. */
export function StageProgress({ routeType, stage, closed }: { routeType: string; stage: string; closed: boolean }) {
  const milestones = ROUTE_MILESTONES[routeType] ?? ROUTE_MILESTONES.FULL;
  const currentKey = MILESTONE_OF[stage] ?? 'scrutiny';
  const currentIdx = Math.max(0, milestones.findIndex(([k]) => k === currentKey));

  return (
    <ol className="flex items-start" aria-label="Workflow milestones">
      {milestones.map(([key, label], i) => {
        const done = i < currentIdx || (closed && i === currentIdx);
        const active = i === currentIdx && !closed;
        return (
          <li key={key} className="flex-1 min-w-0 flex flex-col items-center text-center relative" aria-current={active ? 'step' : undefined}>
            {i > 0 && (
              <span className={clsx('absolute top-3 right-1/2 w-full h-0.5', i <= currentIdx ? 'bg-ink-slate' : 'bg-ink-gray')} aria-hidden />
            )}
            <span
              className={clsx(
                'relative z-10 w-6 h-6 rounded-full border-2 flex items-center justify-center text-[10px] font-semibold',
                done && 'bg-ink-slate border-ink-slate text-white',
                active && 'bg-white border-ink-slate text-ink-slate ring-4 ring-ink-slate/20',
                !done && !active && 'bg-white border-ink-gray text-brand-text-muted',
              )}
            >
              {done ? <Check size={12} /> : i + 1}
            </span>
            <span className={clsx('mt-1.5 text-[11px] leading-tight px-0.5', active ? 'text-ink-charcoal font-semibold' : 'text-brand-text-muted')}>
              {label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
