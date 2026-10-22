import type { ReactNode } from 'react';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
}

export function EmptyState({ title, description, icon, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-12 h-12 rounded-full bg-ink-gray/30 flex items-center justify-center text-brand-text-muted mb-4">
        {icon || <Inbox size={24} />}
      </div>
      <h3 className="text-sm font-medium text-ink-charcoal">{title}</h3>
      {description && (
        <p className="text-sm text-brand-text-muted mt-1 max-w-sm">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
