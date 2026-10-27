import React, { useEffect, useState } from 'react';
import { api } from '../../api/client';

export function AdminAttendance() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/shifts/attendance')
      .then(setEvents)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="p-8 text-slate-500">Loading attendance…</p>;
  return <section className="space-y-4">
    <header><h1 className="text-2xl font-black">Attendance & check-in audit</h1><p className="text-sm text-slate-600">Recent successful check-ins/outs and rejected attempts for your organization.</p></header>
    {error && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
    {!events.length && !error && <p className="rounded-xl border border-dashed p-8 text-center text-slate-500">No attendance events recorded yet.</p>}
    {!!events.length && <div className="overflow-x-auto rounded-xl border bg-white shadow-sm">
      <table className="w-full min-w-[700px] text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="p-4">Time</th><th className="p-4">Worker</th><th className="p-4">Site</th><th className="p-4">Action</th><th className="p-4">Result</th><th className="p-4">Details</th></tr></thead>
        <tbody className="divide-y">{events.map((event) => <tr key={event.id}>
          <td className="p-4 whitespace-nowrap">{new Date(event.timestamp).toLocaleString()}</td>
          <td className="p-4">{event.worker_name}</td><td className="p-4">{event.site_name}</td><td className="p-4">{event.action.replace('_', ' ')}</td>
          <td className="p-4"><span className={`rounded-full px-2 py-1 text-xs font-semibold ${event.result === 'verified' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}`}>{event.result.replaceAll('_', ' ')}</span></td>
          <td className="max-w-sm p-4 text-slate-600">{event.reason || event.shift_id || '—'}</td>
        </tr>)}</tbody>
      </table>
    </div>}
  </section>;
}
