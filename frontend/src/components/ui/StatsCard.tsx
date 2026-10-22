import type { ReactNode } from 'react';

interface StatsCardProps {
  title: string;
  value: string | number;
  icon: ReactNode;
  trend?: string;
  trendUp?: boolean;
}

export function StatsCard({ title, value, icon, trend, trendUp }: StatsCardProps) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-brand-text-muted">{title}</p>
          <p className="text-2xl font-bold text-ink-charcoal mt-1">{value}</p>
          {trend && (
            <p className={`text-xs mt-1 ${trendUp ? 'text-status-success' : 'text-status-error'}`}>
              {trend}
            </p>
          )}
        </div>
        <div className="w-10 h-10 rounded bg-ink-slate/10 flex items-center justify-center text-ink-slate">
          {icon}
        </div>
      </div>
    </div>
  );
}
