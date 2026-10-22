import type { FieldError, UseFormRegister } from 'react-hook-form';
import { clsx } from 'clsx';
import type { FormField } from '@/types/api';

interface Props {
  field: FormField;
  register: UseFormRegister<Record<string, unknown>>;
  error?: FieldError;
  disabled?: boolean;
}

export function FormFieldInput({ field: f, register, error, disabled }: Props) {
  const id = `field-${f.name}`;
  const describedBy = [f.help ? `${id}-help` : null, error ? `${id}-error` : null].filter(Boolean).join(' ') || undefined;
  const common = {
    id,
    disabled,
    'aria-invalid': error ? true : undefined,
    'aria-describedby': describedBy,
    className: clsx('input', error && 'border-status-error focus:ring-status-error'),
  };

  if (f.type === 'checkbox') {
    return (
      <div className="sm:col-span-2">
        <label htmlFor={id} className="flex items-start gap-3 rounded border border-brand-border bg-ink-ivory/60 p-3 cursor-pointer">
          <input
            type="checkbox"
            id={id}
            disabled={disabled}
            aria-invalid={error ? true : undefined}
            aria-describedby={describedBy}
            className="mt-0.5 h-4 w-4 accent-ink-slate"
            {...register(f.name)}
          />
          <span className="text-sm text-ink-charcoal">
            {f.label}
            {f.required && <span className="text-status-error ml-0.5" aria-hidden>*</span>}
          </span>
        </label>
        {error && <p id={`${id}-error`} className="text-xs text-status-error mt-1">{error.message}</p>}
      </div>
    );
  }

  const wide = f.type === 'textarea';
  return (
    <div className={clsx(wide && 'sm:col-span-2')}>
      <label htmlFor={id} className="label">
        {f.label}
        {f.required && <span className="text-status-error ml-0.5" aria-hidden>*</span>}
        {f.required && <span className="sr-only"> (required)</span>}
      </label>
      {f.type === 'textarea' ? (
        <textarea rows={4} maxLength={f.max_length} {...common} {...register(f.name)} />
      ) : f.type === 'select' ? (
        <select {...common} {...register(f.name)}>
          <option value="">Select…</option>
          {f.options?.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      ) : f.type === 'integer' ? (
        <input type="number" inputMode="numeric" step={1} min={f.min} max={f.max} {...common}
               {...register(f.name, { valueAsNumber: true })} />
      ) : (
        <input type={f.type === 'tel' ? 'tel' : f.type === 'email' ? 'email' : 'text'} maxLength={f.max_length}
               autoComplete={f.type === 'email' ? 'email' : f.type === 'tel' ? 'tel' : undefined}
               {...common} {...register(f.name)} />
      )}
      {f.help && <p id={`${id}-help`} className="text-xs text-brand-text-muted mt-1">{f.help}</p>}
      {error && <p id={`${id}-error`} className="text-xs text-status-error mt-1">{error.message}</p>}
    </div>
  );
}
