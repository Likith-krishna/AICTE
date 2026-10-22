/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          charcoal: '#4A4A4A',
          gray: '#CBCBCB',
          ivory: '#FFFFE3',
          slate: '#6D8196',
        },
        brand: {
          bg: 'var(--color-bg)',
          surface: 'var(--color-surface)',
          'surface-elevated': 'var(--color-surface-elevated)',
          text: 'var(--color-text)',
          'text-muted': 'var(--color-text-muted)',
          border: 'var(--color-border)',
          primary: 'var(--color-primary)',
          'primary-hover': 'var(--color-primary-hover)',
          'primary-text': 'var(--color-primary-text)',
        },
        status: {
          success: '#2E7D4F',
          'success-bg': '#E8F5E9',
          warning: '#C67700',
          'warning-bg': '#FFF8E1',
          error: '#C62828',
          'error-bg': '#FFEBEE',
          info: '#1565C0',
          'info-bg': '#E3F2FD',
        },
      },
      fontFamily: {
        sans: ['"Inter"', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      boxShadow: {
        'card': '0 1px 3px rgba(74, 74, 74, 0.08), 0 1px 2px rgba(74, 74, 74, 0.06)',
        'card-hover': '0 4px 6px rgba(74, 74, 74, 0.1), 0 2px 4px rgba(74, 74, 74, 0.06)',
        'elevated': '0 10px 15px rgba(74, 74, 74, 0.1), 0 4px 6px rgba(74, 74, 74, 0.05)',
      },
      borderRadius: {
        DEFAULT: '6px',
      },
    },
  },
  plugins: [],
}
