import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm, type Resolver } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowLeft, ArrowRight, Save, Send, Pencil } from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ErrorState } from '@/components/ui/ErrorState';
import { Callout } from '@/components/ui/Callout';
import { StepIndicator } from '@/components/applications/StepIndicator';
import { FormFieldInput } from '@/components/applications/FormFieldInput';
import { api, ApiError, errorMessage } from '@/lib/api';
import { buildZodSchema, defaultValues, groupBySection, toPayload } from '@/lib/formSchema';
import { formatDateTime } from '@/lib/labels';
import type { ApplicationDetail, FormSchema } from '@/types/api';

type Values = Record<string, unknown>;

export function ApplicationFormPage() {
  const { id = '' } = useParams();
  const app = useQuery({
    queryKey: ['application', id],
    queryFn: () => api.get<ApplicationDetail>(`/applications/${id}`),
  });
  const schema = useQuery({
    queryKey: ['form-schema', app.data?.category.code],
    queryFn: () => api.get<FormSchema>(`/applications/form-schema/${app.data!.category.code}`),
    enabled: !!app.data,
    staleTime: Infinity,
  });

  if (app.isLoading || (app.data && schema.isLoading)) return <div className="card"><LoadingSpinner /></div>;
  if (app.error || schema.error) {
    return <div className="card"><ErrorState error={app.error || schema.error} onRetry={() => { app.refetch(); schema.refetch(); }} /></div>;
  }
  if (!app.data || !schema.data) return null;
  if (!app.data.permissions.can_edit) {
    return (
      <div className="card p-6">
        <Callout tone="info" title="This application can no longer be edited">
          Only active drafts can be edited by the institution applicant.{' '}
          <Link to={`/applications/${id}`}>Open the application</Link>
        </Callout>
      </div>
    );
  }
  return <DraftEditor app={app.data} schema={schema.data} />;
}

