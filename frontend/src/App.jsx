import React, { Suspense, lazy, useState } from 'react';
import { useAuth } from './context/AuthContext';
import { Navbar } from './components/common/Navbar';
import { api } from './api/client';

const WorkerDashboard = lazy(() => import('./pages/worker/WorkerDashboard').then((module) => ({ default: module.WorkerDashboard })));
const WorkerEarnings = lazy(() => import('./pages/worker/WorkerEarnings').then((module) => ({ default: module.WorkerEarnings })));
const WorkerSafety = lazy(() => import('./pages/worker/WorkerSafety').then((module) => ({ default: module.WorkerSafety })));
const WorkerDisputes = lazy(() => import('./pages/worker/WorkerDisputes').then((module) => ({ default: module.WorkerDisputes })));
const AdminShiftDispatch = lazy(() => import('./pages/admin/AdminShiftDispatch').then((module) => ({ default: module.AdminShiftDispatch })));
const AdminSiteQR = lazy(() => import('./pages/admin/AdminSiteQR').then((module) => ({ default: module.AdminSiteQR })));
const AdminFatiguePolicies = lazy(() => import('./pages/admin/AdminFatiguePolicies').then((module) => ({ default: module.AdminFatiguePolicies })));
const AdminFatigueAudit = lazy(() => import('./pages/admin/AdminFatigueAudit').then((module) => ({ default: module.AdminFatigueAudit })));
const AdminPayrollLedger = lazy(() => import('./pages/admin/AdminPayrollLedger').then((module) => ({ default: module.AdminPayrollLedger })));
const AdminSafetyAudit = lazy(() => import('./pages/admin/AdminSafetyAudit').then((module) => ({ default: module.AdminSafetyAudit })));
const AdminPeopleSites = lazy(() => import('./pages/admin/AdminPeopleSites').then((module) => ({ default: module.AdminPeopleSites })));
const AdminAttendance = lazy(() => import('./pages/admin/AdminAttendance').then((module) => ({ default: module.AdminAttendance })));

const workerTabs = [
  ['home', 'My shifts'],
  ['earnings', 'Earnings'],
  ['safety', 'Safety reports'],
  ['disputes', 'Disputes'],
];
const adminTabs = [
  ['dispatch', 'Shift dispatch'],
  ['people', 'Workers & sites'],
  ['attendance', 'Attendance'],
  ['policies', 'Work/rest policy'],
  ['qr', 'Site QR'],
  ['payroll', 'Earnings ledger'],
  ['fatigue', 'Fatigue audit'],
  ['safety', 'Safety reports'],
  ['disputes', 'Disputes'],
];
const safetyTabs = [
  ['safety', 'Safety reports'],
  ['fatigue', 'Fatigue audit'],
];

function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await login(email.trim(), password);
    } catch (requestError) {
      setError(requestError.message || 'Login failed. Check your credentials.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-12 flex items-center justify-center">
      <section className="w-full max-w-5xl grid md:grid-cols-2 overflow-hidden rounded-3xl shadow-2xl">
        <div className="bg-slate-900 p-8 md:p-12 text-white flex flex-col justify-between min-h-[420px]">
          <div>
            <p className="text-sm font-bold uppercase tracking-[.2em] text-sky-400">FairShift</p>
            <h1 className="mt-8 text-4xl font-black leading-tight">Fair work.<br />Safer shifts.</h1>
            <p className="mt-4 max-w-sm text-slate-300">Attendance, earnings, work/rest protection and safety reporting for platform and construction workers.</p>
          </div>
          <p className="mt-8 text-xs leading-5 text-slate-400">Sign in with the demo account for your organization. Fatigue limits are configured per employer and enforced by the service.</p>
        </div>
        <form onSubmit={submit} className="bg-white p-8 md:p-12 flex flex-col justify-center">
          <h2 className="text-2xl font-bold text-slate-900">Sign in</h2>
          <label className="mt-6 text-sm font-semibold text-slate-700" htmlFor="email">Email</label>
          <input id="email" type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} className="mt-2 rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-sky-600" />
          <label className="mt-4 text-sm font-semibold text-slate-700" htmlFor="password">Password</label>
          <input id="password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} className="mt-2 rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-sky-600" />
          {error && <p role="alert" className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
          <button disabled={busy} className="mt-6 rounded-xl bg-sky-700 px-4 py-3 font-bold text-white hover:bg-sky-800 disabled:opacity-60">{busy ? 'Signing in…' : 'Sign in securely'}</button>
          <p className="mt-4 text-xs leading-5 text-slate-500">Demo users are created by <code>python -m seed.demo_data</code> from the backend directory. Public registration is disabled.</p>
        </form>
      </section>
    </main>
  );
}

