import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { DollarSign, CheckCircle2, AlertTriangle, Plus, ShieldCheck, FileText, Check, ChevronDown, ChevronUp } from 'lucide-react';

export function AdminPayrollLedger() {
  const [ledgerData, setLedgerData] = useState({ entries: [], summary: {} });
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [expandedId, setExpandedId] = useState(null);

  // Deduction Form State
  const [showDeductModal, setShowDeductModal] = useState(false);
  const [targetLedgerId, setTargetLedgerId] = useState('');
  const [deductCategory, setDeductCategory] = useState('equipment_rental');
  const [deductAmount, setDeductAmount] = useState('');
  const [deductDesc, setDeductDesc] = useState('');
  const [deductDocRef, setDeductDocRef] = useState('');
  const [submittingDeduct, setSubmittingDeduct] = useState(false);

  useEffect(() => {
    loadLedger();
  }, []);

  const loadLedger = async () => {
    try {
      setLoading(true);
      setErrorMsg('');
      const data = await api.get('/ledger/admin');
      setLedgerData(data);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load payroll ledger.');
    } finally {
      setLoading(false);
    }
  };

  const handleAddDeduction = async (e) => {
    e.preventDefault();
    if (!targetLedgerId || !deductAmount || !deductDesc) {
      setErrorMsg('Please specify all deduction fields.');
      return;
    }

    try {
      setSubmittingDeduct(true);
      setErrorMsg('');
      await api.post(`/ledger/${targetLedgerId}/deductions`, {
        category: deductCategory,
        amount: parseFloat(deductAmount),
        description: deductDesc,
        authorization_doc_ref: deductDocRef || null
      });

      setSuccessMsg('Legitimate deduction authorized and recorded in ledger.');
      setShowDeductModal(false);
      setDeductAmount('');
      setDeductDesc('');
      setDeductDocRef('');
      await loadLedger();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to record deduction.');
    } finally {
      setSubmittingDeduct(false);
    }
  };

  const handleUpdateStatus = async (ledgerId, newStatus) => {
    try {
      setErrorMsg('');
      const ref = newStatus === 'paid' ? `DISBURSE-${Date.now().toString().slice(-6)}` : null;
      await api.patch(`/ledger/${ledgerId}/status`, {
        payment_status: newStatus,
        payment_reference: ref
      });
      setSuccessMsg(`Payment status updated to "${newStatus}".`);
      await loadLedger();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to update payment status.');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 text-slate-500 text-sm">
        <div className="w-5 h-5 border-2 border-sky-600 border-t-transparent rounded-full animate-spin mr-2"></div>
        Loading payroll ledger & itemized calculations...
      </div>
    );
  }

  const { entries, summary } = ledgerData;

  return (
    <div className="space-y-6 pb-12">
      {/* Header & Arithmetic Invariant Card */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Financial Operations & Audit
              </span>
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-slate-300"></span>
              <span className="text-xs text-slate-500 font-medium">Audited Compensation</span>
            </div>
            <h1 className="text-2xl font-black text-slate-900 mt-1">
              Employer Payroll Ledger
            </h1>
            <p className="text-xs text-slate-600 mt-0.5">
              Review completed shifts, authorize itemized deductions, and disburse verified worker wages.
            </p>
          </div>

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-700 flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            <div>
              <span className="font-semibold text-slate-900">Ledger Invariant: </span>
              <span className="font-mono text-[11px] text-slate-600">net = gross - deductions</span>
              {summary.arithmetic_invariant_verified && (
                <span className="ml-1.5 inline-block px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                  Strictly Verified
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Totals Computed from Real Database Records */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mt-6">
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Completed Shifts</span>
            <div className="text-2xl font-black text-slate-900 mt-1 font-mono">{summary.total_shifts_recorded}</div>
            <span className="text-[10px] text-slate-500">Stored shift records</span>
          </div>

          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Total Gross Wages</span>
            <div className="text-2xl font-black text-slate-900 mt-1 font-mono">${summary.total_gross_pay}</div>
            <span className="text-[10px] text-slate-500">Regular + overtime hours</span>
          </div>

          <div className="bg-rose-50/60 p-4 rounded-xl border border-rose-200">
            <span className="text-xs font-bold text-rose-700 uppercase tracking-wider">Total Deductions</span>
            <div className="text-2xl font-black text-rose-900 mt-1 font-mono">-${summary.total_deductions}</div>
            <span className="text-[10px] text-rose-600">Itemized & authorized</span>
          </div>

          <div className="bg-emerald-50/80 p-4 rounded-xl border border-emerald-300">
            <span className="text-xs font-bold text-emerald-800 uppercase tracking-wider">Total Net Payable</span>
            <div className="text-2xl font-black text-emerald-950 mt-1 font-mono">${summary.total_net_pay}</div>
            <span className="text-[10px] text-emerald-700">Calculated from stored records</span>
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

      {/* Ledger Records Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-900">Shift Itemization & Payment Records</h2>
          <span className="text-xs text-slate-500">{entries.length} shifts recorded</span>
        </div>

        <div className="divide-y divide-slate-100">
          {entries.length === 0 ? (
            <div className="px-6 py-12 text-center text-slate-400 text-xs">
              No completed shifts recorded in payroll yet.
            </div>
          ) : (
            entries.map((entry) => {
              const isExpanded = expandedId === entry.id;
              return (
                <div key={entry.id} className="p-6 hover:bg-slate-50/50 transition space-y-3">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    {/* Worker & Shift Details */}
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-black text-slate-900">{entry.worker_name}</span>
                        <span className="text-xs text-slate-400">•</span>
                        <span className="text-xs font-semibold text-slate-700">{entry.workplace_name}</span>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                          entry.payment_status === 'paid'
                            ? 'bg-emerald-100 text-emerald-800'
                            : entry.payment_status === 'approved'
                            ? 'bg-sky-100 text-sky-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}>
                          {entry.payment_status}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Shift Date: {entry.shift_start ? new Date(entry.shift_start).toLocaleDateString() : 'N/A'} • 
                        Regular: {entry.regular_hours}h • Overtime: {entry.overtime_hours}h
                      </p>
                      {entry.payment_reference && (
                        <p className="text-[11px] font-mono text-slate-500 mt-0.5">
                          Reference: {entry.payment_reference}
                        </p>
                      )}
                    </div>

                    {/* Monetary Breakdown */}
                    <div className="flex items-center space-x-6">
                      <div className="text-right">
                        <span className="text-[11px] text-slate-400 uppercase tracking-wider block">Gross</span>
                        <span className="text-sm font-bold font-mono text-slate-800">${entry.gross_pay}</span>
                      </div>
                      <div className="text-right">
                        <span className="text-[11px] text-rose-500 uppercase tracking-wider block">Deductions</span>
                        <span className="text-sm font-bold font-mono text-rose-700">-${entry.total_deductions}</span>
                      </div>
                      <div className="text-right">
                        <span className="text-[11px] text-emerald-700 uppercase tracking-wider block font-bold">Net Pay</span>
                        <span className="text-base font-black font-mono text-emerald-800">${entry.net_pay}</span>
                      </div>

                      {/* Payment Status Action Buttons */}
                      <div className="flex items-center space-x-2">
                        {entry.payment_status === 'pending' && (
                          <button
                            onClick={() => handleUpdateStatus(entry.id, 'approved')}
                            className="px-2.5 py-1.5 bg-sky-600 hover:bg-sky-700 text-white rounded text-xs font-semibold shadow transition"
                          >
                            Approve
                          </button>
                        )}
                        {entry.payment_status === 'approved' && (
                          <button
                            onClick={() => handleUpdateStatus(entry.id, 'paid')}
                            className="px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-semibold shadow transition"
                          >
                            Mark Paid
                          </button>
                        )}
                        <button
                          onClick={() => {
                            setTargetLedgerId(entry.id);
                            setShowDeductModal(true);
                          }}
                          disabled={entry.payment_status === 'paid'}
                          className="px-2.5 py-1.5 border border-slate-300 hover:bg-slate-100 disabled:opacity-40 text-slate-700 rounded text-xs font-semibold transition"
                          title="Add itemized deduction"
                        >
                          + Deduction
                        </button>
                        <button
                          onClick={() => setExpandedId(isExpanded ? null : entry.id)}
                          className="p-1 text-slate-400 hover:text-slate-700 rounded transition"
                        >
                          {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Expanded Deductions List */}
                  {isExpanded && (
                    <div className="mt-3 pt-3 border-t border-slate-100 bg-slate-50/80 -mx-6 -mb-6 p-4 space-y-2">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                        Itemized Deductions Applied
                      </span>
                      {entry.deductions.length === 0 ? (
                        <p className="text-xs text-slate-400 italic">No deductions applied to this shift.</p>
                      ) : (
                        <div className="space-y-1.5">
                          {entry.deductions.map((d) => (
                            <div key={d.id} className="p-2.5 bg-white rounded border border-slate-200 flex items-center justify-between text-xs">
                              <div>
                                <span className="font-bold text-slate-800 capitalize">{d.category.replace('_', ' ')}: </span>
                                <span className="text-slate-600">{d.description}</span>
                                {d.authorization_doc_ref && (
                                  <span className="text-[10px] text-slate-400 block font-mono">
                                    Auth Doc: {d.authorization_doc_ref}
                                  </span>
                                )}
                              </div>
                              <span className="font-bold font-mono text-rose-700">-${d.amount}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Add Deduction Modal */}
      {showDeductModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <form onSubmit={handleAddDeduction} className="bg-white rounded-2xl shadow-xl max-w-md w-full border border-slate-200 p-6 space-y-4">
            <h3 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-2">
              Record Legitimate, Itemized Deduction
            </h3>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Deduction Category</label>
              <select
                value={deductCategory}
                onChange={(e) => setDeductCategory(e.target.value)}
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500"
              >
                <option value="equipment_rental">Equipment / Gear Rental</option>
                <option value="uniform">Uniform / Safety Gear Replacement</option>
                <option value="transport">Transit / Fuel Surcharge</option>
                <option value="advance">Cash Advance Recovery</option>
                <option value="other">Other Authorized Deduction</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Amount ($ USD)</label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={deductAmount}
                onChange={(e) => setDeductAmount(e.target.value)}
                placeholder="e.g. 25.00"
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500 font-mono"
              />
              <span className="text-[10px] text-slate-500">Invariant: Cannot exceed shift gross earnings.</span>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Mandatory Description / Reason</label>
              <input
                type="text"
                value={deductDesc}
                onChange={(e) => setDeductDesc(e.target.value)}
                placeholder="e.g. Weekly fall-arrest harness rental fee"
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Authorization Doc Reference</label>
              <input
                type="text"
                value={deductDocRef}
                onChange={(e) => setDeductDocRef(e.target.value)}
                placeholder="e.g. TOOL-CRIB-RECEIPT-9081"
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500 font-mono"
              />
            </div>

            <div className="flex justify-end space-x-3 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setShowDeductModal(false)}
                className="px-4 py-2 border border-slate-300 rounded text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submittingDeduct}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white rounded text-xs font-bold shadow"
              >
                {submittingDeduct ? 'Recording...' : 'Record Deduction'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
