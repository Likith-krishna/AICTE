import type { ReactNode } from 'react';
import { AlertTriangle, Info, ShieldAlert, CheckCircle2 } from 'lucide-react';
import { clsx } from 'clsx';

type Tone = 'info' | 'warning' | 'error' | 'success' | 'mock';

const STYLES: Record<Tone, { box: string; icon: ReactNode }> = {
  info: { box: 'bg-status-info-bg/60 border-status-info/30 text-ink-charcoal', icon: <Info size={16} className="text-status-info" /> },
  warning: { box: 'bg-status-warning-bg border-status-warning/30 text-ink-charcoal', icon: <AlertTriangle size={16} className="text-status-warning" /> },
  error: { box: 'bg-status-error-bg border-status-error/30 text-status-error', icon: <ShieldAlert size={16} className="text-status-error" /> },
  success: { box: 'bg-status-success-bg border-status-success/30 text-ink-charcoal', icon: <CheckCircle2 size={16} className="text-status-success" /> },
  mock: { box: 'bg-ink-ivory border-dashed border-ink-slate text-ink-charcoal', icon: <ShieldAlert size={16} className="text-ink-slate" /> },
};

/** Inline notice. Use tone="mock" for anything simulated so it can never be mistaken for a real transaction. */
export function Callout({ tone = 'info', title, children, className }: {
  tone?: Tone; title?: string; children?: ReactNode; className?: string;
}) {
  const s = STYLES[tone];
  return (
    <div role={tone === 'error' ? 'alert' : 'note'} className={clsx('flex gap-2.5 rounded border px-3 py-2.5 text-sm', s.box, className)}>
      <span className="mt-0.5 shrink-0">{s.icon}</span>
      <div className="min-w-0">
        {title && <div className="font-medium">{title}</div>}
        {children && <div className={clsx(title && 'mt-0.5', 'text-[13px] leading-relaxed')}>{children}</div>}
      </div>
    </div>
  );
}
