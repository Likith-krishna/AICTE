import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Gavel, CheckCircle2, XCircle, AlertTriangle, ArrowRightCircle } from 'lucide-react';
import { clsx } from 'clsx';
import { Modal } from '@/components/ui/Modal';
import { Callout } from '@/components/ui/Callout';
import { api, ApiError, errorMessage } from '@/lib/api';
import { roleLabel } from '@/lib/labels';
import { useAuth } from '@/lib/auth';
import type { ApplicationDetail, AvailableAction } from '@/types/api';

const MIN_REMARKS = 10;

const TONE_BUTTON: Record<AvailableAction['tone'], string> = {
  approve: 'btn bg-status-success text-white hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-status-success focus:ring-offset-2',
  reject: 'btn-danger',
  warn: 'btn bg-status-warning text-white hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-status-warning focus:ring-offset-2',
  neutral: 'btn-primary',
};

const TONE_ICON: Record<AvailableAction['tone'], JSX.Element> = {
  approve: <CheckCircle2 size={16} />,
  reject: <XCircle size={16} />,
  warn: <AlertTriangle size={16} />,
  neutral: <ArrowRightCircle size={16} />,
};

export function ActionPanel({ app }: { app: ApplicationDetail }) {
  const { user } = useAuth();
  const [pending, setPending] = useState<AvailableAction | null>(null);
  const actions = app.available_actions;

  if (app.status !== 'ACTIVE') {
    return (
      <p className="text-sm text-brand-text-muted">
        This application is {app.status.toLowerCase()}; no further workflow actions are possible.
      </p>
    );
  }
  if (actions.length === 0) {
    return (
      <p className="text-sm text-brand-text-muted">
        No action is required from you ({roleLabel(user?.role)}) at the <strong>{app.stage_label}</strong> stage.
      </p>
    );
  }
  return (
    <>
      <div className="flex flex-col gap-2">
        {actions.map((a) => (
          <div key={a.to_stage}>
            <button
              className={clsx(TONE_BUTTON[a.tone], 'w-full justify-start')}
              onClick={() => setPending(a)}
              disabled={a.blockers.length > 0}
              aria-describedby={a.blockers.length ? `blk-${a.to_stage}` : undefined}
            >
              {a.is_decision ? <Gavel size={16} /> : TONE_ICON[a.tone]}
              {a.label}
            </button>
            {a.blockers.length > 0 && (
              <p id={`blk-${a.to_stage}`} className="text-xs text-status-error mt-1">{a.blockers.join(' ')}</p>
            )}
          </div>
        ))}
      </div>
      {pending && <ConfirmTransition app={app} action={pending} onClose={() => setPending(null)} />}
    </>
  );
}

function ConfirmTransition({ app, action, onClose }: { app: ApplicationDetail; action: AvailableAction; onClose: () => void }) {
  const qc = useQueryClient();
  const [remarks, setRemarks] = useState('');
  const [touched, setTouched] = useState(false);
  const remarksError = action.requires_remarks && remarks.trim().length < MIN_REMARKS
    ? `Please record at least ${MIN_REMARKS} characters explaining this action.` : null;

  const mutation = useMutation({
    mutationFn: () =>
      api.post<ApplicationDetail>(`/applications/${app.id}/transition`, {
        to_stage: action.to_stage,
        remarks: remarks.trim() || null,
        expected_version: app.version,
      }),
    onSuccess: (updated) => {
      qc.setQueryData(['application', app.id], updated);
      qc.invalidateQueries({ queryKey: ['application-timeline', app.id] });
      qc.invalidateQueries({ queryKey: ['applications'] });
      qc.invalidateQueries({ queryKey: ['dashboard-stats'] });
      onClose();
    },
    onError: (err) => {
      if (err instanceof ApiError && err.status === 409) {
        qc.invalidateQueries({ queryKey: ['application', app.id] });
        qc.invalidateQueries({ queryKey: ['application-timeline', app.id] });
      }
    },
  });

  const conflict = mutation.error instanceof ApiError && mutation.error.status === 409;

  return (
    <Modal
      title={action.label}
      icon={action.is_decision ? <Gavel size={18} /> : undefined}
      onClose={onClose}
      footer={
        <>
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
          <button
            className={TONE_BUTTON[action.tone]}
            disabled={mutation.isPending || (!!remarksError && action.requires_remarks) || conflict}
            onClick={() => { setTouched(true); if (!remarksError) mutation.mutate(); }}
          >
            {mutation.isPending ? 'Recording…' : `Confirm: ${action.label}`}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <p className="text-sm">
          <span className="text-brand-text-muted">Move </span>
          <strong>{app.reference_number}</strong>
          <span className="text-brand-text-muted"> from </span>
          <strong>{app.stage_label}</strong>
          <span className="text-brand-text-muted"> to </span>
          <strong>{action.to_stage_label}</strong>.
        </p>
        {action.is_decision && (
          <Callout tone="warning" title="Official decision">
            You are recording a decision in your capacity as {roleLabel('competent_authority')}. FlowGuard records and
            audits the decision; it does not make it.
          </Callout>
        )}
        {action.note && <Callout tone="info">{action.note}</Callout>}
        <div>
          <label htmlFor="remarks" className="label">
            Remarks {action.requires_remarks ? <span className="text-status-error">*</span> : <span className="text-brand-text-muted font-normal">(optional)</span>}
          </label>
          <textarea
            id="remarks"
            className={clsx('input', touched && remarksError && 'border-status-error')}
            rows={4}
            maxLength={4000}
            value={remarks}
            onChange={(e) => setRemarks(e.target.value)}
            onBlur={() => setTouched(true)}
            aria-invalid={touched && !!remarksError}
            aria-describedby="remarks-hint"
            placeholder={action.requires_remarks ? 'Reasons are recorded in the audit trail and shown in the timeline.' : ''}
          />
          <p id="remarks-hint" className={clsx('text-xs mt-1', touched && remarksError ? 'text-status-error' : 'text-brand-text-muted')}>
            {touched && remarksError ? remarksError : `${remarks.trim().length} / 4000`}
          </p>
        </div>
        {mutation.error && (
          <Callout tone="error" title={conflict ? 'This application changed' : 'Action not recorded'}>
            {errorMessage(mutation.error)}
            {conflict && ' The latest version has been loaded — close this dialog and review it.'}
            {mutation.error instanceof ApiError && mutation.error.failures && (
              <ul className="list-disc ml-4 mt-1">{mutation.error.failures.map((f) => <li key={f}>{f}</li>)}</ul>
            )}
          </Callout>
        )}
      </div>
    </Modal>
  );
}
