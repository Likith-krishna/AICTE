import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import {
  createColumnHelper, flexRender, getCoreRowModel, useReactTable, type ColumnDef, type SortingState,
} from '@tanstack/react-table';
import { FileText, Plus, Search, ChevronLeft, ChevronRight, ArrowUpDown, ArrowUp, ArrowDown, BellDot } from 'lucide-react';
import { clsx } from 'clsx';
import { PageHeader } from '@/components/ui/PageHeader';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ErrorState } from '@/components/ui/ErrorState';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { useAuth } from '@/lib/auth';
import { api } from '@/lib/api';
import { formatDate, ROUTE_LABELS } from '@/lib/labels';
import type { AcademicYear, ApplicationCategory, ApplicationListItem, PaginatedResponse } from '@/types/api';

const STAGE_FILTERS: [string, string][] = [
  ['DRAFT', 'Draft'], ['SUBMITTED', 'Submitted (awaiting payment)'], ['UNDER_SCRUTINY', 'Under scrutiny'],
  ['AWAITING_INSTITUTION_RESPONSE', 'Awaiting institution response'], ['RE_SCRUTINY', 'Re-scrutiny'],
  ['EVC_QUEUED', 'EVC queued'], ['EVC_SCHEDULED', 'EVC scheduled'], ['REPORT_SUBMITTED', 'EVC report submitted'],
  ['PLACED_BEFORE_EC', 'Placed before EC'], ['EC_DECISION', 'EC decision'], ['SELF_DISCLOSURE_VALIDATED', 'Self-disclosure review'],
  ['DEFICIENCY_FREE', 'Deficiency free'], ['APPROVED', 'Approved'], ['APPROVED_WITH_CONDITIONS', 'Approved with conditions'],
  ['REJECTED', 'Rejected'], ['SAC_HEARING', 'SAC hearing'], ['FINAL_REJECTION', 'Final rejection'], ['EOA_ISSUED', 'EoA issued'],
];

const PAGE_SIZE = 15;
const col = createColumnHelper<ApplicationListItem>();

function useDebounced<T>(value: T, ms = 300): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