function AdminDisputes() {
  const [items, setItems] = React.useState([]);
  const [busy, setBusy] = React.useState(true);
  const [error, setError] = React.useState('');

  const load = React.useCallback(async () => {
    try {
      setError('');
      setItems(await api.get('/disputes'));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }, []);
  React.useEffect(() => { load(); }, [load]);

  async function review(item, status) {
    const notes = window.prompt('Review notes (required):');
    if (!notes || notes.trim().length < 5) return;
    try {
      await api.patch(`/disputes/${item.id}/review`, {
        status,
        settled_amount: status === 'resolved_upheld' ? item.claimed_amount : null,
        resolution_notes: notes.trim(),
      });
      await load();
    } catch (e) {
      setError(e.message);
    }
  }

  if (busy) return <p className="p-8 text-slate-500">Loading disputes…</p>;
  return <section className="space-y-4">
    <header><h1 className="text-2xl font-black">Work & pay disputes</h1><p className="text-sm text-slate-600">Review submissions and record a reasoned outcome.</p></header>
    {error && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
    {items.length === 0 && <p className="rounded-xl border border-dashed p-8 text-center text-slate-500">No disputes in your organization.</p>}
    {items.map((item) => <article key={item.id} className="rounded-xl border bg-white p-5 shadow-sm">
      <div className="flex flex-wrap justify-between gap-2"><h2 className="font-bold">{item.dispute_type.replaceAll('_', ' ')} · {item.worker_name}</h2><span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold">{item.status}</span></div>
      <p className="mt-2 text-sm text-slate-600">{item.worker_explanation}</p><p className="mt-2 text-sm">Claimed: ${item.claimed_amount} · {item.workplace_name || 'Work site'}</p>
      {item.status !== 'resolved_upheld' && item.status !== 'resolved_rejected' && <div className="mt-4 flex gap-2">
        <button onClick={() => review(item, 'under_review')} className="rounded-lg bg-slate-100 px-3 py-2 text-sm font-semibold">Mark reviewing</button>
        <button onClick={() => review(item, 'resolved_upheld')} className="rounded-lg bg-emerald-700 px-3 py-2 text-sm font-semibold text-white">Uphold claim</button>
        <button onClick={() => review(item, 'resolved_rejected')} className="rounded-lg bg-rose-700 px-3 py-2 text-sm font-semibold text-white">Reject with notes</button>
      </div>}
      {item.resolution_notes && <p className="mt-3 border-t pt-3 text-sm text-slate-600">Review: {item.resolution_notes}</p>}
    </article>)}
  </section>;
}

function Workspace({ user }) {
  const isWorker = user.role === 'worker';
  const tabs = isWorker ? workerTabs : user.role === 'employer_admin' ? adminTabs : safetyTabs;
  const [active, setActive] = useState(tabs[0][0]);
  const screen = {
    home: <WorkerDashboard />,
    earnings: <WorkerEarnings />,
    safety: isWorker ? <WorkerSafety /> : <AdminSafetyAudit />,
    disputes: isWorker ? <WorkerDisputes /> : <AdminDisputes />,
    dispatch: <AdminShiftDispatch />,
    people: <AdminPeopleSites />,
    attendance: <AdminAttendance />,
    qr: <AdminSiteQR />,
    policies: <AdminFatiguePolicies />,
    payroll: <AdminPayrollLedger />,
    fatigue: <AdminFatigueAudit />,
  }[active];

  return <>
    <Navbar />
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <nav aria-label="Main navigation" className="mb-6 flex gap-2 overflow-x-auto rounded-2xl border border-slate-200 bg-white p-2 shadow-sm">
        {tabs.map(([id, label]) => <button key={id} onClick={() => setActive(id)} aria-current={active === id ? 'page' : undefined} className={`shrink-0 rounded-xl px-4 py-2.5 text-sm font-semibold transition ${active === id ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'}`}>{label}</button>)}
      </nav>
      <Suspense fallback={<p className="rounded-xl border bg-white p-8 text-slate-500">Loading workspace…</p>}>
        {screen}
      </Suspense>
    </main>
  </>;
}

export function App() {
  const { user, loading } = useAuth();
  if (loading) return <main className="min-h-screen grid place-items-center text-slate-600">Loading FairShift…</main>;
  return user ? <Workspace key={user.id} user={user} /> : <Login />;
}
