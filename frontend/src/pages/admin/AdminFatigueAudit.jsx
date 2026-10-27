import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { ShieldAlert, AlertOctagon, CheckCircle2, Clock, FileText, Info, Edit3, Save } from 'lucide-react';

export function AdminFatigueAudit() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [auditNote, setAuditNote] = useState('');

  useEffect(() => {
    loadLogs();
  }, []);

  const loadLogs = async () => {
    try {
      setLoading(true);
      setErrorMsg('');
      const data = await api.get('/fatigue/exceptions');
      setLogs(data);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load fatigue exception logs.');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveAuditNote = async (logId) => {
    try {
      await api.patch(`/fatigue/exceptions/${logId}/review`, {
        admin_audit_notes: auditNote
      });
      setEditingId(null);
      setAuditNote('');
      await loadLogs();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to save audit note.');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 text-slate-500 text-sm">
        <div className="w-5 h-5 border-2 border-sky-600 border-t-transparent rounded-full animate-spin mr-2"></div>
        Loading FatigueGuard violation logs & exception records...
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
                Compliance & Zero-Bypass Safety
              </span>
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-slate-300"></span>
              <span className="text-xs text-slate-500 font-medium">Immutable Exception Log</span>
            </div>
            <h1 className="text-2xl font-black text-slate-900 mt-1">
              Fatigue Exceptions & Rejection Audit Log
            </h1>
            <p className="text-xs text-slate-600 mt-0.5">
              Audits all system rejections for unsafe shift assignments and QR check-in attempts exceeding rest thresholds.
            </p>
          </div>

          <div className="p-3 bg-rose-50 rounded-xl border border-rose-200 text-xs text-rose-900 flex items-start space-x-2 max-w-md">
            <AlertOctagon className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            <p>
              <span className="font-bold">Zero-Bypass Policy: </span>
              No admin override can bypass configured rest thresholds. Exceptions remain permanently rejected and recorded for compliance audits.
            </p>
          </div>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 bg-rose-50 border border-rose-300 rounded-xl text-xs text-rose-800 font-semibold flex items-center space-x-2">
          <AlertOctagon className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Audit Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-900">Recorded Rejection Events</h2>
          <span className="text-xs text-slate-500">{logs.length} violations audited</span>
        </div>

        <div className="divide-y divide-slate-100">
          {logs.length === 0 ? (
            <div className="px-6 py-12 text-center text-slate-400 text-xs">
              No fatigue exceptions or rejected assignments recorded. Workforce is operating within limits.
            </div>
          ) : (
            logs.map((log) => {
              const isEditing = editingId === log.id;
              return (
                <div key={log.id} className="p-6 hover:bg-slate-50/50 transition space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center space-x-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-rose-100 text-rose-800 border border-rose-300">
                        {log.breach_type.replace(/_/g, ' ')}
                      </span>
                      <span className="text-xs font-bold text-slate-900">{log.worker_name}</span>
                      <span className="text-xs text-slate-400">•</span>
                      <span className="text-xs text-slate-500 font-medium">{log.workplace_name}</span>
                    </div>

                    <div className="flex items-center space-x-3 text-xs">
                      <span className="font-mono text-slate-400">
                        {new Date(log.timestamp).toLocaleString()}
                      </span>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                        log.reviewed_by_admin ? 'bg-slate-100 text-slate-700' : 'bg-amber-100 text-amber-800'
                      }`}>
                        {log.reviewed_by_admin ? 'Reviewed' : 'Pending Audit Note'}
                      </span>
                    </div>
                  </div>

                  {/* Rejection Details */}
                  <div className="bg-rose-50/60 p-3.5 rounded-xl border border-rose-200 text-xs text-rose-950 space-y-1">
                    <div className="font-bold flex items-center space-x-1.5">
                      <AlertOctagon className="w-3.5 h-3.5 text-rose-600" />
                      <span className="uppercase tracking-wider text-[10px] text-rose-800 font-bold">
                        Backend Rejection Reason ({log.attempted_action.replace(/_/g, ' ')})
                      </span>
                    </div>
                    <p className="font-medium">{log.rejection_reason}</p>
                    <div className="flex items-center space-x-4 text-[11px] text-rose-800 pt-1">
                      <span>• Policy Required Rest: <span className="font-bold">{log.policy_required_rest}h</span></span>
                      <span>• Actual Rest Elapsed: <span className="font-bold">{log.rest_hours_elapsed}h</span></span>
                      <span>• Worked in 24h: <span className="font-bold">{log.hours_worked_past_24h}h</span></span>
                    </div>
                  </div>

                  {/* Admin Audit Notes Area */}
                  <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 text-xs">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-slate-700 text-[11px] uppercase tracking-wider">
                        Supervisor Compliance Notes:
                      </span>
                      {!isEditing && (
                        <button
                          onClick={() => { setEditingId(log.id); setAuditNote(log.admin_audit_notes || ''); }}
                          className="text-sky-600 hover:text-sky-800 font-semibold text-[11px] flex items-center space-x-1"
                        >
                          <Edit3 className="w-3 h-3" />
                          <span>{log.admin_audit_notes ? 'Edit Note' : 'Add Audit Note'}</span>
                        </button>
                      )}
                    </div>

                    {isEditing ? (
                      <div className="space-y-2 mt-2">
                        <textarea
                          rows={2}
                          value={auditNote}
                          onChange={(e) => setAuditNote(e.target.value)}
                          placeholder="e.g. Confirmed rejection. Reassigned shift to preserve mandatory 11h rest gap..."
                          className="w-full p-2 text-xs bg-white border border-slate-300 rounded focus:ring-2 focus:ring-sky-500 text-slate-800"
                        />
                        <div className="flex justify-end space-x-2">
                          <button
                            type="button"
                            onClick={() => setEditingId(null)}
                            className="px-2.5 py-1 text-[11px] border border-slate-300 rounded text-slate-600 hover:bg-slate-100"
                          >
                            Cancel
                          </button>
                          <button
                            type="button"
                            onClick={() => handleSaveAuditNote(log.id)}
                            className="px-3 py-1 text-[11px] bg-slate-900 hover:bg-slate-800 text-white font-semibold rounded flex items-center space-x-1"
                          >
                            <Save className="w-3 h-3" />
                            <span>Save Note</span>
                          </button>
                        </div>
                      </div>
                    ) : (
                      <p className="text-slate-600 text-xs italic">
                        {log.admin_audit_notes || 'No supervisor notes recorded yet.'}
                      </p>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
