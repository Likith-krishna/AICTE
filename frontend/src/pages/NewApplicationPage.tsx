import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowRight, Search, Route, ClipboardList, FileCheck2 } from 'lucide-react';
import { clsx } from 'clsx';
import { PageHeader } from '@/components/ui/PageHeader';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ErrorState } from '@/components/ui/ErrorState';
import { Callout } from '@/components/ui/Callout';
import { StepIndicator } from '@/components/applications/StepIndicator';
import { api, errorMessage } from '@/lib/api';
import { ROUTE_LABELS } from '@/lib/labels';
import type { AcademicYear, ApplicationCategory, ApplicationDetail } from '@/types/api';

const ROUTE_ICON: Record<string, JSX.Element> = {
  FULL: <Route size={14} />,
  SCRUTINY_ONLY: <ClipboardList size={14} />,
  SELF_DISCLOSURE: <FileCheck2 size={14} />,
};

export function NewApplicationPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [categoryId, setCategoryId] = useState('');
  const [yearId, setYearId] = useState('');
  const [filter, setFilter] = useState('');

  const categories = useQuery({
    queryKey: ['application-categories'],
    queryFn: () => api.get<ApplicationCategory[]>('/applications/categories'),
    staleTime: 5 * 60_000,
  });
  const years = useQuery({
    queryKey: ['academic-years'],
    queryFn: () => api.get<AcademicYear[]>('/applications/academic-years'),
    staleTime: 5 * 60_000,
  });

  const create = useMutation({
    mutationFn: () =>
      api.post<ApplicationDetail>('/applications', { category_id: categoryId, academic_year_id: yearId || years.data?.[0]?.id }),
    onSuccess: (app) => {
      qc.invalidateQueries({ queryKey: ['applications'] });
      qc.setQueryData(['application', app.id], app);
      navigate(`/applications/${app.id}/edit`);
    },
  });

  const grouped = useMemo(() => {
    const q = filter.trim().toLowerCase();
    const list = (categories.data ?? []).filter((c) => !q || c.name.toLowerCase().includes(q) || c.code.toLowerCase().includes(q));
    return [1, 2].map((pc) => [pc, list.filter((c) => c.processing_category === pc)] as const);
  }, [categories.data, filter]);

  const selected = categories.data?.find((c) => c.id === categoryId);
  const effectiveYear = yearId || years.data?.[0]?.id || '';

  return (
    <div className="max-w-5xl">
      <PageHeader
        title="New Application"
        description="Choose the application category and academic year. A draft is saved as soon as you continue."
        breadcrumbs={[{ label: 'Dashboard', href: '/' }, { label: 'Applications', href: '/applications' }, { label: 'New' }]}
      />
      <StepIndicator steps={['Category', 'Details', 'Review & submit']} current={0} />

      {categories.isLoading || years.isLoading ? (
        <div className="card"><LoadingSpinner /></div>
      ) : categories.error || years.error ? (
        <div className="card"><ErrorState error={categories.error || years.error} onRetry={() => { categories.refetch(); years.refetch(); }} /></div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
          <section className="card p-4 sm:p-5" aria-labelledby="cat-heading">
            <div className="flex flex-col sm:flex-row sm:items-center gap-3 justify-between mb-4">
              <h2 id="cat-heading" className="text-base">Application category</h2>
              <div className="relative sm:w-64">
                <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-brand-text-muted" />
                <input className="input pl-9" placeholder="Filter categories…" value={filter}
                       onChange={(e) => setFilter(e.target.value)} aria-label="Filter categories" />
              </div>
            </div>
            {grouped.map(([pc, items]) => items.length > 0 && (
              <fieldset key={pc} className="mb-5 last:mb-0">
                <legend className="text-xs font-semibold uppercase tracking-wider text-brand-text-muted mb-2">
                  Category {pc} · {pc === 1 ? 'processed per Public Notice period' : 'processed year-round'}
                  <span className="normal-case font-normal"> (APH Table 2.2)</span>
                </legend>
                <div className="grid gap-2 sm:grid-cols-2">
                  {items.map((c) => (
                    <label key={c.id}
                      className={clsx(
                        'flex items-start gap-3 rounded border p-3 cursor-pointer transition-colors',
                        c.id === categoryId ? 'border-ink-slate bg-ink-ivory ring-1 ring-ink-slate' : 'border-brand-border hover:border-ink-slate bg-white',
                      )}>
                      <input type="radio" name="category" value={c.id} checked={c.id === categoryId}
                             onChange={() => setCategoryId(c.id)} className="mt-1 accent-ink-slate" />
                      <span className="min-w-0">
                        <span className="block text-sm font-medium text-ink-charcoal">{c.name}</span>
                        <span className="mt-1 inline-flex items-center gap-1 text-xs text-brand-text-muted">
                          {ROUTE_ICON[c.route_type]} {ROUTE_LABELS[c.route_type] ?? c.route_type}
                        </span>
                      </span>
                    </label>
                  ))}
                </div>
              </fieldset>
            ))}
            {grouped.every(([, items]) => items.length === 0) && (
              <p className="text-sm text-brand-text-muted py-6 text-center">No categories match “{filter}”.</p>
            )}
          </section>

          <aside className="space-y-4">
            <div className="card p-4">
              <label htmlFor="ay" className="label">Academic year</label>
              <select id="ay" className="input" value={effectiveYear} onChange={(e) => setYearId(e.target.value)}>
                {years.data?.map((y) => (
                  <option key={y.id} value={y.id}>{y.year_label}{y.is_current ? ' (current)' : ''}</option>
                ))}
              </select>
              {selected && (
                <dl className="mt-4 text-sm space-y-2 border-t border-brand-border pt-3">
                  <div><dt className="text-xs text-brand-text-muted">Selected</dt><dd className="font-medium">{selected.name}</dd></div>
                  <div><dt className="text-xs text-brand-text-muted">Workflow route</dt><dd>{selected.workflow_name}</dd></div>
                  <div className="flex gap-2 flex-wrap pt-1">
                    {selected.requires_scrutiny && <span className="badge-neutral">Scrutiny</span>}
                    {selected.requires_evc && <span className="badge-neutral">EVC</span>}
                    {selected.requires_self_disclosure && <span className="badge-neutral">Self-disclosure</span>}
                    {selected.sac_shc_applicable === 'AA' && <span className="badge-neutral">SAC/SHC as applicable</span>}
                  </div>
                </dl>
              )}
              {create.error && <Callout tone="error" className="mt-3">{errorMessage(create.error)}</Callout>}
              <button className="btn-primary w-full mt-4" disabled={!categoryId || !effectiveYear || create.isPending}
                      onClick={() => create.mutate()}>
                {create.isPending ? 'Creating draft…' : <>Continue <ArrowRight size={16} /></>}
              </button>
            </div>
            <Callout tone="info" title="Routes follow APH Table 2.3">
              Each category is mapped to a verified workflow route. Fees, document lists and category eligibility
              criteria are not yet encoded and will not be requested here.
            </Callout>
          </aside>
        </div>
      )}
    </div>
  );
}
