import { useEffect, useRef, type ReactNode } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  icon?: ReactNode;
  size?: 'md' | 'lg';
}

/** Accessible dialog: focus moves inside on open, Escape closes, backdrop click closes. */
export function Modal({ title, onClose, children, footer, icon, size = 'md' }: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    const first = panelRef.current?.querySelector<HTMLElement>('textarea, input, select, button:not([data-close])');
    (first ?? panelRef.current)?.focus();
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      prev?.focus();
    };
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-ink-charcoal/40 p-0 sm:p-4"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        tabIndex={-1}
        className={`bg-brand-surface w-full ${size === 'lg' ? 'sm:max-w-2xl' : 'sm:max-w-lg'} rounded-t-lg sm:rounded-lg shadow-elevated max-h-[92vh] flex flex-col focus:outline-none`}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-brand-border">
          <h2 id="modal-title" className="text-base font-semibold text-ink-charcoal flex items-center gap-2">
            {icon}
            {title}
          </h2>
          <button data-close onClick={onClose} className="btn-ghost p-1.5" aria-label="Close dialog">
            <X size={18} />
          </button>
        </div>
        <div className="px-5 py-4 overflow-y-auto">{children}</div>
        {footer && <div className="px-5 py-3 border-t border-brand-border flex justify-end gap-2">{footer}</div>}
      </div>
    </div>
  );
}
