import { PageHeader } from '@/components/ui/PageHeader';
import { Construction } from 'lucide-react';

interface PlaceholderPageProps {
  title: string;
  description?: string;
}

export function PlaceholderPage({ title, description }: PlaceholderPageProps) {
  return (
    <div>
      <PageHeader
        title={title}
        description={description}
        breadcrumbs={[{ label: 'Dashboard', href: '/' }, { label: title }]}
      />
      <div className="card p-12 text-center">
        <Construction size={40} className="mx-auto text-ink-slate mb-4" />
        <h3 className="text-lg font-medium text-ink-charcoal">Under Development</h3>
        <p className="text-sm text-brand-text-muted mt-2 max-w-md mx-auto">
          The {title} module is part of the next implementation phase.
          It will be connected to the backend and fully functional.
        </p>
      </div>
    </div>
  );
}
