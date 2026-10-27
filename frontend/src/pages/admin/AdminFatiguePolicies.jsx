import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { Sliders, CheckCircle2, AlertTriangle, Save, HardHat, Bike, Shield } from 'lucide-react';

export function AdminFatiguePolicies() {
  const [policies, setPolicies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    loadPolicies();
  }, []);

  const loadPolicies = async () => {
    try {
      setLoading(true);
      setErrorMsg('');
      const data = await api.get('/fatigue/policies');
      setPolicies(data);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load fatigue policies.');
    } finally {
      setLoading(false);
    }
  };

  const handleFieldChange = (policyId, field, val) => {
    setPolicies(policies.map((p) => (p.id === policyId ? { ...p, [field]: val } : p)));
  };

  const handleSavePolicy = async (policy) => {
    try {
      setSavingId(policy.id);
      setErrorMsg('');
      setSuccessMsg('');
      const res = await api.put(`/fatigue/policies/${policy.id}`, {
        policy_name: policy.policy_name,
        max_daily_hours: parseFloat(policy.max_daily_hours),
        min_rest_hours_between_shifts: parseFloat(policy.min_rest_hours_between_shifts),
        max_weekly_hours: parseFloat(policy.max_weekly_hours),
        mandatory_break_threshold_hours: parseFloat(policy.mandatory_break_threshold_hours),
        mandatory_break_duration_minutes: parseFloat(policy.mandatory_break_duration_minutes),
        max_consecutive_days: parseInt(policy.max_consecutive_days, 10)
      });
      setSuccessMsg(`Policy "${res.policy_name}" updated and activated!`);
      await loadPolicies();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to update policy.');
    } finally {
      setSavingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 text-slate-500 text-sm">
        <div className="w-5 h-5 border-2 border-sky-600 border-t-transparent rounded-full animate-spin mr-2"></div>
        Loading configurable industry fatigue policies...
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
                Configurable Regulatory Rules
              </span>
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-slate-300"></span>
              <span className="text-xs text-slate-500 font-medium">Industry Specific Standards</span>
            </div>
            <h1 className="text-2xl font-black text-slate-900 mt-1">
              Industry Work & Rest Policies
            </h1>
            <p className="text-xs text-slate-600 mt-0.5">
              Customize daily caps, minimum rest intervals, and weekly overwork boundaries per industry sector.
            </p>
          </div>
        </div>
      </div>

      {successMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-300 rounded-xl text-xs text-emerald-800 font-semibold flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 bg-rose-50 border border-rose-300 rounded-xl text-xs text-rose-800 font-semibold flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Policies Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {policies.map((p) => (
          <div key={p.id} className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 flex flex-col justify-between space-y-5">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  {p.industry_sector === 'construction' ? (
                    <HardHat className="w-5 h-5 text-amber-500" />
                  ) : (
                    <Bike className="w-5 h-5 text-emerald-500" />
                  )}
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-500 capitalize">
                    {p.industry_sector.replace('_', ' ')} Sector
                  </span>
                </div>
                <span className="text-[10px] font-mono text-slate-400">Policy ID: #{p.id.slice(0, 8)}</span>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Policy Title</label>
                <input
                  type="text"
                  value={p.policy_name}
                  onChange={(e) => handleFieldChange(p.id, 'policy_name', e.target.value)}
                  className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg font-bold text-slate-900"
                />
              </div>

              {/* Threshold Fields */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">
                    Max Daily Hours (24h)
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    value={p.max_daily_hours}
                    onChange={(e) => handleFieldChange(p.id, 'max_daily_hours', e.target.value)}
                    className="w-full p-2 bg-slate-50 border border-slate-300 rounded font-mono font-bold"
                  />
                  <span className="text-[10px] text-slate-500">e.g. 10.0h or 12.0h</span>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">
                    Min Rest Between Shifts
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    value={p.min_rest_hours_between_shifts}
                    onChange={(e) => handleFieldChange(p.id, 'min_rest_hours_between_shifts', e.target.value)}
                    className="w-full p-2 bg-slate-50 border border-slate-300 rounded font-mono font-bold"
                  />
                  <span className="text-[10px] text-slate-500">e.g. 11.0h or 8.0h</span>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">
                    Max Weekly Hours (7d)
                  </label>
                  <input
                    type="number"
                    step="1"
                    value={p.max_weekly_hours}
                    onChange={(e) => handleFieldChange(p.id, 'max_weekly_hours', e.target.value)}
                    className="w-full p-2 bg-slate-50 border border-slate-300 rounded font-mono font-bold"
                  />
                  <span className="text-[10px] text-slate-500">e.g. 50.0h or 60.0h</span>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">
                    Max Consecutive Days
                  </label>
                  <input
                    type="number"
                    step="1"
                    value={p.max_consecutive_days}
                    onChange={(e) => handleFieldChange(p.id, 'max_consecutive_days', e.target.value)}
                    className="w-full p-2 bg-slate-50 border border-slate-300 rounded font-mono font-bold"
                  />
                  <span className="text-[10px] text-slate-500">Standard: 6 days</span>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
              <span className="text-[11px] text-slate-400">
                Updated: {new Date(p.updated_at).toLocaleDateString()}
              </span>
              <button
                type="button"
                disabled={savingId === p.id}
                onClick={() => handleSavePolicy(p)}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white text-xs font-bold rounded-lg shadow transition flex items-center space-x-1.5"
              >
                <Save className="w-3.5 h-3.5" />
                <span>{savingId === p.id ? 'Updating...' : 'Save & Enforce'}</span>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
