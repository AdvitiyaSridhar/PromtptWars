import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { ShieldAlert, AlertTriangle, CheckCircle2, Upload, FileText, UserCheck, EyeOff, Plus, ChevronRight } from 'lucide-react';

export function WorkerSafety() {
  const [reports, setReports] = useState([]);
  const [workplaces, setWorkplaces] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [showForm, setShowForm] = useState(false);

  // Form State
  const [workplaceId, setWorkplaceId] = useState('');
  const [category, setCategory] = useState('hazard');
  const [severity, setSeverity] = useState('high');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [isAnonymous, setIsAnonymous] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setErrorMsg('');
      const [reportsData, placesData] = await Promise.all([
        api.get('/safety/reports'),
        api.get('/workplaces')
      ]);
      setReports(reportsData);
      setWorkplaces(placesData);
      if (placesData.length > 0 && !workplaceId) {
        setWorkplaceId(placesData[0].id);
      }
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load safety reports.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title || !description || !workplaceId) {
      setErrorMsg('Please complete all required fields.');
      return;
    }

    try {
      setSubmitting(true);
      setErrorMsg('');
      setSuccessMsg('');

      // 1. Submit report
      const newReport = await api.post('/safety/reports', {
        workplace_id: workplaceId,
        category,
        severity,
        title,
        description,
        is_anonymous: isAnonymous
      });

      // 2. Upload evidence if selected
      if (selectedFile) {
        const formData = new FormData();
        formData.append('file', selectedFile);
        await api.post(`/safety/reports/${newReport.id}/evidence`, formData);
      }

      setSuccessMsg(`Safety report submitted successfully! Case #${newReport.id.slice(0, 8)}`);
      setTitle('');
      setDescription('');
      setSelectedFile(null);
      setShowForm(false);
      await loadData();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to submit safety report.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 text-slate-500 text-sm">
        <div className="w-5 h-5 border-2 border-sky-600 border-t-transparent rounded-full animate-spin mr-2"></div>
        Loading safety incident registry...
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
                Workplace Protection
              </span>
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-slate-300"></span>
              <span className="text-xs text-slate-500 font-medium">Whistleblower Protection</span>
            </div>
            <h1 className="text-2xl font-black text-slate-900 mt-1">
              Safety Reporting & Corrective Actions
            </h1>
            <p className="text-xs text-slate-600 mt-0.5">
              Report hazards, near-misses, and safety non-compliance with optional identity shielding.
            </p>
          </div>

          <button
            onClick={() => setShowForm(!showForm)}
            className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold rounded-xl shadow transition flex items-center space-x-1.5 self-start md:self-auto"
          >
            <Plus className="w-4 h-4" />
            <span>{showForm ? 'Cancel Report' : 'File Hazard Report'}</span>
          </button>
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

      {/* Safety Submission Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white rounded-2xl p-6 shadow-sm border border-amber-200 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
              <ShieldAlert className="w-4 h-4 text-amber-600" />
              <span>Submit Workplace Safety Report</span>
            </h2>
            <span className="text-xs text-slate-500">* All fields required</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Worksite</label>
              <select
                value={workplaceId}
                onChange={(e) => setWorkplaceId(e.target.value)}
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 text-slate-800"
              >
                {workplaces.map((w) => (
                  <option key={w.id} value={w.id}>{w.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Hazard Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 text-slate-800"
              >
                <option value="hazard">Hazard / Physical Obstacle</option>
                <option value="near_miss">Near Miss</option>
                <option value="injury">Injury Incident</option>
                <option value="heat_stress">Heat / Weather Stress</option>
                <option value="ppe_shortage">Lack of Mandatory PPE</option>
                <option value="equipment_defect">Faulty Equipment / Vehicle</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Severity Level</label>
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 text-slate-800"
              >
                <option value="low">Low — Minor observation</option>
                <option value="medium">Medium — Action needed</option>
                <option value="high">High — Dangerous condition</option>
                <option value="critical">Critical — Immediate life safety stop</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">Incident / Hazard Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Scaffolding missing guardrail on Level 3 walkway"
              className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 text-slate-800"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">Detailed Description & Location</label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what occurred or what condition exists, where on the site, and immediate risks..."
              className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 text-slate-800"
            />
          </div>

          {/* Evidence Upload & Anonymous Shield */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Attach Photo Evidence (Optional)</label>
              <input
                type="file"
                accept="image/*,application/pdf"
                onChange={(e) => setSelectedFile(e.target.files[0] || null)}
                className="w-full text-xs p-2 bg-slate-50 border border-slate-300 rounded-lg file:mr-3 file:py-1 file:px-2.5 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-slate-800 file:text-white hover:file:bg-slate-700"
              />
              <p className="text-[10px] text-slate-500 mt-1">Stored in persistent blob storage.</p>
            </div>

            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 flex items-start space-x-3">
              <input
                id="anon_check"
                type="checkbox"
                checked={isAnonymous}
                onChange={(e) => setIsAnonymous(e.target.checked)}
                className="mt-1 w-4 h-4 text-sky-600 rounded border-slate-300 focus:ring-sky-500"
              />
              <label htmlFor="anon_check" className="text-xs text-slate-700 cursor-pointer">
                <span className="font-bold flex items-center space-x-1 text-slate-900">
                  <EyeOff className="w-3.5 h-3.5 text-slate-600" />
                  <span>Submit Anonymously</span>
                </span>
                <span className="text-[11px] text-slate-500 block mt-0.5">
                  Your identity is redacted from site supervisors and fellow workers to guarantee anti-retaliation protection.
                </span>
              </label>
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
              className="px-5 py-2 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white text-xs font-bold rounded-lg shadow transition"
            >
              {submitting ? 'Submitting...' : 'File Safety Report'}
            </button>
          </div>
        </form>
      )}

      {/* Safety Reports List */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-900">Active Site Hazards & Corrective Actions</h2>
          <span className="text-xs text-slate-500">{reports.length} reports tracked</span>
        </div>

        <div className="divide-y divide-slate-100">
          {reports.length === 0 ? (
            <div className="px-6 py-12 text-center text-slate-400 text-xs">
              No safety hazards or incidents currently recorded.
            </div>
          ) : (
            reports.map((r) => (
              <div key={r.id} className="p-6 hover:bg-slate-50/50 transition space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                      r.severity === 'critical'
                        ? 'bg-rose-100 text-rose-800 border border-rose-300'
                        : r.severity === 'high'
                        ? 'bg-amber-100 text-amber-800'
                        : 'bg-slate-100 text-slate-800'
                    }`}>
                      {r.severity}
                    </span>
                    <span className="text-xs font-bold text-slate-900 capitalize">
                      {r.category.replace('_', ' ')}
                    </span>
                    <span className="text-xs text-slate-400">•</span>
                    <span className="text-xs text-slate-500 font-medium">{r.workplace_name}</span>
                  </div>

                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase self-start sm:self-auto ${
                    r.status === 'resolved'
                      ? 'bg-emerald-100 text-emerald-800'
                      : r.status === 'corrective_action_pending'
                      ? 'bg-amber-100 text-amber-800'
                      : 'bg-sky-100 text-sky-800'
                  }`}>
                    {r.status.replace(/_/g, ' ')}
                  </span>
                </div>

                <div>
                  <h3 className="text-sm font-bold text-slate-900">{r.title}</h3>
                  <p className="text-xs text-slate-600 mt-1 leading-relaxed">{r.description}</p>
                </div>

                <div className="text-[11px] text-slate-400 flex items-center space-x-3">
                  <span>Reported by: <span className="font-semibold text-slate-600">{r.reporter_name}</span></span>
                  <span>•</span>
                  <span>{new Date(r.created_at).toLocaleDateString()}</span>
                </div>

                {/* Corrective Actions Section */}
                {r.actions && r.actions.length > 0 && (
                  <div className="mt-3 p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                      Corrective Action Plan & Sign-Off
                    </span>
                    {r.actions.map((act) => (
                      <div key={act.id} className="text-xs space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-800">{act.action_description}</span>
                          <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                            act.completed_at ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                          }`}>
                            {act.completed_at ? 'Completed' : `Due: ${act.due_date}`}
                          </span>
                        </div>
                        {act.verification_notes && (
                          <p className="text-[11px] text-emerald-700 bg-emerald-50/70 p-2 rounded border border-emerald-200">
                            Verification: {act.verification_notes}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
