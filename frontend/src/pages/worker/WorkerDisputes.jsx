import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { Scale, AlertCircle, CheckCircle2, Clock, FileText, Plus, ShieldCheck, ArrowRight, UserCheck } from 'lucide-react';

export function WorkerDisputes({ prefillShiftId, prefillLedgerId }) {
  const [disputes, setDisputes] = useState([]);
  const [shifts, setShifts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [showForm, setShowForm] = useState(false);

  // Form fields
  const [shiftId, setShiftId] = useState(prefillShiftId || '');
  const [disputeType, setDisputeType] = useState('unauthorized_deduction');
  const [claimedAmount, setClaimedAmount] = useState('');
  const [explanation, setExplanation] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);

  useEffect(() => {
    loadData();
    if (prefillShiftId) {
      setShiftId(prefillShiftId);
      setShowForm(true);
    }
  }, [prefillShiftId]);

  const loadData = async () => {
    try {
      setLoading(true);
      setErrorMsg('');
      const [disputesData, shiftsData] = await Promise.all([
        api.get('/disputes'),
        api.get('/shifts')
      ]);
      setDisputes(disputesData);
      setShifts(shiftsData.filter((s) => s.status === 'completed'));
      if (shiftsData.length > 0 && !shiftId && !prefillShiftId) {
        setShiftId(shiftsData[0].id);
      }
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load disputes.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!shiftId || !claimedAmount || !explanation) {
      setErrorMsg('Please specify the shift, claimed amount, and explanation.');
      return;
    }

    try {
      setSubmitting(true);
      setErrorMsg('');
      setSuccessMsg('');

      const newDispute = await api.post('/disputes', {
        shift_id: shiftId,
        ledger_id: prefillLedgerId || null,
        dispute_type: disputeType,
        claimed_amount: parseFloat(claimedAmount),
        worker_explanation: explanation
      });

      if (selectedFile) {
        const formData = new FormData();
        formData.append('file', selectedFile);
        await api.post(`/disputes/${newDispute.id}/evidence`, formData);
      }

      setSuccessMsg(`Dispute filed successfully! Case #${newDispute.id.slice(0, 8)}`);
      setExplanation('');
      setClaimedAmount('');
      setSelectedFile(null);
      setShowForm(false);
      await loadData();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to file dispute.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 text-slate-500 text-sm">
        <div className="w-5 h-5 border-2 border-sky-600 border-t-transparent rounded-full animate-spin mr-2"></div>
        Loading Fair-Work resolution tracker...
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
                Transparent Resolution
              </span>
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-slate-300"></span>
              <span className="text-xs text-slate-500 font-medium">Human Review Accountability</span>
            </div>
            <h1 className="text-2xl font-black text-slate-900 mt-1">
              Fair-Work Evidence & Dispute Tracker
            </h1>
            <p className="text-xs text-slate-600 mt-0.5">
              Submit evidence-backed claims for unpaid overtime, unauthorized deductions, or rate mismatches.
            </p>
          </div>

          <button
            onClick={() => setShowForm(!showForm)}
            className="px-4 py-2 bg-purple-700 hover:bg-purple-800 text-white text-xs font-bold rounded-xl shadow transition flex items-center space-x-1.5 self-start md:self-auto"
          >
            <Plus className="w-4 h-4" />
            <span>{showForm ? 'Cancel Dispute' : 'File New Dispute'}</span>
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
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Dispute Submission Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white rounded-2xl p-6 shadow-sm border border-purple-200 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
              <Scale className="w-4 h-4 text-purple-700" />
              <span>File a Fair-Work Compensation Claim</span>
            </h2>
            <span className="text-xs text-slate-500">Traceable human review</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Referenced Shift</label>
              <select
                value={shiftId}
                onChange={(e) => setShiftId(e.target.value)}
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-purple-500 text-slate-800"
              >
                {shifts.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.workplace_name} ({new Date(s.scheduled_start).toLocaleDateString()})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Dispute Reason</label>
              <select
                value={disputeType}
                onChange={(e) => setDisputeType(e.target.value)}
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-purple-500 text-slate-800"
              >
                <option value="unauthorized_deduction">Unauthorized Gear / Pay Deduction</option>
                <option value="unpaid_hours">Unpaid Regular or Overtime Hours</option>
                <option value="wrong_rate">Incorrect Base Hourly Rate</option>
                <option value="missing_break">Missed Mandatory Break Penalty</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Claimed Amount ($ USD)</label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={claimedAmount}
                onChange={(e) => setClaimedAmount(e.target.value)}
                placeholder="e.g. 35.00"
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-purple-500 text-slate-800 font-mono"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">Detailed Explanation & Narrative</label>
            <textarea
              rows={3}
              value={explanation}
              onChange={(e) => setExplanation(e.target.value)}
              placeholder="Cite what was omitted or improperly deducted, agreement clauses, tool-crib return receipts, or supervisor promises..."
              className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-purple-500 text-slate-800"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">Upload Proof / Receipt (Optional)</label>
            <input
              type="file"
              accept="image/*,application/pdf"
              onChange={(e) => setSelectedFile(e.target.files[0] || null)}
              className="w-full text-xs p-2 bg-slate-50 border border-slate-300 rounded-lg file:mr-3 file:py-1 file:px-2.5 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-slate-800 file:text-white hover:file:bg-slate-700"
            />
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
              className="px-5 py-2 bg-purple-700 hover:bg-purple-800 disabled:opacity-50 text-white text-xs font-bold rounded-lg shadow transition"
            >
              {submitting ? 'Filing...' : 'Submit Dispute'}
            </button>
          </div>
        </form>
      )}

      {/* Disputes History List */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-900">Your Filed Disputes & Resolution Outcomes</h2>
          <span className="text-xs text-slate-500">{disputes.length} cases tracked</span>
        </div>

        <div className="divide-y divide-slate-100">
          {disputes.length === 0 ? (
            <div className="px-6 py-12 text-center text-slate-400 text-xs">
              No disputes filed on your shifts. All ledger entries match attendance records.
            </div>
          ) : (
            disputes.map((d) => (
              <div key={d.id} className="p-6 hover:bg-slate-50/50 transition space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold text-slate-900 capitalize">
                      {d.dispute_type.replace(/_/g, ' ')}
                    </span>
                    <span className="text-xs text-slate-400">•</span>
                    <span className="text-xs text-slate-500 font-medium">{d.workplace_name}</span>
                  </div>

                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase self-start sm:self-auto ${
                    d.status === 'resolved_upheld'
                      ? 'bg-emerald-100 text-emerald-800'
                      : d.status === 'resolved_rejected'
                      ? 'bg-rose-100 text-rose-800'
                      : 'bg-purple-100 text-purple-800'
                  }`}>
                    {d.status.replace(/_/g, ' ')}
                  </span>
                </div>

                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-[11px] text-slate-500 font-medium">Claimed Amount: </span>
                    <span className="text-sm font-bold font-mono text-purple-900">${d.claimed_amount}</span>
                  </div>
                  {d.settled_amount !== null && (
                    <div className="text-right">
                      <span className="text-[11px] text-slate-500 font-medium">Settled / Awarded: </span>
                      <span className="text-sm font-bold font-mono text-emerald-800">${d.settled_amount}</span>
                    </div>
                  )}
                </div>

                <p className="text-xs text-slate-700 bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <span className="font-semibold block text-slate-900 mb-0.5">Worker Narrative:</span>
                  {d.worker_explanation}
                </p>

                {d.resolution_notes && (
                  <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200 text-xs text-emerald-900 space-y-1">
                    <div className="font-bold flex items-center space-x-1.5">
                      <ShieldCheck className="w-4 h-4 text-emerald-600" />
                      <span>Reviewer Resolution Notes (Reviewed by {d.reviewer_name || 'Administrator'}):</span>
                    </div>
                    <p>{d.resolution_notes}</p>
                    {d.status === 'resolved_upheld' && (
                      <p className="text-[11px] text-emerald-700 font-semibold mt-1">
                        +${d.settled_amount} adjustment credit was automatically posted to your Earnings Ledger.
                      </p>
                    )}
                  </div>
                )}

                <div className="text-[10px] text-slate-400">
                  Case ID: #{d.id} • Filed: {new Date(d.created_at).toLocaleDateString()}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
