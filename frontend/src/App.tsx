import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/lib/auth';
import { AppShell } from '@/components/layout/AppShell';
import { LoginPage } from '@/pages/LoginPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { ApplicationsPage } from '@/pages/ApplicationsPage';
import { PlaceholderPage } from '@/pages/PlaceholderPage';
import { UsersPage } from '@/pages/UsersPage';
import { InstitutionsPage } from '@/pages/InstitutionsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<AppShell />}>
              <Route index element={<DashboardPage />} />
              <Route path="applications" element={<ApplicationsPage />} />
              <Route path="institutions" element={<InstitutionsPage />} />
              <Route path="scrutiny" element={<PlaceholderPage title="Scrutiny" description="Review applications and record observations" />} />
              <Route path="compliance" element={<PlaceholderPage title="Compliance" description="Track compliance obligations and evidence submissions" />} />
              <Route path="notifications" element={<PlaceholderPage title="Notifications" description="View your notifications and alerts" />} />
              <Route path="reports" element={<PlaceholderPage title="Reports" description="Operational analytics and workflow metrics" />} />
              <Route path="rules" element={<PlaceholderPage title="Regulatory Rules" description="Manage the regulatory rule registry and lifecycle" />} />
              <Route path="users" element={<UsersPage />} />
              <Route path="audit" element={<PlaceholderPage title="Audit Log" description="View system audit trail and historical records" />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
