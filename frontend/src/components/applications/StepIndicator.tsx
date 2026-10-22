import { Check } from 'lucide-react';
import { clsx } from 'clsx';

export function StepIndicator({ steps, current }: { steps: string[]; current: number }) {
  return (
    <ol className="flex items-center gap-2 sm:gap-4 mb-6 overflow-x-auto" aria-label="Application progress">
      {steps.map((label, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <li key={label} className="flex items-center gap-2 shrink-0" aria-current={active ? 'step' : undefined}>
            <span
              className={clsx(
                'w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold border',
                done && 'bg-ink-slate border-ink-slate text-white',
                active && 'bg-white border-ink-slate text-ink-slate ring-2 ring-ink-slate/25',
                !done && !active && 'bg-white border-ink-gray text-brand-text-muted',
              )}
            >
              {done ? <Check size={14} /> : i + 1}
            </span>
            <span className={clsx('text-sm', active ? 'font-medium text-ink-charcoal' : 'text-brand-text-muted')}>{label}</span>
            {i < steps.length - 1 && <span className="w-6 sm:w-10 h-px bg-ink-gray" aria-hidden />}
          </li>
        );
      })}
    </ol>
  );
}
