import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { ShieldAlert, AlertTriangle, CheckCircle2, Clock, Plus, Check, UserCheck, EyeOff } from 'lucide-react';

export function AdminSafetyAudit() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Corrective action modal state
  const [selectedReportId, setSelectedReportId] = useState(null);
  const [actionDesc, setActionDesc] = useState('');
  const [actionDueDate, setActionDueDate] = useState('');
  const [submittingAction, setSubmittingAction] = useState(false);

  // Verification modal state
  const [verifyingActionId, setVerifyingActionId] = useState(null);
  const [verificationNotes, setVerificationNotes] = useState('');
  const [submittingVerify, setSubmittingVerify] = useState(false);

  useEffect(() => {
    loadReports();
    const tomorrow = new Date(Date.now() + 86400000).toISOString().split('T')[0];
    setActionDueDate(tomorrow);
  }, []);

  const loadReports = async () => {
    try {
      setLoading(true);
      setErrorMsg('');
      const data = await api.get('/safety/reports');
      setReports(data);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load safety reports.');
    } finally {
      setLoading(false);
    }
  };

  const handleAddAction = async (e) => {
    e.preventDefault();
    if (!actionDesc || !actionDueDate) {
      setErrorMsg('Please enter an action description and due date.');
      return;
    }

    try {
      setSubmittingAction(true);
      setErrorMsg('');
      // Assign to current admin
      const profile = await api.get('/auth/me');
      await api.post(`/safety/reports/${selectedReportId}/actions`, {
        action_description: actionDesc,
        assigned_to: profile.id,
        due_date: actionDueDate
      });

      setSuccessMsg('Corrective action assigned and tracked.');
      setSelectedReportId(null);
      setActionDesc('');
      await loadReports();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to assign corrective action.');
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleVerifyAction = async (e) => {
    e.preventDefault();
    if (!verificationNotes) {
      setErrorMsg('Please enter physical inspection verification notes.');
      return;
    }

    try {
      setSubmittingVerify(true);
      setErrorMsg('');
      await api.patch(`/safety/actions/${verifyingActionId}/resolve`, {
        verification_notes: verificationNotes
      });

      setSuccessMsg('Corrective action signed off and verified. Safety report resolved.');
      setVerifyingActionId(null);
      setVerificationNotes('');
      await loadReports();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to verify corrective action.');
    } finally {
      setSubmittingVerify(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 text-slate-500 text-sm">
        <div className="w-5 h-5 border-2 border-sky-600 border-t-transparent rounded-full animate-spin mr-2"></div>
        Loading safety audit registry & corrective action board...
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
                Site Safety Officer & Admin Hub
              </span>
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-slate-300"></span>
              <span className="text-xs text-slate-500 font-medium">OSHA Compliance & Mitigation</span>
            </div>
            <h1 className="text-2xl font-black text-slate-900 mt-1">
              Safety Audit Board & Corrective Actions
            </h1>
            <p className="text-xs text-slate-600 mt-0.5">
              Review filed hazards, assign preventative remediations, and sign off verified inspections.
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

      {/* Reports Board */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-900">Workplace Incidents & Hazard Reports</h2>
          <span className="text-xs text-slate-500">{reports.length} reports logged</span>
        </div>

        <div className="divide-y divide-slate-100">
          {reports.length === 0 ? (
            <div className="px-6 py-12 text-center text-slate-400 text-xs">
              No safety hazard reports submitted.
            </div>
          ) : (
            reports.map((r) => (
              <div key={r.id} className="p-6 hover:bg-slate-50/50 transition space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <span className={`px-2.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                      r.severity === 'critical'
                        ? 'bg-rose-100 text-rose-800 border border-rose-300'
                        : r.severity === 'high'
                        ? 'bg-amber-100 text-amber-800'
                        : 'bg-slate-100 text-slate-800'
                    }`}>
                      {r.severity}
                    </span>
                    <span className="text-xs font-bold text-slate-900 capitalize">{r.category.replace('_', ' ')}</span>
                    <span className="text-xs text-slate-400">•</span>
                    <span className="text-xs text-slate-600 font-medium">{r.workplace_name}</span>
                  </div>

                  <div className="flex items-center space-x-3">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                      r.status === 'resolved'
                        ? 'bg-emerald-100 text-emerald-800'
                        : r.status === 'corrective_action_pending'
                        ? 'bg-amber-100 text-amber-800'
                        : 'bg-sky-100 text-sky-800'
                    }`}>
                      {r.status.replace(/_/g, ' ')}
                    </span>
                    <button
                      onClick={() => setSelectedReportId(r.id)}
                      className="px-2.5 py-1 bg-amber-600 hover:bg-amber-700 text-white rounded text-xs font-semibold shadow transition"
                    >
                      + Action Plan
                    </button>
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-bold text-slate-900">{r.title}</h3>
                  <p className="text-xs text-slate-700 mt-1 leading-relaxed bg-slate-50 p-3 rounded-xl border border-slate-200">
                    {r.description}
                  </p>
                </div>

                <div className="text-[11px] text-slate-400 flex items-center space-x-2">
                  <span>Reported by: <span className="font-semibold text-slate-600">{r.reporter_name}</span></span>
                  <span>•</span>
                  <span>Date: {new Date(r.created_at).toLocaleDateString()}</span>
                  <span>•</span>
                  <span>Case ID: #{r.id.slice(0, 8)}</span>
                </div>

                {/* Corrective Action Trail */}
                {r.actions && r.actions.length > 0 && (
                  <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                      Corrective Action Plan & Verified Sign-Off
                    </span>
                    {r.actions.map((act) => (
                      <div key={act.id} className="p-3 bg-white rounded-lg border border-slate-200 text-xs space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-slate-900">{act.action_description}</span>
                          <div className="flex items-center space-x-2">
                            <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                              act.completed_at ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                            }`}>
                              {act.completed_at ? 'Completed' : `Due: ${act.due_date}`}
                            </span>
                            {!act.completed_at && (
                              <button
                                onClick={() => setVerifyingActionId(act.id)}
                                className="px-2 py-1 bg-emerald-600 hover:bg-emerald-700 text-white text-[10px] font-bold rounded shadow transition"
                              >
                                Verify & Sign Off
                              </button>
                            )}
                          </div>
                        </div>
                        {act.verification_notes && (
                          <p className="text-[11px] text-emerald-800 bg-emerald-50 p-2 rounded border border-emerald-200 font-medium">
                            Safety Sign-Off: {act.verification_notes}
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

      {/* Assign Corrective Action Modal */}
      {selectedReportId && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <form onSubmit={handleAddAction} className="bg-white rounded-2xl shadow-xl max-w-md w-full border border-slate-200 p-6 space-y-4">
            <h3 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-2">
              Assign Remediation Action Plan
            </h3>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Corrective Action Directive</label>
              <textarea
                rows={3}
                value={actionDesc}
                onChange={(e) => setActionDesc(e.target.value)}
                placeholder="e.g. Install 4-inch wood toe-boards along Level 4 scaffolding and inspect rigging fasteners..."
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Due Date</label>
              <input
                type="date"
                value={actionDueDate}
                onChange={(e) => setActionDueDate(e.target.value)}
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500"
              />
            </div>

            <div className="flex justify-end space-x-3 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setSelectedReportId(null)}
                className="px-4 py-2 border border-slate-300 rounded text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submittingAction}
                className="px-4 py-2 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white rounded text-xs font-bold shadow"
              >
                {submittingAction ? 'Assigning...' : 'Assign Action'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Verify Action Modal */}
      {verifyingActionId && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <form onSubmit={handleVerifyAction} className="bg-white rounded-2xl shadow-xl max-w-md w-full border border-slate-200 p-6 space-y-4">
            <h3 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-2">
              Physical Verification & Safety Sign-Off
            </h3>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Inspection & Completion Notes</label>
              <textarea
                rows={3}
                value={verificationNotes}
                onChange={(e) => setVerificationNotes(e.target.value)}
                placeholder="e.g. Physical site inspection completed at 14:00. Guardrails installed, bolted, and certified safe for crew entry."
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500"
              />
            </div>

            <div className="flex justify-end space-x-3 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setVerifyingActionId(null)}
                className="px-4 py-2 border border-slate-300 rounded text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submittingVerify}
                className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 disabled:opacity-50 text-white rounded text-xs font-bold shadow"
              >
                {submittingVerify ? 'Signing off...' : 'Sign Off & Close Hazard'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
