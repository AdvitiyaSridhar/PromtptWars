import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { DollarSign, AlertCircle, FileText, CheckCircle, Clock, ShieldCheck, ChevronDown, ChevronUp } from 'lucide-react';

export function WorkerEarnings({ onFileDispute }) {
  const [ledger, setLedger] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    loadLedger();
  }, []);

  const loadLedger = async () => {
    try {
      setLoading(true);
      setErrorMsg('');
      const data = await api.get('/ledger/worker');
      setLedger(data);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load earnings ledger.');
    } finally {
      setLoading(false);
    }
  };

  const totalGross = ledger.reduce((acc, curr) => acc + parseFloat(curr.gross_pay || 0), 0);
  const totalDeductions = ledger.reduce((acc, curr) => acc + parseFloat(curr.total_deductions || 0), 0);
  const totalNet = ledger.reduce((acc, curr) => acc + parseFloat(curr.net_pay || 0), 0);

  // Invariant verification
  const invariantHolds = Math.abs((totalGross - totalDeductions) - totalNet) < 0.01;

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 text-slate-500 text-sm">
        <div className="w-5 h-5 border-2 border-sky-600 border-t-transparent rounded-full animate-spin mr-2"></div>
        Loading verified earnings & deduction ledger...
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Header & Invariant Card */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Transparent Compensation
              </span>
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-slate-300"></span>
              <span className="text-xs text-slate-500 font-medium">Immutable Records</span>
            </div>
            <h1 className="text-2xl font-black text-slate-900 mt-1">
              Work & Earnings Ledger
            </h1>
            <p className="text-xs text-slate-600 mt-0.5">
              Every completed shift is cryptographically calculated and audited against authorized deductions.
            </p>
          </div>

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-700 flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            <div>
              <span className="font-semibold text-slate-900">Arithmetic Invariant: </span>
              <span className="font-mono text-[11px] text-slate-600">net_pay = gross_pay - deductions</span>
              {invariantHolds && (
                <span className="ml-1.5 inline-block px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                  Verified
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Totals Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6">
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Total Gross Pay</span>
            <div className="text-2xl font-black text-slate-900 mt-1 font-mono">${totalGross.toFixed(2)}</div>
            <span className="text-[10px] text-slate-500">Base hours + overtime</span>
          </div>

          <div className="bg-rose-50/60 p-4 rounded-xl border border-rose-200">
            <span className="text-xs font-bold text-rose-700 uppercase tracking-wider">Itemized Deductions</span>
            <div className="text-2xl font-black text-rose-900 mt-1 font-mono">-${totalDeductions.toFixed(2)}</div>
            <span className="text-[10px] text-rose-600">Gear, tools, authorized advances</span>
          </div>

          <div className="bg-emerald-50/80 p-4 rounded-xl border border-emerald-300">
            <span className="text-xs font-bold text-emerald-800 uppercase tracking-wider">Total Net Earnings</span>
            <div className="text-2xl font-black text-emerald-950 mt-1 font-mono">${totalNet.toFixed(2)}</div>
            <span className="text-[10px] text-emerald-700">Available or paid to date</span>
          </div>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 bg-rose-50 border border-rose-300 rounded-xl text-xs text-rose-800 font-semibold flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Ledger Records Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-900">Shift Itemization & Payment Records</h2>
          <span className="text-xs text-slate-500">{ledger.length} ledger records</span>
        </div>

        <div className="divide-y divide-slate-100">
          {ledger.length === 0 ? (
            <div className="px-6 py-12 text-center text-slate-400 text-xs">
              No completed shifts recorded in your earnings ledger yet.
            </div>
          ) : (
            ledger.map((entry) => {
              const isExpanded = expandedId === entry.id;
              return (
                <div key={entry.id} className="p-6 hover:bg-slate-50/50 transition">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    {/* Shift & Workplace Info */}
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-black text-slate-900">{entry.workplace_name}</span>
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
                      <p className="text-xs text-slate-500 font-medium">
                        Shift Date: {entry.shift_start ? new Date(entry.shift_start).toLocaleDateString() : 'N/A'} • 
                        Regular: {entry.regular_hours}h • Overtime: {entry.overtime_hours}h
                      </p>
                      {entry.payment_reference && (
                        <p className="text-[11px] font-mono text-slate-500">
                          Ref: {entry.payment_reference}
                        </p>
                      )}
                    </div>

                    {/* Pay Breakdown Values */}
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

                      <button
                        onClick={() => setExpandedId(isExpanded ? null : entry.id)}
                        className="p-1 text-slate-400 hover:text-slate-700 rounded transition"
                        title="View itemized breakdown"
                      >
                        {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                      </button>
                    </div>
                  </div>

                  {/* Expanded Itemized Deductions & Action Area */}
                  {isExpanded && (
                    <div className="mt-4 pt-4 border-t border-slate-100 bg-slate-50/80 -mx-6 -mb-6 p-6 space-y-4">
                      <div>
                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">
                          Itemized Deductions on this Shift
                        </h4>
                        {entry.deductions.length === 0 ? (
                          <p className="text-xs text-slate-400 italic">No deductions applied. 100% gross pay retained.</p>
                        ) : (
                          <div className="space-y-2">
                            {entry.deductions.map((d) => (
                              <div key={d.id} className="p-3 bg-white rounded-lg border border-slate-200 flex items-center justify-between text-xs">
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

                      {/* Dispute Pay Shortcut */}
                      <div className="flex items-center justify-between pt-2 border-t border-slate-200">
                        <span className="text-xs text-slate-500">
                          Discrepancy in hours, rate, or deduction authorization?
                        </span>
                        <button
                          type="button"
                          onClick={() => onFileDispute(entry.shift_id, entry.id)}
                          className="px-3 py-1.5 bg-purple-700 hover:bg-purple-800 text-white text-xs font-semibold rounded-lg shadow transition"
                        >
                          Dispute this Shift Pay
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
