import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { Calendar, Clock, AlertTriangle, Plus, CheckCircle2, User, HardHat, Building, AlertOctagon } from 'lucide-react';

export function AdminShiftDispatch() {
  const [shifts, setShifts] = useState([]);
  const [workplaces, setWorkplaces] = useState([]);
  const [workers, setWorkers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [errorData, setErrorData] = useState(null);
  const [successMsg, setSuccessMsg] = useState('');

  // Form State
  const [workerId, setWorkerId] = useState('');
  const [workplaceId, setWorkplaceId] = useState('');
  const [startDate, setStartDate] = useState('');
  const [startTime, setStartTime] = useState('08:00');
  const [durationHours, setDurationHours] = useState('8');
  const [baseRate, setBaseRate] = useState('26.00');

  useEffect(() => {
    loadData();
    // Default today's date
    const today = new Date().toISOString().split('T')[0];
    setStartDate(today);
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setErrorData(null);
      const [shiftsData, placesData, workerList] = await Promise.all([
        api.get('/shifts'),
        api.get('/workplaces'),
        api.get('/workers')
      ]);
      setShifts(shiftsData);
      setWorkplaces(placesData);
      if (placesData.length > 0 && !workplaceId) {
        setWorkplaceId(placesData[0].id);
      }

      setWorkers(workerList);
      if (workerList.length > 0 && !workerId) {
        setWorkerId(workerList[0].id);
      }
    } catch (err) {
      setErrorData({ message: err.message || 'Failed to load dispatch board.' });
    } finally {
      setLoading(false);
    }
  };

  const handleScheduleShift = async (e) => {
    e.preventDefault();
    setErrorData(null);
    setSuccessMsg('');

    if (!workerId || !workplaceId || !startDate || !startTime) {
      setErrorData({ message: 'Please complete all scheduling fields.' });
      return;
    }

    try {
      setSubmitting(true);
      const scheduledStart = new Date(`${startDate}T${startTime}:00Z`);
      const scheduledEnd = new Date(scheduledStart.getTime() + parseFloat(durationHours) * 3600000);

      // Backend evaluates FatigueGuard pre-assignment rules (Zero-Bypass)
      const res = await api.post('/shifts', {
        worker_id: workerId,
        workplace_id: workplaceId,
        scheduled_start: scheduledStart.toISOString(),
        scheduled_end: scheduledEnd.toISOString(),
        base_hourly_rate: parseFloat(baseRate),
        overtime_rate_multiplier: 1.50
      });

      setSuccessMsg(`Shift scheduled successfully for ${res.worker_name}! (Shift ID: #${res.id.slice(0, 8)})`);
      setShowForm(false);
      await loadData();
    } catch (err) {
      setErrorData(err.data?.detail || { message: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 text-slate-500 text-sm">
        <div className="w-5 h-5 border-2 border-sky-600 border-t-transparent rounded-full animate-spin mr-2"></div>
        Loading dispatch board & active assignments...
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Operations & Workforce Dispatch
              </span>
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-slate-300"></span>
              <span className="text-xs text-slate-500 font-medium">Pre-Assignment Safety Gating</span>
            </div>
            <h1 className="text-2xl font-black text-slate-900 mt-1">
              Shift Scheduling & Dispatch
            </h1>
            <p className="text-xs text-slate-600 mt-0.5">
              Assignments are automatically evaluated against mandatory industry work/rest limits before confirmation.
            </p>
          </div>

          <button
            onClick={() => setShowForm(!showForm)}
            className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white text-xs font-bold rounded-xl shadow transition flex items-center space-x-1.5 self-start md:self-auto"
          >
            <Plus className="w-4 h-4" />
            <span>{showForm ? 'Cancel Scheduling' : 'Assign New Shift'}</span>
          </button>
        </div>
      </div>

      {successMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-300 rounded-xl text-xs text-emerald-800 font-semibold flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Fatigue Block / Pre-Assignment Rejection Error */}
      {errorData && (
        <div className="p-4 bg-rose-50 border border-rose-300 rounded-xl space-y-2">
          <div className="flex items-center space-x-2 text-rose-900 font-bold text-xs">
            <AlertOctagon className="w-5 h-5 text-rose-600 shrink-0" />
            <span>
              {errorData.code === 'FATIGUE_LIMIT_BREACHED'
                ? 'Assignment Blocked by FatigueGuard'
                : 'Scheduling Validation Failed'}
            </span>
          </div>
          <p className="text-xs text-rose-800 font-medium">
            {errorData.reason || errorData.message || (typeof errorData === 'string' ? errorData : 'Shift assignment rejected.')}
          </p>

          {errorData.code === 'FATIGUE_LIMIT_BREACHED' && (
            <div className="bg-white p-3 rounded-lg border border-rose-200 text-xs text-rose-900 space-y-1">
              <span className="font-semibold block">Zero-Bypass Policy Invariant:</span>
              <p className="text-[11px] text-slate-600">
                FairShift strictly prohibits scheduling shifts that breach mandatory rest intervals or rolling work limits. 
                This attempt was logged to the Fatigue Violations Log for supervisory compliance review.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Scheduling Modal / Form */}
      {showForm && (
        <form onSubmit={handleScheduleShift} className="bg-white rounded-2xl p-6 shadow-sm border border-sky-200 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
              <Calendar className="w-4 h-4 text-sky-600" />
              <span>Schedule Shift with Safety Pre-Validation</span>
            </h2>
            <span className="text-[11px] text-slate-400">FatigueGuard evaluates rest gaps automatically</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Assign Worker</label>
              <select
                value={workerId}
                onChange={(e) => setWorkerId(e.target.value)}
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500 text-slate-800"
              >
                {workers.map((w) => (
                  <option key={w.id} value={w.id}>{w.full_name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Worksite / Job Location</label>
              <select
                value={workplaceId}
                onChange={(e) => setWorkplaceId(e.target.value)}
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500 text-slate-800"
              >
                {workplaces.map((w) => (
                  <option key={w.id} value={w.id}>{w.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Base Hourly Rate ($ USD)</label>
              <input
                type="number"
                step="0.50"
                value={baseRate}
                onChange={(e) => setBaseRate(e.target.value)}
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500 font-mono text-slate-800"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Date</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500 text-slate-800"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Start Time (UTC/Local)</label>
              <input
                type="time"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500 text-slate-800"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Planned Duration</label>
              <select
                value={durationHours}
                onChange={(e) => setDurationHours(e.target.value)}
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500 text-slate-800"
              >
                <option value="4">4 Hours (Half shift)</option>
                <option value="8">8 Hours (Standard)</option>
                <option value="10">10 Hours (Max trade shift)</option>
                <option value="12">12 Hours (Courier max)</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end space-x-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="px-4 py-2 border border-slate-300 text-slate-700 hover:bg-slate-50 text-xs font-semibold rounded-lg transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2 bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white text-xs font-bold rounded-lg shadow transition"
            >
              {submitting ? 'Evaluating Safety Rules...' : 'Confirm & Dispatch'}
            </button>
          </div>
        </form>
      )}

      {/* Shifts Board */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-900">Worksite Shift Board</h2>
          <span className="text-xs text-slate-500">{shifts.length} active assignments</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
              <tr>
                <th className="px-6 py-3">Assigned Worker</th>
                <th className="px-6 py-3">Worksite</th>
                <th className="px-6 py-3">Scheduled Window</th>
                <th className="px-6 py-3">Rate</th>
                <th className="px-6 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {shifts.length === 0 ? (
                <tr>
                  <td colSpan="5" className="px-6 py-8 text-center text-slate-400">
                    No shifts created.
                  </td>
                </tr>
              ) : (
                shifts.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-50/70 transition">
                    <td className="px-6 py-3.5 font-bold text-slate-900">{s.worker_name}</td>
                    <td className="px-6 py-3.5 text-slate-700 font-medium">{s.workplace_name}</td>
                    <td className="px-6 py-3.5 text-slate-600">
                      {new Date(s.scheduled_start).toLocaleDateString()} {new Date(s.scheduled_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} — {new Date(s.scheduled_end).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="px-6 py-3.5 font-mono">${s.base_hourly_rate}/hr</td>
                    <td className="px-6 py-3.5">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                        s.status === 'completed'
                          ? 'bg-emerald-100 text-emerald-800'
                          : s.status === 'in_progress'
                          ? 'bg-sky-100 text-sky-800 font-bold'
                          : 'bg-amber-100 text-amber-800'
                      }`}>
                        {s.status.replace('_', ' ')}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
