# FairShift

FairShift is a React/Vite and FastAPI worker-protection MVP. It supports two seeded demo organizations, organization-scoped administration, configurable work/rest policy enforcement, QR attendance, pay ledgers, safety reporting and worker disputes.

## Local setup (PowerShell)

From the repository root:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
npm install --prefix .\frontend
Set-Location -LiteralPath .\backend
$env:DATABASE_URL = "sqlite:///../fairshift.db"
..\.venv\Scripts\python.exe -m seed.demo_data
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal, launch the Vite dev server:

```powershell
Set-Location -LiteralPath .\frontend
node .\node_modules\vite\bin\vite.js --host 127.0.0.1
```

Open `http://127.0.0.1:5173`. FastAPI serves the production frontend at `http://127.0.0.1:8000` after a frontend build (`node .\node_modules\vite\bin\vite.js build` from `frontend`).

The seed command leaves existing user data untouched. To deliberately clear and recreate the current database, pass `--reset`; this deletes all app records in that database:

```powershell
Set-Location -LiteralPath .\backend
..\.venv\Scripts\python.exe -m seed.demo_data --reset
```

## Demo accounts

| Organization | Role | Email | Password |
|---|---|---|---|
| Metro Construction Services | Admin | `admin.sarah@fairshift.demo` | `AdminPass123!` |
| Metro Construction Services | Safety officer | `safety.marcus@fairshift.demo` | `SafetyPass123!` |
| Metro Construction Services | Worker | `worker.carlos@fairshift.demo` | `WorkerPass123!` |
| Northstar Delivery Platform | Admin | `admin.priya@fairshift.demo` | `AdminPass123!` |
| Northstar Delivery Platform | Worker | `worker.amina@fairshift.demo` | `WorkerPass123!` |

Public registration is disabled. Organization admins can create worker accounts and sites; role and tenant association are assigned by the backend. To switch demo roles, sign out and authenticate with the other account; the signed-in navbar does not offer a shortcut between users.

These shared demo credentials are for local testing only. Do not seed a production database with the documented demo passwords; configure unique credentials and production secrets before any deployment.

## Core behavior

- Every user, site and fatigue policy is assigned to an organization. Shift assignment, policy, payroll, safety, dispute, evidence, QR and audit endpoints scope records to the authenticated user's organization.
- FatigueGuard rejects overlapping shifts, insufficient rest, and daily/weekly threshold breaches at assignment and again at check-in. Rejections are retained in organization-scoped fatigue/attendance audit records. No override endpoint exists.
- Site QR tokens identify sites; signed-in worker identity and shift assignment remain mandatory. Check-in and check-out support the camera scanner and a clearly marked manual/demo token fallback.
- Ledger calculations use `net_pay = gross_pay - total_deductions`; payment transitions are pending → approved → paid. Evidence downloads require authentication and organization/owner authorization.

The seeded fatigue thresholds and policy labels are demonstration configurations, not universal legal limits or legal advice. Each organization administrator can adjust policy thresholds within validated bounds.

## Configuration and Cloud Run preparation

Local defaults are for development only. In deployed environments set different random `JWT_SECRET_KEY` and `SITE_QR_SECRET` values (at least 32 characters each), `DATABASE_URL` (PostgreSQL URL supported through psycopg), `ENVIRONMENT=production`, `CORS_ORIGINS` (JSON array), `STORAGE_BACKEND=gcs`, and `GCS_BUCKET_NAME`. Startup rejects production configuration that would use development secrets, SQLite, or local evidence storage. The runtime service account needs least-privilege access to the private evidence bucket. GCS signed-URL signing must be configured for the service identity.

The app's additive startup schema setup is suitable for the local MVP, not a substitute for reviewed production database migrations. SQLite and the container filesystem are not durable on Cloud Run. Use managed PostgreSQL and a private durable object bucket; configure secrets and database connectivity before deployment. `Dockerfile` builds the Vite assets and serves them from FastAPI.

## Vercel deployment

`index.py` exposes the existing FastAPI app to Vercel, while `vercel.json` builds and serves the Vite frontend. Link the existing Vercel project with `npx vercel link`; do not create a new project. Before deploying, configure production environment variables in that project's settings: `ENVIRONMENT=production`, `DATABASE_URL` (managed PostgreSQL), distinct random `JWT_SECRET_KEY` and `SITE_QR_SECRET` values of at least 32 characters, `STORAGE_BACKEND=gcs`, `GCS_BUCKET_NAME`, and `GCS_SERVICE_ACCOUNT_JSON` (service-account JSON with least-privilege access to the private bucket). Seed an empty production database with `python -m seed.demo_data` from `backend`, then deploy with `npx vercel deploy --prod`. Do not use SQLite or local uploads for deployed records or evidence.

## Tests

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
Set-Location -LiteralPath .\frontend
node .\node_modules\vite\bin\vite.js build
```