import { ShieldOff, WifiOff, AlertCircle, RotateCw } from 'lucide-react';
import { ApiError } from '@/lib/api';

/** Full-card error with permission-denied / not-found / network variants and a retry action. */
export function ErrorState({ error, onRetry, title }: { error: unknown; onRetry?: () => void; title?: string }) {
  const status = error instanceof ApiError ? error.status : undefined;
  const message = error instanceof Error ? error.message : 'Unexpected error';
  const denied = status === 403;
  const notFound = status === 404;
  const network = error instanceof ApiError && error.code === 'NETWORK';
  const Icon = denied ? ShieldOff : network ? WifiOff : AlertCircle;
  const heading =
    title ?? (denied ? 'Access denied' : notFound ? 'Not found' : network ? 'Connection problem' : 'Could not load data');

  return (
    <div className="flex flex-col items-center justify-center py-14 px-4 text-center" role="alert">
      <div className="w-12 h-12 rounded-full bg-status-error-bg flex items-center justify-center text-status-error mb-4">
        <Icon size={22} />
      </div>
      <h3 className="text-sm font-semibold text-ink-charcoal">{heading}</h3>
      <p className="text-sm text-brand-text-muted mt-1 max-w-md">{message}</p>
      {onRetry && !denied && !notFound && (
        <button className="btn-secondary btn-sm mt-4" onClick={onRetry}>
          <RotateCw size={14} /> Try again
        </button>
      )}
    </div>
  );
}
