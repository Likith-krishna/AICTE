export function LoadingSpinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizeClass = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-8 h-8' }[size];

  return (
    <div className="flex items-center justify-center p-8">
      <div
        className={`${sizeClass} border-2 border-ink-gray border-t-ink-slate rounded-full animate-spin`}
      />
    </div>
  );
}
