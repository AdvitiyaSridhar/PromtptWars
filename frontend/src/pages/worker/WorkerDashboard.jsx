import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';
import { QRScannerModal } from '../../components/qr/QRScannerModal';
import { 
  ShieldAlert, Clock, CheckCircle2, AlertOctagon, 
  DollarSign, ArrowRight, HardHat, Bike, Calendar, LogOut, ChevronRight
} from 'lucide-react';

export function WorkerDashboard({ onNavigateTab }) {
  const { user } = useAuth();
  const [shifts, setShifts] = useState([]);
  const [workplaces, setWorkplaces] = useState([]);
  const [fatigueInfo, setFatigueInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [qrModalOpen, setQrModalOpen] = useState(false);
  const [attendanceMode, setAttendanceMode] = useState('check-in');
  const [errorMsg, setErrorMsg] = useState('');

  const loadData = async () => {
    try {
      setLoading(true);
      setErrorMsg('');
      const [shiftsData, placesData, fatigueData] = await Promise.all([
        api.get('/shifts'),
        api.get('/workplaces'),
        api.get(`/fatigue/eligibility/${user.id}`)
      ]);
      setShifts(shiftsData);
      setWorkplaces(placesData);
      setFatigueInfo(fatigueData);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load worker dashboard.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [user.id]);

  const activeShift = shifts.find((s) => s.status === 'in_progress');
  const upcomingShift = shifts
    .filter((shift) => shift.status === 'scheduled')
    .sort((a, b) => new Date(a.scheduled_start) - new Date(b.scheduled_start))[0];

  const handleCheckinSuccess = async () => {
    await loadData();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 text-slate-500 text-sm">
        <div className="w-5 h-5 border-2 border-sky-600 border-t-transparent rounded-full animate-spin mr-2"></div>
        Loading worker workspace & safety status...
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Worker Greeting & Fatigue Status Card */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                {user.industry_sector === 'construction' ? 'Construction Field Portal' : 'Gig Courier Portal'}
              </span>
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-slate-300"></span>
              <span className="text-xs text-slate-500 font-medium">Worker ID: #{user.id.slice(0, 8)}</span>
            </div>
            <h1 className="text-2xl font-black text-slate-900 mt-1">
              Welcome back, {user.full_name}
            </h1>
            <p className="text-xs text-slate-600 mt-0.5">
              Governed by <span className="font-semibold text-slate-800">{fatigueInfo?.policy_applied}</span>
            </p>
          </div>

          {/* FatigueGuard Eligibility Chip */}
          {fatigueInfo && (
            <div className={`p-4 rounded-xl border flex items-center space-x-3.5 ${
              fatigueInfo.is_eligible
                ? 'bg-emerald-50 border-emerald-300 text-emerald-950'
                : 'bg-rose-50 border-rose-300 text-rose-950'
            }`}>
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${
                fatigueInfo.is_eligible ? 'bg-emerald-600 text-white' : 'bg-rose-600 text-white'
              }`}>
                {fatigueInfo.is_eligible ? (
                  <CheckCircle2 className="w-5 h-5" />
                ) : (
                  <AlertOctagon className="w-5 h-5" />
                )}
              </div>
              <div className="text-left">
                <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  FatigueGuard Status
                </div>
                <div className="text-sm font-black">
                  {fatigueInfo.is_eligible ? 'Eligible to Work' : 'Blocked by Rest Rules'}
                </div>
                <div className="text-[11px] opacity-80">
                  {fatigueInfo.is_eligible
                    ? `${fatigueInfo.rest_hours_elapsed}h rest elapsed • ${fatigueInfo.hours_worked_past_24h}h worked in 24h`
                    : fatigueInfo.rejection_reason}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Notifications / Feedback */}
      {errorMsg && (
        <div className="p-4 bg-rose-50 border border-rose-300 rounded-xl text-xs text-rose-800 font-semibold flex items-center space-x-2">
          <AlertOctagon className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Active Shift / QR Check-In Callout */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Active Shift Card */}
        {activeShift ? (
          <div className="bg-sky-950 text-white p-6 rounded-2xl shadow-md border border-sky-800 flex flex-col justify-between">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 text-[11px] font-bold uppercase tracking-wider border border-emerald-500/40 animate-pulse">
                  Shift in Progress
                </span>
                <span className="text-xs text-slate-400 font-mono">
                  Rate: ${activeShift.base_hourly_rate}/hr
                </span>
              </div>
              <h2 className="text-lg font-bold text-white">{activeShift.workplace_name}</h2>
              <p className="text-xs text-slate-300 flex items-center space-x-1">
                <Clock className="w-3.5 h-3.5 text-sky-400" />
                <span>
                  Checked in at: {new Date(activeShift.actual_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </p>
            </div>

            <div className="mt-6 pt-4 border-t border-sky-900/60 flex items-center justify-between">
              <span className="text-xs text-slate-400">Ready to conclude shift?</span>
              <button
                type="button"
                onClick={() => {
                  setAttendanceMode('check-out');
                  setQrModalOpen(true);
                }}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-white text-xs font-bold rounded-lg shadow transition flex items-center space-x-1.5"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Scan site QR to check out</span>
              </button>
            </div>
          </div>
        ) : upcomingShift ? (
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col justify-between">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="px-2.5 py-1 rounded-full bg-amber-100 text-amber-800 text-[11px] font-bold uppercase tracking-wider">
                  Upcoming Shift
                </span>
                <span className="text-xs text-slate-500 font-mono">
                  Rate: ${upcomingShift.base_hourly_rate}/hr
                </span>
              </div>
              <h2 className="text-lg font-bold text-slate-900">{upcomingShift.workplace_name}</h2>
              <div className="text-xs text-slate-600 space-y-1">
                <p className="flex items-center space-x-1">
                  <Calendar className="w-3.5 h-3.5 text-slate-400" />
                  <span>
                    Scheduled: {new Date(upcomingShift.scheduled_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} — {new Date(upcomingShift.scheduled_end).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </p>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between">
              <span className="text-xs text-slate-500">At worksite?</span>
              <button
                type="button"
                onClick={() => {
                  setAttendanceMode('check-in');
                  setQrModalOpen(true);
                }}
                className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white text-xs font-bold rounded-lg shadow transition flex items-center space-x-1.5"
              >
                <span>Scan Site QR to Check In</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-slate-50 p-6 rounded-2xl border border-slate-200 text-center flex flex-col items-center justify-center space-y-3">
            <Clock className="w-8 h-8 text-slate-400" />
            <div>
              <p className="text-sm font-bold text-slate-800">No Shifts Scheduled Today</p>
              <p className="text-xs text-slate-500">Contact your site supervisor or dispatch manager to assign upcoming work.</p>
            </div>
          </div>
        )}

        {/* Quick Actions Card */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col justify-between">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-3">
              Worker Protection Actions
            </h2>
            <div className="space-y-2.5">
              <button
                onClick={() => {
                  setAttendanceMode('check-in');
                  setQrModalOpen(true);
                }}
                className="w-full text-left p-3 rounded-xl bg-slate-50 hover:bg-sky-50 border border-slate-200 hover:border-sky-300 transition flex items-center justify-between text-xs font-semibold text-slate-800"
              >
                <div className="flex items-center space-x-2.5">
                  <div className="w-7 h-7 rounded-lg bg-sky-100 text-sky-700 flex items-center justify-center font-bold">
                    QR
                  </div>
                  <span>Scan Site QR Attendance</span>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-400" />
              </button>

              <button
                onClick={() => onNavigateTab('earnings')}
                className="w-full text-left p-3 rounded-xl bg-slate-50 hover:bg-emerald-50 border border-slate-200 hover:border-emerald-300 transition flex items-center justify-between text-xs font-semibold text-slate-800"
              >
                <div className="flex items-center space-x-2.5">
                  <div className="w-7 h-7 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold">
                    $
                  </div>
                  <span>View Earnings & Itemized Deductions</span>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-400" />
              </button>

              <button
                onClick={() => onNavigateTab('safety')}
                className="w-full text-left p-3 rounded-xl bg-slate-50 hover:bg-amber-50 border border-slate-200 hover:border-amber-300 transition flex items-center justify-between text-xs font-semibold text-slate-800"
              >
                <div className="flex items-center space-x-2.5">
                  <div className="w-7 h-7 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center font-bold">
                    !
                  </div>
                  <span>Report Workplace Hazard (Anonymous or Open)</span>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-400" />
              </button>

              <button
                onClick={() => onNavigateTab('disputes')}
                className="w-full text-left p-3 rounded-xl bg-slate-50 hover:bg-purple-50 border border-slate-200 hover:border-purple-300 transition flex items-center justify-between text-xs font-semibold text-slate-800"
              >
                <div className="flex items-center space-x-2.5">
                  <div className="w-7 h-7 rounded-lg bg-purple-100 text-purple-700 flex items-center justify-center font-bold">
                    #
                  </div>
                  <span>Fair-Work Resolution & Pay Dispute Tracker</span>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-400" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Shifts History Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-900">Assigned Shift History</h2>
          <span className="text-xs text-slate-500">{shifts.length} total shifts recorded</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
              <tr>
                <th className="px-6 py-3">Site / Workplace</th>
                <th className="px-6 py-3">Scheduled Window</th>
                <th className="px-6 py-3">Actual Hours</th>
                <th className="px-6 py-3">Base Rate</th>
                <th className="px-6 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {shifts.length === 0 ? (
                <tr>
                  <td colSpan="5" className="px-6 py-8 text-center text-slate-400">
                    No shifts found for this account.
                  </td>
                </tr>
              ) : (
                shifts.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-50/70 transition">
                    <td className="px-6 py-3.5 font-bold text-slate-900">{s.workplace_name}</td>
                    <td className="px-6 py-3.5 text-slate-600">
                      {new Date(s.scheduled_start).toLocaleDateString()} {new Date(s.scheduled_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} — {new Date(s.scheduled_end).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="px-6 py-3.5 font-mono text-slate-800">
                      {s.actual_start && s.actual_end ? (
                        `${((new Date(s.actual_end) - new Date(s.actual_start)) / 3600000).toFixed(1)} hrs`
                      ) : s.actual_start ? (
                        <span className="text-sky-600 font-semibold">Active now</span>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-6 py-3.5 font-mono">${s.base_hourly_rate}/hr</td>
                    <td className="px-6 py-3.5">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                        s.status === 'completed'
                          ? 'bg-emerald-100 text-emerald-800'
                          : s.status === 'in_progress'
                          ? 'bg-sky-100 text-sky-800'
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

      {/* QR Scanner Modal */}
      <QRScannerModal
        isOpen={qrModalOpen}
        onClose={() => setQrModalOpen(false)}
        onCheckinSuccess={handleCheckinSuccess}
        availableSites={workplaces}
        attendanceMode={attendanceMode}
        activeShiftId={activeShift?.id}
      />
    </div>
  );
}