export function ApplicationsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const isInstitution = user?.role === 'institution_applicant' || user?.role === 'institution_signatory';
  const canCreate = user?.role === 'institution_applicant';

  // Filters live in the URL so views are shareable and survive reloads.
  const [params, setParams] = useSearchParams();
  const page = Number(params.get('page') || 1);
  const stage = params.get('stage') || '';
  const categoryId = params.get('category_id') || '';
  const yearId = params.get('academic_year_id') || '';
  const mine = params.get('needs_my_action') === 'true';
  const [searchInput, setSearchInput] = useState(params.get('search') || '');
  const search = useDebounced(searchInput);
  const [sorting, setSorting] = useState<SortingState>([{ id: 'updated_at', desc: true }]);

  const update = (patch: Record<string, string | null>) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) (v ? next.set(k, v) : next.delete(k));
    if (!('page' in patch)) next.delete('page');
    setParams(next, { replace: true });
  };

  useEffect(() => {
    if ((params.get('search') || '') !== search) update({ search: search || null });
  }, [search]); // eslint-disable-line react-hooks/exhaustive-deps

  const sort = sorting[0] ?? { id: 'updated_at', desc: true };
  const query = useQuery({
    queryKey: ['applications', { page, stage, categoryId, yearId, mine, search, sort }],
    queryFn: () => {
      const q = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE), sort_by: sort.id, sort_dir: sort.desc ? 'desc' : 'asc' });
      if (search) q.set('search', search);
      if (stage) q.set('stage', stage);
      if (categoryId) q.set('category_id', categoryId);
      if (yearId) q.set('academic_year_id', yearId);
      if (mine) q.set('needs_my_action', 'true');
      return api.get<PaginatedResponse<ApplicationListItem>>(`/applications?${q}`);
    },
    placeholderData: keepPreviousData,
  });
  const categories = useQuery({ queryKey: ['application-categories'], queryFn: () => api.get<ApplicationCategory[]>('/applications/categories'), staleTime: 300_000 });
  const years = useQuery({ queryKey: ['academic-years'], queryFn: () => api.get<AcademicYear[]>('/applications/academic-years'), staleTime: 300_000 });

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const columns = useMemo<ColumnDef<ApplicationListItem, any>[]>(() => [
    col.accessor('reference_number', {
      header: 'Reference',
      cell: (c) => (
        <span className="flex items-center gap-2">
          {c.row.original.needs_my_action && <span title="Needs your action" className="w-2 h-2 rounded-full bg-ink-slate shrink-0" aria-label="Needs your action" />}
          <Link to={`/applications/${c.row.original.id}`} className="font-mono text-[13px] font-medium">{c.getValue()}</Link>
        </span>
      ),
    }),
    ...(isInstitution ? [] : [col.accessor('institution_name', { header: 'Institution', enableSorting: false,
      cell: (c) => <span className="block max-w-[220px] truncate" title={c.getValue()}>{c.getValue()}</span> })]),
    col.accessor('category_name', {
      header: 'Category', enableSorting: false,
      cell: (c) => (
        <div className="max-w-[240px]">
          <div className="truncate" title={c.getValue()}>{c.getValue()}</div>
          <div className="text-xs text-brand-text-muted">{ROUTE_LABELS[c.row.original.route_type] ?? c.row.original.route_type} · AY {c.row.original.academic_year}</div>
        </div>
      ),
    }),
    col.accessor('stage', {
      header: 'Stage',
      cell: (c) => (
        <div className="flex flex-col items-start gap-1">
          <StatusBadge status={c.getValue()} label={c.row.original.stage_label} />
          {c.row.original.status !== 'ACTIVE' && <span className="text-[11px] text-brand-text-muted uppercase">{c.row.original.status}</span>}
        </div>
      ),
    }),
    ...(isInstitution ? [] : [col.accessor('region_code', { header: 'Region', enableSorting: false, cell: (c) => c.getValue() ?? '—' })]),
    col.accessor('submitted_at', { header: 'Submitted', cell: (c) => <span className="whitespace-nowrap">{formatDate(c.getValue())}</span> }),
    col.accessor('updated_at', { header: 'Last activity', cell: (c) => <span className="whitespace-nowrap">{formatDate(c.getValue())}</span> }),
  ], [isInstitution]);

  const data = query.data;
  const table = useReactTable({
    data: data?.items ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualSorting: true,
    manualPagination: true,
    pageCount: data?.pages ?? 0,
    state: { sorting },
    onSortingChange: (u) => { setSorting(u); update({ page: null }); },
    enableSortingRemoval: false,
  });

  const filtersActive = !!(stage || categoryId || yearId || mine || search);

  return (
    <div>
      <PageHeader
        title="Applications"
        description={isInstitution ? "Your institution's applications and their workflow status" : 'Applications within your access scope'}
        breadcrumbs={[{ label: 'Dashboard', href: '/' }, { label: 'Applications' }]}
        actions={canCreate ? (
          <button className="btn-primary" onClick={() => navigate('/applications/new')}><Plus size={16} /> New Application</button>
        ) : undefined}
      />

      <div className="card mb-4">
        <div className="flex flex-wrap items-center gap-3 p-4">
          <div className="relative flex-1 min-w-[200px]">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-brand-text-muted" />
            <input type="search" className="input pl-9" placeholder={isInstitution ? 'Search by reference…' : 'Search by reference or institution…'}
                   value={searchInput} onChange={(e) => setSearchInput(e.target.value)} aria-label="Search applications" />
          </div>
          <select className="input w-full sm:w-52" value={stage} onChange={(e) => update({ stage: e.target.value || null })} aria-label="Filter by stage">
            <option value="">All stages</option>
            {STAGE_FILTERS.filter(([s]) => isInstitution || s !== 'DRAFT').map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <select className="input w-full sm:w-56" value={categoryId} onChange={(e) => update({ category_id: e.target.value || null })} aria-label="Filter by category">
            <option value="">All categories</option>
            {categories.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <select className="input w-full sm:w-36" value={yearId} onChange={(e) => update({ academic_year_id: e.target.value || null })} aria-label="Filter by academic year">
            <option value="">All years</option>
            {years.data?.map((y) => <option key={y.id} value={y.id}>{y.year_label}</option>)}
          </select>
          <button
            type="button"
            aria-pressed={mine}
            onClick={() => update({ needs_my_action: mine ? null : 'true' })}
            className={clsx('btn btn-sm border', mine ? 'bg-ink-slate text-white border-ink-slate' : 'bg-white border-brand-border text-ink-charcoal hover:bg-gray-50')}
          >
            <BellDot size={14} /> Needs my action
          </button>
          {filtersActive && (
            <button className="btn-ghost btn-sm" onClick={() => { setSearchInput(''); setParams(new URLSearchParams(), { replace: true }); }}>
              Clear filters
            </button>
          )}
        </div>
      </div>

      <div className="card">
        {query.isLoading ? (
          <LoadingSpinner />
        ) : query.error ? (
          <ErrorState error={query.error} onRetry={() => query.refetch()} />
        ) : !data || data.items.length === 0 ? (
          <EmptyState
            title={filtersActive ? 'No applications match these filters' : 'No applications yet'}
            description={filtersActive ? 'Try clearing or adjusting the filters.'
              : canCreate ? 'Start a new application to begin the approval workflow.'
              : 'Applications submitted within your scope will appear here.'}
            icon={<FileText size={24} />}
            action={canCreate && !filtersActive ? <button className="btn-primary" onClick={() => navigate('/applications/new')}><Plus size={16} /> New Application</button> : undefined}
          />
        ) : (
          <>
            <div className={clsx('table-container', query.isFetching && 'opacity-70 transition-opacity')}>
              <table>
                <thead>
                  {table.getHeaderGroups().map((hg) => (
                    <tr key={hg.id}>
                      {hg.headers.map((h) => {
                        const sorted = h.column.getIsSorted();
                        return (
                          <th key={h.id} aria-sort={sorted ? (sorted === 'desc' ? 'descending' : 'ascending') : undefined}>
                            {h.column.getCanSort() ? (
                              <button className="inline-flex items-center gap-1 uppercase tracking-wider hover:text-ink-charcoal"
                                      onClick={h.column.getToggleSortingHandler()}>
                                {flexRender(h.column.columnDef.header, h.getContext())}
                                {sorted === 'asc' ? <ArrowUp size={12} /> : sorted === 'desc' ? <ArrowDown size={12} /> : <ArrowUpDown size={12} className="opacity-40" />}
                              </button>
                            ) : flexRender(h.column.columnDef.header, h.getContext())}
                          </th>
                        );
                      })}
                    </tr>
                  ))}
                </thead>
                <tbody>
                  {table.getRowModel().rows.map((r) => (
                    <tr key={r.id} className="cursor-pointer" onClick={(e) => {
                      if ((e.target as HTMLElement).closest('a,button')) return;
                      navigate(`/applications/${r.original.id}`);
                    }}>
                      {r.getVisibleCells().map((c) => <td key={c.id}>{flexRender(c.column.columnDef.cell, c.getContext())}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-t border-brand-border">
              <span className="text-xs text-brand-text-muted">
                Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, data.total)} of {data.total}
              </span>
              <div className="flex items-center gap-1">
                <button className="btn-secondary btn-sm" disabled={page <= 1} onClick={() => update({ page: String(page - 1) })} aria-label="Previous page">
                  <ChevronLeft size={14} />
                </button>
                <span className="text-xs px-2">Page {page} of {Math.max(1, data.pages)}</span>
                <button className="btn-secondary btn-sm" disabled={page >= data.pages} onClick={() => update({ page: String(page + 1) })} aria-label="Next page">
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
