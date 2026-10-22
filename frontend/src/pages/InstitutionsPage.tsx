import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Building2, Search, ChevronLeft, ChevronRight, MapPin, Users as UsersIcon } from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { api } from '@/lib/api';
import type { PaginatedResponse, InstitutionDetail, Region } from '@/types/api';

export function InstitutionsPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [regionFilter, setRegionFilter] = useState('');
  const [selectedInst, setSelectedInst] = useState<InstitutionDetail | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['institutions', page, search, regionFilter],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), page_size: '15' });
      if (search) params.set('search', search);
      if (regionFilter) params.set('region_id', regionFilter);
      return api.get<PaginatedResponse<InstitutionDetail>>(`/institutions?${params}`);
    },
  });

  const { data: regions } = useQuery({
    queryKey: ['regions'],
    queryFn: () => api.get<Region[]>('/institutions/regions'),
  });

  const institutions = data?.items || [];
  const total = data?.total || 0;
  const pages = data?.pages || 0;

  return (
    <div>
      <PageHeader
        title="Institutions"
        description="View and manage AICTE-registered institutions"
        breadcrumbs={[{ label: 'Dashboard', href: '/' }, { label: 'Institutions' }]}
      />

      {/* Filters */}
      <div className="card mb-4">
        <div className="flex flex-wrap items-center gap-3 p-4">
          <div className="relative flex-1 min-w-[200px]">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-brand-text-muted" />
            <input
              type="text"
              placeholder="Search institutions..."
              className="input pl-9 w-full"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            />
          </div>
          <select
            className="input w-48"
            value={regionFilter}
            onChange={(e) => { setRegionFilter(e.target.value); setPage(1); }}
          >
            <option value="">All Regions</option>
            {(regions || []).map((r) => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
          <span className="text-xs text-brand-text-muted">{total} institutions</span>
        </div>
      </div>

      {/* Grid / List */}
      <div className="card">
        {isLoading ? (
          <LoadingSpinner />
        ) : institutions.length === 0 ? (
          <EmptyState
            title="No institutions found"
            description="Adjust your search or filters."
            icon={<Building2 size={24} />}
          />
        ) : (
          <>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>PID</th>
                    <th>Institution Name</th>
                    <th>Type</th>
                    <th>Region</th>
                    <th>Location</th>
                    <th>Users</th>
                  </tr>
                </thead>
                <tbody>
                  {institutions.map((inst) => (
                    <tr
                      key={inst.id}
                      className="cursor-pointer hover:bg-ink-ivory/60"
                      onClick={() => setSelectedInst(inst)}
                    >
                      <td className="font-mono text-xs">{inst.pid}</td>
                      <td className="font-medium">{inst.name}</td>
                      <td>
                        <span className="badge-info capitalize">{inst.institution_type}</span>
                      </td>
                      <td className="text-brand-text-muted text-xs">{inst.region_name || '—'}</td>
                      <td className="text-brand-text-muted text-xs">
                        <span className="flex items-center gap-1">
                          <MapPin size={12} /> {inst.city}, {inst.state}
                        </span>
                      </td>
                      <td>
                        <span className="flex items-center gap-1 text-xs text-brand-text-muted">
                          <UsersIcon size={12} /> {inst.user_count}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {pages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-ink-gray/30">
                <span className="text-xs text-brand-text-muted">Page {page} of {pages}</span>
                <div className="flex items-center gap-1">
                  <button className="btn px-2 py-1" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                    <ChevronLeft size={14} />
                  </button>
                  <button className="btn px-2 py-1" disabled={page >= pages} onClick={() => setPage(page + 1)}>
                    <ChevronRight size={14} />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Detail Panel */}
      {selectedInst && (
        <InstitutionDetailPanel inst={selectedInst} onClose={() => setSelectedInst(null)} />
      )}
    </div>
  );
}

function InstitutionDetailPanel({ inst, onClose }: { inst: InstitutionDetail; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-ink-gray/30">
          <h2 className="text-lg font-semibold text-ink-charcoal flex items-center gap-2">
            <Building2 size={18} />
            {inst.name}
          </h2>
          <button onClick={onClose} className="text-brand-text-muted hover:text-ink-charcoal text-sm">
            Close
          </button>
        </div>
        <div className="p-4 space-y-3 text-sm">
          <InfoRow label="PID" value={inst.pid} />
          <InfoRow label="Type" value={inst.institution_type} />
          <InfoRow label="Region" value={inst.region_name || '—'} />
          <InfoRow label="State" value={inst.state} />
          <InfoRow label="City" value={inst.city} />
          {inst.address && <InfoRow label="Address" value={inst.address} />}
          {inst.pincode && <InfoRow label="Pincode" value={inst.pincode} />}
          {inst.contact_email && <InfoRow label="Email" value={inst.contact_email} />}
          {inst.contact_phone && <InfoRow label="Phone" value={inst.contact_phone} />}
          {inst.established_year && <InfoRow label="Established" value={String(inst.established_year)} />}
          {inst.website && <InfoRow label="Website" value={inst.website} />}
          <InfoRow label="Users" value={String(inst.user_count)} />
          <InfoRow label="Created" value={new Date(inst.created_at).toLocaleDateString()} />
        </div>
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-brand-text-muted">{label}</span>
      <span className="text-ink-charcoal font-medium">{value}</span>
    </div>
  );
}
