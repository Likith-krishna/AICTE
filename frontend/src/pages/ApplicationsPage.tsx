import { PageHeader } from '@/components/ui/PageHeader';
import { EmptyState } from '@/components/ui/EmptyState';
import { FileText, Plus } from 'lucide-react';
import { useAuth } from '@/lib/auth';

export function ApplicationsPage() {
  const { user } = useAuth();
  const canCreate = user?.role === 'institution_applicant';

  return (
    <div>
      <PageHeader
        title="Applications"
        description="Manage institutional applications and track their progress"
        breadcrumbs={[{ label: 'Dashboard', href: '/' }, { label: 'Applications' }]}
        actions={
          canCreate ? (
            <button className="btn-primary">
              <Plus size={16} />
              New Application
            </button>
          ) : undefined
        }
      />

      <div className="card">
        <EmptyState
          title="No applications yet"
          description="Applications will appear here once created. Use the button above to start a new application."
          icon={<FileText size={24} />}
        />
      </div>
    </div>
  );
}
