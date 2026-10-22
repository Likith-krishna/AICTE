import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Pencil, CreditCard, Clock3, Building2, CalendarRange, MapPin, Workflow, Ban, RotateCw } from 'lucide-react';
import { clsx } from 'clsx';
import { PageHeader } from '@/components/ui/PageHeader';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ErrorState } from '@/components/ui/ErrorState';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Callout } from '@/components/ui/Callout';
import { Modal } from '@/components/ui/Modal';
import { StageProgress } from '@/components/applications/StageProgress';
import { WorkflowTimeline } from '@/components/applications/WorkflowTimeline';
import { ActionPanel } from '@/components/applications/ActionPanel';
import { api, errorMessage } from '@/lib/api';
import { formatDateTime, formatDuration, ROUTE_LABELS } from '@/lib/labels';
import type { ApplicationDetail, FormSchema, Timeline } from '@/types/api';

type Tab = 'timeline' | 'details' | 'clock';

export function ApplicationDetailPage() {
  const { id = '' } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  // Copied into local state (rather than read from location.state on every
  // render) so it can be cleared once stale. location.state otherwise lingers
  // in the browser's session history indefinitely — including across a page
  // reload — showing an outdated message (e.g. "complete the payment") even
  // after a later action (confirming payment, a workflow transition) has
  // already moved the application past what the flash describes.
  const [flash, setFlash] = useState<string | null>((location.state as { flash?: string } | null)?.flash ?? null);
  const [tab, setTab] = useState<Tab>('timeline');
  const flashBaselineVersion = useRef<number | null>(null);

  useEffect(() => {
    if ((location.state as { flash?: string } | null)?.flash) {
      // Scrub it from history so a reload can't resurrect the stale message.
      navigate(location.pathname, { replace: true, state: null });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const app = useQuery({
    queryKey: ['application', id],
    queryFn: () => api.get<ApplicationDetail>(`/applications/${id}`),
  });
  const timeline = useQuery({
    queryKey: ['application-timeline', id],
    queryFn: () => api.get<Timeline>(`/applications/${id}/timeline`),
    enabled: !!app.data,
  });

  useEffect(() => {
    if (!app.data) return;
    if (flashBaselineVersion.current === null) {
      flashBaselineVersion.current = app.data.version;
      return;
    }
    if (flash && app.data.version !== flashBaselineVersion.current) {
      // Any later action (payment confirmation, a transition, an edit) has
      // superseded whatever the flash described — drop it.
      setFlash(null);
    }
  }, [app.data, flash]);

  if (app.isLoading) return <div className="card"><LoadingSpinner /></div>;
  if (app.error || !app.data) {
    return (
      <div>
        <PageHeader title="Application" breadcrumbs={[{ label: 'Dashboard', href: '/' }, { label: 'Applications', href: '/applications' }]} />
        <div className="card"><ErrorState error={app.error} onRetry={() => app.refetch()} /></div>
      </div>
    );
  }
  const a = app.data;

  return (
    <div className="max-w-7xl">
      <PageHeader
        title={a.reference_number}
        description={`${a.category.name} · ${a.institution.name}`}
        breadcrumbs={[{ label: 'Dashboard', href: '/' }, { label: 'Applications', href: '/applications' }, { label: a.reference_number }]}
        actions={
          <>
            <StatusBadge status={a.stage} label={a.stage_label} className="text-sm px-3 py-1" />
            {a.status !== 'ACTIVE' && <StatusBadge status={a.status} className="text-sm px-3 py-1" />}
            <button className="btn-ghost btn-sm" onClick={() => { app.refetch(); timeline.refetch(); }} aria-label="Refresh">
              <RotateCw size={14} className={clsx(app.isFetching && 'animate-spin')} />
            </button>
          </>
        }
      />

      {flash && <Callout tone="success" className="mb-4">{flash}</Callout>}

      <div className="card p-4 sm:p-5 mb-5">
        <StageProgress routeType={a.workflow.route_type} stage={a.stage} closed={a.status === 'CLOSED'} />
        {a.stage_note && <Callout tone="warning" className="mt-4">{a.stage_note}</Callout>}
        {a.decision && (
          <div className="mt-4 border-t border-brand-border pt-3 text-sm">
            <span className="text-brand-text-muted">Recorded decision: </span>
            <StatusBadge status={a.decision} /> <span className="text-brand-text-muted">on {formatDateTime(a.decided_at)}</span>
            {a.decision_remarks && <p className="mt-1 text-ink-charcoal whitespace-pre-wrap">{a.decision_remarks}</p>}
          </div>
        )}
      </div>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0 space-y-5">
          {a.stage === 'DRAFT' && a.status === 'ACTIVE' && <DraftCard app={a} />}

          <div className="card">
            <div role="tablist" aria-label="Application sections" className="flex border-b border-brand-border px-2 overflow-x-auto">
              {([['timeline', 'Workflow history'], ['details', 'Application details'], ['clock', 'Clock log']] as [Tab, string][]).map(([key, label]) => (
                <button
                  key={key}
                  role="tab"
                  aria-selected={tab === key}
                  aria-controls={`panel-${key}`}
                  id={`tab-${key}`}
                  onClick={() => setTab(key)}
                  className={clsx(
                    'px-3 py-3 text-sm whitespace-nowrap border-b-2 -mb-px transition-colors',
                    tab === key ? 'border-ink-slate text-ink-charcoal font-medium' : 'border-transparent text-brand-text-muted hover:text-ink-charcoal',
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
            <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="p-4 sm:p-5">
              {tab === 'details' ? (
                <DetailsPanel app={a} />
              ) : timeline.isLoading ? (
                <LoadingSpinner />
              ) : timeline.error || !timeline.data ? (
                <ErrorState error={timeline.error} onRetry={() => timeline.refetch()} />
              ) : tab === 'timeline' ? (
                <WorkflowTimeline timeline={timeline.data} />
              ) : (
                <ClockLog timeline={timeline.data} />
              )}
            </div>
          </div>
        </div>

        <aside className="space-y-5">
          <section className="card p-4" aria-labelledby="actions-heading">
            <h2 id="actions-heading" className="text-sm font-semibold text-ink-charcoal mb-3">Your actions</h2>
            <ActionPanel app={a} />
          </section>
          <PaymentCard app={a} />
          <ClockCard app={a} />
          <section className="card p-4 text-sm" aria-labelledby="meta-heading">
            <h2 id="meta-heading" className="text-sm font-semibold text-ink-charcoal mb-3">Summary</h2>
            <dl className="space-y-2.5">
              <Meta icon={<Building2 size={14} />} label="Institution" value={`${a.institution.name} (${a.institution.pid})`} />
              <Meta icon={<MapPin size={14} />} label="Region" value={a.region ? `${a.region.name} (${a.region.code})` : '—'} />
              <Meta icon={<CalendarRange size={14} />} label="Academic year" value={a.academic_year.year_label} />
              <Meta icon={<Workflow size={14} />} label="Workflow"
                    value={`${a.workflow.name} · v${a.workflow.version} (${ROUTE_LABELS[a.workflow.route_type] ?? a.workflow.route_type})`} />
              <Meta label="Created" value={formatDateTime(a.created_at)} />
              <Meta label="Submitted" value={formatDateTime(a.submitted_at)} />
              <Meta label="Record version" value={String(a.version)} />
            </dl>
          </section>
        </aside>
      </div>
    </div>
  );
}

function Meta({ icon, label, value }: { icon?: JSX.Element; label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <span className="text-brand-text-muted mt-0.5 w-3.5 shrink-0">{icon}</span>
      <div className="min-w-0">
        <dt className="text-xs text-brand-text-muted">{label}</dt>
        <dd className="text-ink-charcoal break-words">{value}</dd>
      </div>
    </div>
  );
}

function DraftCard({ app }: { app: ApplicationDetail }) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [confirm, setConfirm] = useState(false);
  const withdraw = useMutation({
    mutationFn: () => api.post<ApplicationDetail>(`/applications/${app.id}/withdraw`, { expected_version: app.version }),
    onSuccess: (u) => {
      qc.setQueryData(['application', app.id], u);
      qc.invalidateQueries({ queryKey: ['applications'] });
      setConfirm(false);
    },
  });
  const missing = Object.keys(app.form_errors).length;
  return (
    <div className="card p-4 sm:p-5 border-l-4 border-l-ink-slate">
      <h2 className="text-base mb-1">This application is a draft</h2>
      <p className="text-sm text-brand-text-muted">
        {missing > 0 ? `${missing} field(s) still need attention before it can be submitted.` : 'All fields are complete — review and submit when ready.'}
        {' '}Drafts are visible only to your institution.
      </p>
      {app.permissions.can_edit && (
        <div className="flex flex-wrap gap-2 mt-3">
          <button className="btn-primary" onClick={() => navigate(`/applications/${app.id}/edit`)}>
            <Pencil size={16} /> Continue editing
          </button>
          <button className="btn-secondary" onClick={() => setConfirm(true)}><Ban size={16} /> Withdraw draft</button>
        </div>
      )}
      {confirm && (
        <Modal title="Withdraw draft?" onClose={() => setConfirm(false)}
          footer={<>
            <button className="btn-secondary" onClick={() => setConfirm(false)}>Keep draft</button>
            <button className="btn-danger" disabled={withdraw.isPending} onClick={() => withdraw.mutate()}>
              {withdraw.isPending ? 'Withdrawing…' : 'Withdraw'}
            </button>
          </>}>
          <p className="text-sm">The draft will be marked as withdrawn and can no longer be edited or submitted. It is retained for the audit trail.</p>
          {withdraw.error && <Callout tone="error" className="mt-3">{errorMessage(withdraw.error)}</Callout>}
        </Modal>
      )}
    </div>
  );
}

function PaymentCard({ app }: { app: ApplicationDetail }) {
  const qc = useQueryClient();
  const pay = useMutation({
    mutationFn: () => api.post<ApplicationDetail>(`/applications/${app.id}/mock-payment`, { expected_version: app.version }),
    onSuccess: (u) => {
      qc.setQueryData(['application', app.id], u);
      qc.invalidateQueries({ queryKey: ['application-timeline', app.id] });
      qc.invalidateQueries({ queryKey: ['applications'] });
    },
  });
  if (app.stage === 'DRAFT') return null;
  const p = app.payment;
  return (
    <section className="card p-4" aria-labelledby="pay-heading">
      <h2 id="pay-heading" className="text-sm font-semibold text-ink-charcoal mb-3 flex items-center gap-2">
        <CreditCard size={15} /> Payment
      </h2>
      <div className="flex items-center gap-2 mb-2">
        <StatusBadge status={p.status} label={p.status === 'MOCK_CONFIRMED' ? 'Mock confirmed' : 'Not initiated'} />
      </div>
      {p.is_mock && (
        <Callout tone="mock" title="SIMULATED — not a real payment">
          Reference <code className="font-mono text-xs">{p.reference}</code> was generated by the mock gateway on{' '}
          {formatDateTime(p.confirmed_at)}. No money was transferred.
        </Callout>
      )}
      <p className="text-xs text-brand-text-muted mt-2">{p.fee_note}</p>
      {app.permissions.can_mock_pay && (
        <>
          <Callout tone="mock" className="mt-3" title="Mock payment gateway">
            The real AICTE/NSWS payment integration is not available. This button records a simulated confirmation so the
            workflow can proceed to scrutiny.
          </Callout>
          {pay.error && <Callout tone="error" className="mt-2">{errorMessage(pay.error)}</Callout>}
          <button className="btn-primary w-full mt-3" disabled={pay.isPending} onClick={() => pay.mutate()}>
            {pay.isPending ? 'Recording…' : 'Simulate payment (MOCK)'}
          </button>
        </>
      )}
    </section>
  );
}

function ClockCard({ app }: { app: ApplicationDetail }) {
  const c = app.clock;
  if (app.stage === 'DRAFT') return null;
  return (
    <section className="card p-4" aria-labelledby="clock-heading">
      <h2 id="clock-heading" className="text-sm font-semibold text-ink-charcoal mb-3 flex items-center gap-2">
        <Clock3 size={15} /> Processing clock
      </h2>
      <p className="text-sm mb-3">
        {c.completed ? 'Case closed — clocks stopped.' : c.current_owner ? (
          <>With <strong>{c.current_owner === 'AICTE' ? 'AICTE' : 'the institution'}</strong></>
        ) : 'Not started'}
      </p>
      <dl className="grid grid-cols-2 gap-2 text-sm">
        <div className="rounded bg-gray-50 border border-brand-border p-2">
          <dt className="text-xs text-brand-text-muted">AICTE time</dt>
          <dd className="font-semibold">{formatDuration(c.elapsed_seconds.AICTE)}</dd>
        </div>
        <div className="rounded bg-gray-50 border border-brand-border p-2">
          <dt className="text-xs text-brand-text-muted">Institution time</dt>
          <dd className="font-semibold">{formatDuration(c.elapsed_seconds.INSTITUTION)}</dd>
        </div>
      </dl>
      <p className="text-xs text-brand-text-muted mt-2">{c.policy_note}</p>
    </section>
  );
}

function ClockLog({ timeline }: { timeline: Timeline }) {
  if (timeline.clock_events.length === 0) return <p className="text-sm text-brand-text-muted">No clock events yet.</p>;
  return (
    <div className="table-container">
      <table>
        <thead><tr><th>When</th><th>Event</th><th>Owner</th><th>Reason</th></tr></thead>
        <tbody>
          {timeline.clock_events.map((e) => (
            <tr key={e.id}>
              <td className="whitespace-nowrap text-xs">{formatDateTime(e.occurred_at)}</td>
              <td><code className="font-mono text-xs">{e.event_type}</code></td>
              <td>{e.clock_owner}</td>
              <td className="text-xs text-brand-text-muted">{e.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-xs text-brand-text-muted mt-3">Append-only log (spec §5.2). {timeline.clock.policy_note}</p>
    </div>
  );
}

function DetailsPanel({ app }: { app: ApplicationDetail }) {
  const schema = useQuery({
    queryKey: ['form-schema', app.category.code],
    queryFn: () => api.get<FormSchema>(`/applications/form-schema/${app.category.code}`),
    staleTime: Infinity,
  });
  if (schema.isLoading) return <LoadingSpinner />;
  if (schema.error || !schema.data) return <ErrorState error={schema.error} onRetry={() => schema.refetch()} />;
  const fields = schema.data.fields;
  const filled = fields.filter((f) => app.form_data[f.name] !== undefined);
  if (filled.length === 0) return <p className="text-sm text-brand-text-muted">No details entered yet.</p>;
  return (
    <>
      <dl className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
        {fields.map((f) => {
          const v = app.form_data[f.name];
          return (
            <div key={f.name} className={f.type === 'textarea' || f.type === 'checkbox' ? 'sm:col-span-2' : ''}>
              <dt className="text-xs text-brand-text-muted">{f.label}</dt>
              <dd className="text-sm whitespace-pre-wrap break-words">
                {f.type === 'checkbox' ? (v ? 'Confirmed' : 'Not confirmed') : v === undefined || v === '' ? '—' : String(v)}
                {app.form_errors[f.name] && <span className="block text-xs text-status-error">{app.form_errors[f.name]}</span>}
              </dd>
            </div>
          );
        })}
      </dl>
      <p className="text-xs text-brand-text-muted mt-4">
        Form schema v{app.form_schema_version ?? '—'} · {schema.data.verification_note}
      </p>
      {app.stage === 'DRAFT' && app.permissions.can_edit && (
        <Link to={`/applications/${app.id}/edit`} className="btn-secondary btn-sm mt-3">Edit details</Link>
      )}
    </>
  );
}
