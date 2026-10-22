import { defineConfig, devices } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Dedicated SQLite file for E2E runs only — never the developer's backend/flowguard.db,
// never Supabase. e2e_bootstrap.py refuses to run unless DATABASE_URL points here.
const backendDir = path.resolve(__dirname, '../backend');
const pythonBin = process.platform === 'win32'
  ? path.join(backendDir, '.venv', 'Scripts', 'python.exe')
  : path.join(backendDir, '.venv', 'bin', 'python');
const e2eDbPath = path.join(backendDir, '.e2e-test.db').replace(/\\/g, '/');

const backendEnv = {
  ...process.env,
  DATABASE_URL: `sqlite+aiosqlite:///${e2eDbPath}`,
  DATABASE_URL_SYNC: `sqlite:///${e2eDbPath}`,
  ENVIRONMENT: 'test',
  DEBUG: 'false',
};

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: 'list',
  timeout: 30_000,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  // Both servers are started fresh for every run (reuseExistingServer: false) so
  // the E2E database and app state are always deterministic. This will fail to
  // bind if a manual `npm run dev` / backend dev server is already using these
  // same ports (8000 / 5173) — stop those first.
  webServer: [
    {
      command: `"${pythonBin}" e2e_bootstrap.py && "${pythonBin}" -m uvicorn app.main:app --host 127.0.0.1 --port 8000`,
      cwd: backendDir,
      url: 'http://127.0.0.1:8000/api/health',
      reuseExistingServer: false,
      env: backendEnv,
      timeout: 60_000,
    },
    {
      command: 'npm run dev -- --port 5173 --strictPort',
      cwd: __dirname,
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
