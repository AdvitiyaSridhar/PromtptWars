import React, { useEffect, useState } from 'react';
import { api } from '../../api/client';

export function AdminPeopleSites() {
  const [workers, setWorkers] = useState([]);
  const [sites, setSites] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [worker, setWorker] = useState({ full_name: '', email: '', password: '' });
  const [site, setSite] = useState({ name: '', address: '', industry_sector: 'construction', fatigue_policy_id: '' });

  async function load() {
    try {
      setError('');
      const [people, workplaces, policyList] = await Promise.all([
        api.get('/workers'), api.get('/workplaces'), api.get('/fatigue/policies'),
      ]);
      setWorkers(people);
      setSites(workplaces);
      setPolicies(policyList);
      setSite((current) => ({ ...current, fatigue_policy_id: current.fatigue_policy_id || policyList[0]?.id || '' }));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); }, []);

  async function createWorker(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await api.post('/workers', worker);
      setWorker({ full_name: '', email: '', password: '' });
      setNotice('Worker account created.');
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function createSite(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await api.post('/workplaces', site);
      setSite((current) => ({ ...current, name: '', address: '' }));
      setNotice('Work site created and linked to your fatigue policy.');
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <p className="p-8 text-slate-500">Loading organization records…</p>;
  return <section className="space-y-6">
    <header><h1 className="text-2xl font-black">Workers & work sites</h1><p className="text-sm text-slate-600">These records are private to your organization.</p></header>
    {error && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
    {notice && <p role="status" className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</p>}
    <div className="grid gap-6 lg:grid-cols-2">
      <form onSubmit={createWorker} className="space-y-3 rounded-2xl border bg-white p-5 shadow-sm">
        <h2 className="text-lg font-bold">Add worker account</h2>
        <input required minLength="2" placeholder="Full name" value={worker.full_name} onChange={(e) => setWorker({ ...worker, full_name: e.target.value })} className="w-full rounded-lg border p-3" />
        <input required type="email" placeholder="Email" value={worker.email} onChange={(e) => setWorker({ ...worker, email: e.target.value })} className="w-full rounded-lg border p-3" />
        <input required minLength="10" type="password" placeholder="Temporary password (10+ characters)" value={worker.password} onChange={(e) => setWorker({ ...worker, password: e.target.value })} className="w-full rounded-lg border p-3" />
        <button disabled={busy} className="rounded-lg bg-slate-900 px-4 py-2 font-semibold text-white disabled:opacity-50">Create worker</button>
      </form>
      <form onSubmit={createSite} className="space-y-3 rounded-2xl border bg-white p-5 shadow-sm">
        <h2 className="text-lg font-bold">Add work site</h2>
        <input required minLength="2" placeholder="Site name" value={site.name} onChange={(e) => setSite({ ...site, name: e.target.value })} className="w-full rounded-lg border p-3" />
        <input required minLength="2" placeholder="Address" value={site.address} onChange={(e) => setSite({ ...site, address: e.target.value })} className="w-full rounded-lg border p-3" />
        <select value={site.industry_sector} onChange={(e) => setSite({ ...site, industry_sector: e.target.value, fatigue_policy_id: '' })} className="w-full rounded-lg border p-3">
          <option value="construction">Construction</option><option value="gig_platform">Gig / platform</option>
        </select>
        <select required value={site.fatigue_policy_id} onChange={(e) => setSite({ ...site, fatigue_policy_id: e.target.value })} className="w-full rounded-lg border p-3">
          <option value="">Select a work/rest policy</option>
          {policies.filter((item) => item.industry_sector === site.industry_sector).map((item) => <option key={item.id} value={item.id}>{item.policy_name}</option>)}
        </select>
        <button disabled={busy || !site.fatigue_policy_id} className="rounded-lg bg-sky-700 px-4 py-2 font-semibold text-white disabled:opacity-50">Create site</button>
      </form>
    </div>
    <div className="grid gap-6 md:grid-cols-2">
      <div className="rounded-2xl border bg-white p-5 shadow-sm"><h2 className="font-bold">Workers ({workers.length})</h2>{workers.length ? <ul className="mt-3 divide-y">{workers.map((person) => <li key={person.id} className="py-2"><p className="font-medium">{person.full_name}</p><p className="text-sm text-slate-500">{person.email}</p></li>)}</ul> : <p className="mt-3 text-sm text-slate-500">No worker accounts yet.</p>}</div>
      <div className="rounded-2xl border bg-white p-5 shadow-sm"><h2 className="font-bold">Sites ({sites.length})</h2>{sites.length ? <ul className="mt-3 divide-y">{sites.map((place) => <li key={place.id} className="py-2"><p className="font-medium">{place.name}</p><p className="text-sm text-slate-500">{place.address} · {place.industry_sector.replace('_', ' ')}</p></li>)}</ul> : <p className="mt-3 text-sm text-slate-500">No sites yet.</p>}</div>
    </div>
  </section>;
}
