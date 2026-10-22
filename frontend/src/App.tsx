import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/lib/auth';
import { AppShell } from '@/components/layout/AppShell';
import { LoginPage } from '@/pages/LoginPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { ApplicationsPage } from '@/pages/ApplicationsPage';
import { ApplicationDetailPage } from '@/pages/ApplicationDetailPage';
import { NewApplicationPage } from '@/pages/NewApplicationPage';
import { ApplicationFormPage } from '@/pages/ApplicationFormPage';
import { PlaceholderPage } from '@/pages/PlaceholderPage';
import { UsersPage } from '@/pages/UsersPage';
import { InstitutionsPage } from '@/pages/InstitutionsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      // Do not retry authorisation/validation failures; retry transient errors once.
      retry: (count, err) => {
        const status = (err as { status?: number }).status ?? 0;
        return status >= 500 || status === 0 ? count < 1 : false;
      },
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
              <Route path="applications/new" element={<NewApplicationPage />} />
              <Route path="applications/:id" element={<ApplicationDetailPage />} />
              <Route path="applications/:id/edit" element={<ApplicationFormPage />} />
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
