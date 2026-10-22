import { useQuery } from '@tanstack/react-query';
import { FileText, Shield, Bell, Clock } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { PageHeader } from '@/components/ui/PageHeader';
import { StatsCard } from '@/components/ui/StatsCard';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import type { DashboardStats } from '@/types/api';

const STAGE_LABELS: Record<string, string> = {
  DRAFT: 'Draft',
  SUBMITTED: 'Submitted',
  UNDER_SCRUTINY: 'Under Scrutiny',
  SCRUTINY_CLEAR: 'Scrutiny Clear',
  DEFICIENCY_NOTED: 'Deficiency',
  EVC_QUEUED: 'EVC Queued',
  EVC_IN_PROGRESS: 'EVC In Progress',
  PLACED_BEFORE_EC: 'Before EC',
  APPROVED: 'Approved',
  REJECTED: 'Rejected',
};

const PIE_COLORS = ['#6D8196', '#4A4A4A', '#CBCBCB', '#8FAABB', '#5A6F82', '#7A9BB0'];

export function DashboardPage() {
  const { user } = useAuth();
  const { data, isLoading } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.get('/dashboard/stats'),
  });

  if (isLoading) return <LoadingSpinner />;

  const stageData = Object.entries(data?.applications_by_stage || {}).map(([stage, count]) => ({
    name: STAGE_LABELS[stage] || stage.replace(/_/g, ' '),
    count,
  }));

  const pieData = stageData.filter(d => d.count > 0);

  return (
    <div>
      <PageHeader
        title={`Welcome, ${user?.full_name}`}
        description="Overview of your workflow status and pending actions"
      />

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatsCard
          title="Total Applications"
          value={data?.total_applications ?? 0}
          icon={<FileText size={20} />}
        />
        <StatsCard
          title="Pending Compliance"
          value={data?.pending_compliance ?? 0}
          icon={<Shield size={20} />}
        />
        <StatsCard
          title="Unread Notifications"
          value={data?.unread_notifications ?? 0}
          icon={<Bell size={20} />}
        />
        <StatsCard
          title="Active Stages"
          value={stageData.filter(s => s.count > 0).length}
          icon={<Clock size={20} />}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="card p-6">
          <h3 className="text-sm font-semibold text-ink-charcoal mb-4">Applications by Stage</h3>
          {stageData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={stageData} margin={{ top: 5, right: 5, bottom: 40, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#CBCBCB" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-35} textAnchor="end" height={60} />
                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ border: '1px solid #CBCBCB', borderRadius: '6px', fontSize: '12px' }}
                />
                <Bar dataKey="count" fill="#6D8196" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[280px] text-brand-text-muted text-sm">
              No application data yet
            </div>
          )}
        </div>

        <div className="card p-6">
          <h3 className="text-sm font-semibold text-ink-charcoal mb-4">Status Distribution</h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="count"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  labelLine={false}
                  fontSize={11}
                >
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[280px] text-brand-text-muted text-sm">
              No data to display
            </div>
          )}
        </div>
      </div>

      {/* Recent Activity Placeholder */}
      <div className="card p-6">
        <h3 className="text-sm font-semibold text-ink-charcoal mb-4">Recent Activity</h3>
        <div className="text-sm text-brand-text-muted py-8 text-center">
          Activity feed will populate as applications progress through the workflow.
        </div>
      </div>
    </div>
  );
}
