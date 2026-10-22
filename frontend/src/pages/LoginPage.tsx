import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/lib/auth';
import { Shield, AlertCircle } from 'lucide-react';

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  if (isAuthenticated) {
    navigate('/', { replace: true });
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-brand-bg px-4">
      <div className="w-full max-w-md">
        {/* Logo Section */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-xl bg-ink-slate text-white mb-4">
            <Shield size={32} />
          </div>
          <h1 className="text-2xl font-bold text-ink-charcoal">AICTE FlowGuard</h1>
          <p className="text-sm text-brand-text-muted mt-1">
            Approval Workflow Automation Platform
          </p>
        </div>

        {/* Login Card */}
        <div className="card p-8">
          <h2 className="text-lg font-semibold text-ink-charcoal mb-6">Sign in to your account</h2>

          {error && (
            <div className="flex items-center gap-2 p-3 mb-4 rounded bg-status-error-bg text-status-error text-sm">
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="label">Email address</label>
              <input
                id="email"
                type="email"
                className="input"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                autoComplete="email"
              />
            </div>
            <div>
              <label htmlFor="password" className="label">Password</label>
              <input
                id="password"
                type="password"
                className="input"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
                autoComplete="current-password"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full"
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          {/* Demo Credentials */}
          <div className="mt-6 p-4 rounded bg-ink-ivory/50 border border-brand-border">
            <p className="text-xs font-medium text-ink-charcoal mb-2">Demo Credentials</p>
            <div className="space-y-1 text-xs text-brand-text-muted">
              <p><span className="font-mono">admin@flowguard.gov.in</span> — System Admin</p>
              <p><span className="font-mono">institution@demo.ac.in</span> — Institution</p>
              <p><span className="font-mono">scrutiny@flowguard.gov.in</span> — Scrutiny Officer</p>
              <p><span className="font-mono">authority@flowguard.gov.in</span> — Authority</p>
              <p className="mt-1">Password: <span className="font-mono">Demo@123</span></p>
            </div>
          </div>
        </div>

        <p className="text-center text-xs text-brand-text-muted mt-6">
          SIH26262 — Smart India Hackathon 2026
        </p>
      </div>
    </div>
  );
}
