import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Users, Plus, Search, ChevronLeft, ChevronRight, Shield, X } from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { api, ApiError } from '@/lib/api';
import type { PaginatedResponse, UserDetail, Role, Region, InstitutionDetail } from '@/types/api';
import { ROLE_LABELS } from '@/lib/labels';


export function UsersPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingUser, setEditingUser] = useState<UserDetail | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['users', page, search, roleFilter],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), page_size: '15' });
      if (search) params.set('search', search);
      if (roleFilter) params.set('role', roleFilter);
      return api.get<PaginatedResponse<UserDetail>>(`/users?${params}`);
    },
  });

  const { data: roles } = useQuery({
    queryKey: ['roles'],
    queryFn: () => api.get<Role[]>('/users/roles'),
  });

  const { data: regions } = useQuery({
    queryKey: ['regions'],
    queryFn: () => api.get<Region[]>('/institutions/regions'),
  });

  const { data: institutions } = useQuery({
    queryKey: ['institutions-all'],
    queryFn: () => api.get<PaginatedResponse<InstitutionDetail>>('/institutions?page_size=100'),
  });

  const deactivateMutation = useMutation({
    mutationFn: (userId: string) => api.patch<UserDetail>(`/users/${userId}/deactivate`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
  });

  const users = data?.items || [];
  const total = data?.total || 0;
  const pages = data?.pages || 0;

  return (
    <div>
      <PageHeader
        title="User Management"
        description="Manage system users, roles, and access permissions"
        breadcrumbs={[{ label: 'Dashboard', href: '/' }, { label: 'Users' }]}
        actions={
          <button className="btn-primary" onClick={() => { setEditingUser(null); setShowModal(true); }}>
            <Plus size={16} />
            Add User
          </button>
        }
      />

      {/* Filters */}
      <div className="card mb-4">
        <div className="flex flex-wrap items-center gap-3 p-4">
          <div className="relative flex-1 min-w-[200px]">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-brand-text-muted" />
            <input
              type="text"
              placeholder="Search by name or email..."
              className="input pl-9 w-full"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            />
          </div>
          <select
            className="input w-48"
            value={roleFilter}
            onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }}
          >
            <option value="">All Roles</option>
            {Object.entries(ROLE_LABELS).filter(([key]) => key !== 'system').map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
          <span className="text-xs text-brand-text-muted">{total} users</span>
        </div>
      </div>

      {/* Table */}
      <div className="card">
        {isLoading ? (
          <LoadingSpinner />
        ) : users.length === 0 ? (
          <EmptyState title="No users found" description="Adjust filters or add a new user." icon={<Users size={24} />} />
        ) : (
          <>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Institution</th>
                    <th>Status</th>
                    <th className="w-24">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id}>
                      <td className="font-medium">{u.full_name}</td>
                      <td className="text-brand-text-muted">{u.email}</td>
                      <td>
                        <span className="badge-info">{ROLE_LABELS[u.role] || u.role}</span>
                      </td>
                      <td className="text-brand-text-muted text-xs">
                        {u.institution_name || '—'}
                      </td>
                      <td>
                        <span className={u.is_active ? 'badge-success' : 'badge-error'}>
                          {u.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td>
                        <div className="flex items-center gap-1">
                          <button
                            className="btn text-xs px-2 py-1"
                            onClick={() => { setEditingUser(u); setShowModal(true); }}
                          >
                            Edit
                          </button>
                          {u.is_active && (
                            <button
                              className="btn text-xs px-2 py-1 text-red-600 hover:bg-red-50"
                              onClick={() => {
                                if (confirm(`Deactivate ${u.full_name}?`)) {
                                  deactivateMutation.mutate(u.id);
                                }
                              }}
                            >
                              Deactivate
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {pages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-ink-gray/30">
                <span className="text-xs text-brand-text-muted">
                  Page {page} of {pages}
                </span>
                <div className="flex items-center gap-1">
                  <button
                    className="btn px-2 py-1"
                    disabled={page <= 1}
                    onClick={() => setPage(page - 1)}
                  >
                    <ChevronLeft size={14} />
                  </button>
                  <button
                    className="btn px-2 py-1"
                    disabled={page >= pages}
                    onClick={() => setPage(page + 1)}
                  >
                    <ChevronRight size={14} />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Create/Edit Modal */}
      {showModal && (
        <UserModal
          user={editingUser}
          roles={roles || []}
          regions={regions || []}
          institutions={institutions?.items || []}
          onClose={() => setShowModal(false)}
          onSaved={() => {
            setShowModal(false);
            queryClient.invalidateQueries({ queryKey: ['users'] });
          }}
        />
      )}
    </div>
  );
}

function UserModal({
  user,
  roles,
  regions,
  institutions,
  onClose,
  onSaved,
}: {
  user: UserDetail | null;
  roles: Role[];
  regions: Region[];
  institutions: InstitutionDetail[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = !!user;
  const [form, setForm] = useState({
    email: user?.email || '',
    password: '',
    full_name: user?.full_name || '',
    role: user?.role || 'institution_applicant',
    institution_id: user?.institution_id || '',
    region_id: user?.region_id || '',
    is_active: user?.is_active ?? true,
  });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);

    try {
      if (isEdit) {
        const patch: Record<string, unknown> = {};
        if (form.full_name !== user.full_name) patch.full_name = form.full_name;
        if (form.role !== user.role) patch.role = form.role;
        if (form.is_active !== user.is_active) patch.is_active = form.is_active;
        if (form.institution_id !== (user.institution_id || ''))
          patch.institution_id = form.institution_id || null;
        if (form.region_id !== (user.region_id || ''))
          patch.region_id = form.region_id || null;
        await api.patch(`/users/${user.id}`, patch);
      } else {
        if (!form.email || !form.password || !form.full_name) {
          setError('Email, password, and name are required');
          setSubmitting(false);
          return;
        }
        await api.post('/users', {
          email: form.email,
          password: form.password,
          full_name: form.full_name,
          role: form.role,
          institution_id: form.institution_id || null,
          region_id: form.region_id || null,
        });
      }
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Operation failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-ink-gray/30">
          <h2 className="text-lg font-semibold text-ink-charcoal flex items-center gap-2">
            <Shield size={18} />
            {isEdit ? 'Edit User' : 'Create User'}
          </h2>
          <button onClick={onClose} className="text-brand-text-muted hover:text-ink-charcoal">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {error && (
            <div className="p-3 rounded bg-red-50 text-red-700 text-sm">{error}</div>
          )}

          <div>
            <label className="label">Full Name</label>
            <input
              className="input w-full"
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              required
            />
          </div>

          {!isEdit && (
            <>
              <div>
                <label className="label">Email</label>
                <input
                  type="email"
                  className="input w-full"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="label">Password</label>
                <input
                  type="password"
                  className="input w-full"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  minLength={8}
                  required
                />
              </div>
            </>
          )}

          <div>
            <label className="label">Role</label>
            <select
              className="input w-full"
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
            >
              {roles.map((r) => (
                <option key={r.name} value={r.name}>{r.display_name}</option>
              ))}
            </select>
          </div>

          {(form.role === 'institution_applicant' || form.role === 'institution_signatory') && (
            <div>
              <label className="label" htmlFor="user-institution">Institution</label>
              <select
                id="user-institution"
                className="input w-full"
                value={form.institution_id}
                onChange={(e) => {
                  const inst = institutions.find((i) => i.id === e.target.value);
                  setForm({ ...form, institution_id: e.target.value, region_id: inst?.region_id || form.region_id });
                }}
              >
                <option value="">— None —</option>
                {institutions.map((i) => (
                  <option key={i.id} value={i.id}>{i.name} ({i.pid})</option>
                ))}
              </select>
              <p className="text-xs text-brand-text-muted mt-1">Institution users can only see this institution's records.</p>
            </div>
          )}

          <div>
            <label className="label">Region</label>
            <select
              className="input w-full"
              value={form.region_id}
              onChange={(e) => setForm({ ...form, region_id: e.target.value })}
            >
              <option value="">— None —</option>
              {regions.map((r) => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
          </div>

          {isEdit && (
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_active"
                checked={form.is_active}
                onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
              />
              <label htmlFor="is_active" className="text-sm text-ink-charcoal">Active</label>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? 'Saving...' : isEdit ? 'Update' : 'Create User'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
