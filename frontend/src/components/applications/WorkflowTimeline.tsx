import { Bot, User2, AlertTriangle, BookMarked } from 'lucide-react';
import { clsx } from 'clsx';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { formatDateTime, formatDuration, roleLabel } from '@/lib/labels';
import type { Timeline, TimelineTransition } from '@/types/api';

function MetaNotes({ t }: { t: TimelineTransition }) {
  const m = t.metadata as {
    mock?: boolean; human_confirmation?: string; validation_performed?: boolean; note?: string;
    rule_refs?: { rule_family_code: string; status: string }[];
    workflow_definition?: { name: string; version: number };
  };
  const notes: JSX.Element[] = [];
  if (m.mock) notes.push(<span key="mock" className="badge bg-ink-ivory text-ink-slate border border-dashed border-ink-slate">MOCK — not a real transaction</span>);
  if (m.human_confirmation) notes.push(<span key="hc" className="text-xs text-brand-text-muted">{m.human_confirmation}</span>);
  if (m.validation_performed === false && m.note) {
    notes.push(<span key="val" className="text-xs text-status-warning flex gap-1"><AlertTriangle size={12} className="mt-0.5 shrink-0" />{m.note}</span>);
  }
  if (m.rule_refs?.length) {
    notes.push(
      <span key="rules" className="text-xs text-brand-text-muted flex gap-1 flex-wrap items-center">
        <BookMarked size={12} /> Rules referenced:
        {m.rule_refs.map((r) => <code key={r.rule_family_code} className="font-mono text-[11px] bg-gray-100 px-1 rounded" title={r.status}>{r.rule_family_code} · {r.status.split(' — ')[0]}</code>)}
      </span>,
    );
  }
  return notes.length ? <div className="mt-2 flex flex-col gap-1 items-start">{notes}</div> : null;
}

/** Vertical timeline built only from persisted transition events. */
export function WorkflowTimeline({ timeline }: { timeline: Timeline }) {
  const items = [...timeline.transitions].reverse();
  if (items.length === 0) {
    return <p className="text-sm text-brand-text-muted">No workflow transitions yet — the application is still a draft.</p>;
  }
  return (
    <ol className="relative" aria-label="Workflow history, newest first">
      {items.map((t, i) => {
        const system = t.trigger_type === 'AUTOMATIC';
        const stay = timeline.stage_entries.find((s) => s.stage === t.to_stage && s.entered_at === t.occurred_at);
        return (
          <li key={t.id} className="relative pl-9 pb-6 last:pb-0">
            {i < items.length - 1 && <span className="absolute left-[13px] top-7 bottom-0 w-px bg-ink-gray" aria-hidden />}
            <span
              className={clsx(
                'absolute left-0 top-0.5 w-7 h-7 rounded-full flex items-center justify-center border',
                system ? 'bg-ink-ivory border-ink-gray text-brand-text-muted' : 'bg-ink-slate border-ink-slate text-white',
              )}
              aria-hidden
            >
              {system ? <Bot size={14} /> : <User2 size={14} />}
            </span>
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <StatusBadge status={t.to_stage} label={t.to_stage_label} />
              <span className="text-xs text-brand-text-muted">from {t.from_stage_label}</span>
              <time className="text-xs text-brand-text-muted ml-auto" dateTime={t.occurred_at}>{formatDateTime(t.occurred_at)}</time>
            </div>
            <div className="text-xs text-brand-text-muted mt-1">
              {system ? 'Automatic step' : (
                <>
                  {t.actor.name ? <span className="text-ink-charcoal font-medium">{t.actor.name}</span> : 'An official'}
                  {' · '}{roleLabel(t.actor.role)}
                </>
              )}
              {t.sequence_no != null && <> · step #{t.sequence_no}</>}
              {stay && <> · in stage {stay.exited_at ? formatDuration(stay.duration_seconds) : `for ${formatDuration(stay.duration_seconds)} (current)`}</>}
            </div>
            {t.remarks && <p className="mt-1.5 text-sm text-ink-charcoal bg-gray-50 border border-brand-border rounded px-3 py-2 whitespace-pre-wrap">{t.remarks}</p>}
            <MetaNotes t={t} />
          </li>
        );
      })}
    </ol>
  );
}