function DraftEditor({ app, schema }: { app: ApplicationDetail; schema: FormSchema }) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [step, setStep] = useState<1 | 2>(1);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [banner, setBanner] = useState<{ tone: 'error' | 'success'; text: string; failures?: string[] } | null>(null);
  const versionRef = useRef(app.version);
  const modeRef = useRef<'draft' | 'full'>('full');

  const fullSchema = useMemo(() => buildZodSchema(schema, { partial: false }), [schema]);
  const draftSchema = useMemo(() => buildZodSchema(schema, { partial: true }), [schema]);
  const resolver: Resolver<Values> = (values, ctx, opts) =>
    zodResolver(modeRef.current === 'draft' ? draftSchema : fullSchema)(values, ctx, opts);

  const form = useForm<Values>({ defaultValues: defaultValues(schema, app.form_data), resolver, mode: 'onTouched' });
  const { register, handleSubmit, formState, setError, getValues } = form;

  useEffect(() => { versionRef.current = app.version; }, [app.version]);

  const applyServerErrors = (err: unknown) => {
    if (err instanceof ApiError && err.fieldErrors) {
      for (const [name, message] of Object.entries(err.fieldErrors)) setError(name, { type: 'server', message });
    }
  };

  const save = useMutation({
    mutationFn: (values: Values) =>
      api.patch<ApplicationDetail>(`/applications/${app.id}`, {
        form_data: toPayload(schema, values),
        expected_version: versionRef.current,
      }),
    onSuccess: (updated) => {
      versionRef.current = updated.version;
      qc.setQueryData(['application', app.id], updated);
      qc.invalidateQueries({ queryKey: ['applications'] });
      setSavedAt(updated.updated_at);
    },
    onError: (err) => {
      applyServerErrors(err);
      setBanner({ tone: 'error', text: errorMessage(err) });
    },
  });

  const submit = useMutation({
    mutationFn: () =>
      api.post<ApplicationDetail>(`/applications/${app.id}/transition`, {
        to_stage: 'SUBMITTED',
        expected_version: versionRef.current,
      }),
    onSuccess: (updated) => {
      qc.setQueryData(['application', app.id], updated);
      qc.invalidateQueries({ queryKey: ['applications'] });
      qc.invalidateQueries({ queryKey: ['dashboard-stats'] });
      navigate(`/applications/${app.id}`, { state: { flash: 'Application submitted. Complete the (mock) payment to proceed to scrutiny.' } });
    },
    onError: (err) => setBanner({ tone: 'error', text: errorMessage(err), failures: err instanceof ApiError ? err.failures : undefined }),
  });

  const onSaveDraft = () => {
    setBanner(null);
    modeRef.current = 'draft';
    handleSubmit((v) => save.mutate(v))();
  };

  const onReview = () => {
    setBanner(null);
    modeRef.current = 'full';
    handleSubmit(async (v) => {
      try {
        await save.mutateAsync(v);
        setStep(2);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      } catch {
        /* handled in onError */
      }
    }, () => setBanner({ tone: 'error', text: 'Please correct the highlighted fields before continuing.' }))();
  };

  const sections = groupBySection(schema.fields);
  const values = getValues();

  return (
    <div className="max-w-4xl">
      <PageHeader
        title={step === 1 ? 'Application details' : 'Review & submit'}
        description={`${app.reference_number} · ${app.category.name} · AY ${app.academic_year.year_label}`}
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Applications', href: '/applications' },
          { label: app.reference_number, href: `/applications/${app.id}` },
          { label: step === 1 ? 'Edit draft' : 'Review' },
        ]}
      />
      <StepIndicator steps={['Category', 'Details', 'Review & submit']} current={step} />

      {banner && (
        <Callout tone={banner.tone} className="mb-4">
          {banner.text}
          {banner.failures && banner.failures.length > 0 && (
            <ul className="list-disc ml-4 mt-1">{banner.failures.map((f) => <li key={f}>{f}</li>)}</ul>
          )}
        </Callout>
      )}

      {step === 1 ? (
        <form onSubmit={(e) => { e.preventDefault(); onReview(); }} noValidate className="space-y-5">
          <Callout tone="warning" title="Prototype form — descriptive fields only">{schema.verification_note}</Callout>
          {sections.map(([section, fields]) => (
            <fieldset key={section} className="card p-4 sm:p-5">
              <legend className="sr-only">{section}</legend>
              <h2 className="text-sm font-semibold uppercase tracking-wider text-brand-text-muted mb-4" aria-hidden>{section}</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                {fields.map((f) => (
                  <FormFieldInput key={f.name} field={f} register={register} error={formState.errors[f.name] as never} />
                ))}
              </div>
            </fieldset>
          ))}
          <div className="sticky bottom-0 -mx-1 px-1 py-3 bg-brand-bg border-t border-brand-border flex flex-wrap items-center gap-2 justify-between">
            <span className="text-xs text-brand-text-muted" aria-live="polite">
              {save.isPending ? 'Saving…' : savedAt ? `Draft saved ${formatDateTime(savedAt)}` : `Last saved ${formatDateTime(app.updated_at)}`}
            </span>
            <div className="flex gap-2">
              <button type="button" className="btn-secondary" onClick={onSaveDraft} disabled={save.isPending}>
                <Save size={16} /> Save draft
              </button>
              <button type="submit" className="btn-primary" disabled={save.isPending}>
                Review <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </form>
      ) : (
        <div className="space-y-5">
          {sections.map(([section, fields]) => (
            <section key={section} className="card p-4 sm:p-5">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold uppercase tracking-wider text-brand-text-muted">{section}</h2>
                <button className="btn-ghost btn-sm" onClick={() => setStep(1)}><Pencil size={13} /> Edit</button>
              </div>
              <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
                {fields.map((f) => (
                  <div key={f.name} className={f.type === 'textarea' || f.type === 'checkbox' ? 'sm:col-span-2' : ''}>
                    <dt className="text-xs text-brand-text-muted">{f.label}</dt>
                    <dd className="text-sm text-ink-charcoal whitespace-pre-wrap break-words">
                      {f.type === 'checkbox' ? (values[f.name] ? 'Confirmed' : 'Not confirmed') : String(values[f.name] ?? '—') || '—'}
                    </dd>
                  </div>
                ))}
              </dl>
            </section>
          ))}
          <Callout tone="info">
            After submission the application can no longer be edited. The next step is payment, which in this prototype
            is a clearly labelled <strong>MOCK</strong> confirmation — no real transaction is made.
          </Callout>
          <div className="flex flex-wrap gap-2 justify-between">
            <button className="btn-secondary" onClick={() => setStep(1)}><ArrowLeft size={16} /> Back to edit</button>
            <button className="btn-primary" onClick={() => { setBanner(null); submit.mutate(); }} disabled={submit.isPending}>
              <Send size={16} /> {submit.isPending ? 'Submitting…' : 'Submit application'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
