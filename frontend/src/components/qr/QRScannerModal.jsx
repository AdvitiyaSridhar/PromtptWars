import React, { useState, useEffect, useRef } from 'react';
import { Html5Qrcode } from 'html5-qrcode';
import { api } from '../../api/client';
import { QrCode, Camera, AlertTriangle, CheckCircle2, X, RefreshCw, KeyRound, Info } from 'lucide-react';

export function QRScannerModal({ isOpen, onClose, onCheckinSuccess, availableSites = [], attendanceMode = 'check-in', activeShiftId }) {
  const [scanning, setScanning] = useState(false);
  const [manualToken, setManualToken] = useState('');
  const [selectedSiteId, setSelectedSiteId] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorData, setErrorData] = useState(null);
  const [successData, setSuccessData] = useState(null);
  const qrRef = useRef(null);
  const html5QrCodeInstance = useRef(null);

  useEffect(() => {
    if (availableSites.length > 0 && !selectedSiteId) {
      setSelectedSiteId(availableSites[0].id);
      setManualToken(availableSites[0].site_qr_token || '');
    }
  }, [availableSites]);

  useEffect(() => {
    if (isOpen) {
      setErrorData(null);
      setSuccessData(null);
    } else {
      stopCamera();
    }
    return () => {
      stopCamera();
    };
  }, [isOpen]);

  const startCamera = async () => {
    setErrorData(null);
    setScanning(true);
    try {
      if (!html5QrCodeInstance.current) {
        html5QrCodeInstance.current = new Html5Qrcode('qr-reader');
      }
      await html5QrCodeInstance.current.start(
        { facingMode: 'environment' },
        { fps: 10, qrbox: { width: 250, height: 250 } },
        (decodedText) => {
          stopCamera();
          handleSubmitToken(decodedText);
        },
        () => {}
      );
    } catch (err) {
      setScanning(false);
      setErrorData({
        message: 'Camera permission denied or camera unavailable. Please use the manual token fallback below.'
      });
    }
  };

  const stopCamera = async () => {
    if (html5QrCodeInstance.current && html5QrCodeInstance.current.isScanning) {
      try {
        await html5QrCodeInstance.current.stop();
      } catch (err) {
        // ignore cleanup error
      }
    }
    setScanning(false);
  };

  const handleSiteSelect = (e) => {
    const siteId = e.target.value;
    setSelectedSiteId(siteId);
    const site = availableSites.find((s) => s.id === siteId);
    if (site) {
      setManualToken(site.site_qr_token || '');
    }
  };

  const handleSubmitToken = async (tokenToSubmit) => {
    const token = tokenToSubmit || manualToken;
    if (!token) {
      setErrorData({ message: 'Please scan or select a valid Site QR token.' });
      return;
    }

    setLoading(true);
    setErrorData(null);
    setSuccessData(null);

    try {
      const request = { scanned_site_token: token };
      const res = attendanceMode === 'check-out'
        ? await api.post(`/shifts/${activeShiftId}/check-out`, request)
        : await api.post('/shifts/check-in', request);
      setSuccessData(res);
      if (onCheckinSuccess) onCheckinSuccess(res);
    } catch (err) {
      setErrorData(err.data?.detail || { message: err.message });
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <QrCode className="w-5 h-5 text-sky-400" />
            <h2 className="text-base font-bold text-white">Site QR Attendance {attendanceMode === 'check-out' ? 'Check-Out' : 'Check-In'}</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-5">
          {/* Disclaimer Banner */}
          <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 text-xs text-amber-900 flex items-start space-x-2">
            <Info className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
            <p>
              FairShift verifies worker identity, scheduled shift window, and FatigueGuard work/rest compliance. 
              <span className="font-semibold ml-1">
                This verification audits safety compliance; it does not physically lock or grant site entry.
              </span>
            </p>
          </div>

          {/* Success State */}
          {successData && (
            <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-300 space-y-2">
              <div className="flex items-center space-x-2 text-emerald-800 font-bold">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                <span>{attendanceMode === 'check-out' ? 'Checked Out Successfully!' : 'Checked In Successfully!'}</span>
              </div>
              <p className="text-xs text-emerald-700">
                {attendanceMode === 'check-out' ? 'Your attendance and earnings ledger were recorded.' : <>Shift status is now <span className="font-semibold text-emerald-900">in progress</span> at {successData.workplace_name}.</>}
              </p>
              <div className="text-[11px] text-emerald-600 bg-white/70 p-2.5 rounded-lg border border-emerald-200">
                {successData.physical_access_note || `${successData.duration_hours} hours recorded. Gross pay: $${successData.gross_pay}; net pay: $${successData.net_pay}.`}
              </div>
              <button
                onClick={onClose}
                className="w-full mt-2 py-2 px-4 bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-semibold rounded-lg shadow transition"
              >
                Close & View Shift
              </button>
            </div>
          )}

          {/* Fatigue / Validation Error Banner */}
          {errorData && (
            <div className="p-4 bg-rose-50 rounded-xl border border-rose-300 space-y-2">
              <div className="flex items-center space-x-2 text-rose-800 font-bold">
                <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0" />
                <span>
                  {errorData.code === 'ELIGIBILITY_BLOCKED_FATIGUE'
                    ? 'Check-In Blocked by FatigueGuard'
                    : errorData.code === 'SCHEDULE_WINDOW_INVALID'
                    ? 'Invalid Shift Time Window'
                    : errorData.code === 'ALREADY_CHECKED_IN'
                    ? 'Already Checked In'
                    : 'Check-In Validation Failed'}
                </span>
              </div>
              <p className="text-xs text-rose-700 font-medium">
                {errorData.reason || errorData.message || (typeof errorData === 'string' ? errorData : 'Check-in rejected.')}
              </p>

              {errorData.code === 'ELIGIBILITY_BLOCKED_FATIGUE' && (
                <div className="bg-white p-3 rounded-lg border border-rose-200 text-xs text-rose-900 space-y-1">
                  <div className="font-semibold">Fatigue Policy Thresholds:</div>
                  <div>• Required Rest: {errorData.required_rest_hours}h</div>
                  <div>• Elapsed Rest: {errorData.rest_hours_elapsed}h</div>
                  {errorData.remaining_rest_needed_hours && (
                    <div className="text-rose-700 font-bold">• Additional Rest Needed: {errorData.remaining_rest_needed_hours}h</div>
                  )}
                  <p className="text-[11px] text-slate-500 mt-1 italic">
                    Attempt logged permanently to the Employer Fatigue Audit Log.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Camera Scanner View */}
          {!successData && (
            <div className="space-y-4">
              <div className="border-2 border-dashed border-slate-300 rounded-xl overflow-hidden bg-slate-100 min-h-[220px] flex flex-col items-center justify-center p-4">
                <div id="qr-reader" className="w-full max-w-[280px]"></div>

                {!scanning && (
                  <div className="text-center space-y-3 py-4">
                    <Camera className="w-10 h-10 text-slate-400 mx-auto" />
                    <div>
                      <p className="text-sm font-semibold text-slate-700">Scan Site QR Code</p>
                      <p className="text-xs text-slate-500">Point device camera at the worksite terminal or poster</p>
                    </div>
                    <button
                      type="button"
                      onClick={startCamera}
                      className="inline-flex items-center space-x-2 px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold shadow transition"
                    >
                      <Camera className="w-4 h-4" />
                      <span>Start Camera Scanner</span>
                    </button>
                  </div>
                )}

                {scanning && (
                  <button
                    type="button"
                    onClick={stopCamera}
                    className="mt-3 px-3 py-1.5 bg-slate-700 hover:bg-slate-800 text-white rounded-lg text-xs font-medium"
                  >
                    Cancel Camera
                  </button>
                )}
              </div>

              {/* Manual / Demo Fallback Divider */}
              <div className="relative flex py-2 items-center">
                <div className="flex-grow border-t border-slate-200"></div>
                <span className="flex-shrink mx-3 text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Or Manual / Demo Fallback
                </span>
                <div className="flex-grow border-t border-slate-200"></div>
              </div>

              {/* Manual Selection Form */}
              <div className="space-y-3 bg-slate-50 p-4 rounded-xl border border-slate-200">
                <label className="block text-xs font-bold text-slate-700">
                  Select Worksite (Demo Fast-Fill)
                </label>
                <select
                  value={selectedSiteId}
                  onChange={handleSiteSelect}
                  className="w-full text-xs p-2.5 bg-white border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500 font-medium text-slate-800"
                >
                  <option value="">-- Choose Worksite --</option>
                  {availableSites.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.industry_sector})
                    </option>
                  ))}
                </select>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Site QR Token
                  </label>
                  <div className="flex space-x-2">
                    <input
                      type="text"
                      value={manualToken}
                      onChange={(e) => setManualToken(e.target.value)}
                      placeholder="HMAC signed site token..."
                      className="flex-1 text-xs p-2.5 bg-white border border-slate-300 rounded-lg font-mono text-slate-800 focus:ring-2 focus:ring-sky-500"
                    />
                    <button
                      type="button"
                      disabled={loading || !manualToken}
                      onClick={() => handleSubmitToken()}
                      className="px-4 py-2 bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white text-xs font-semibold rounded-lg shadow transition flex items-center space-x-1"
                    >
                      {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <KeyRound className="w-3.5 h-3.5" />}
                      <span>Verify</span>
                    </button>
                  </div>
                  <p className="text-[10px] text-slate-500 mt-1">
                    Validates shift schedule, worker ID, and FatigueGuard work/rest thresholds on the backend.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
