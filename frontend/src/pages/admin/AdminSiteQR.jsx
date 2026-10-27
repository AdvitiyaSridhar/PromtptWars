import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { QrCode, Copy, Check, Info, Building, HardHat, Bike } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';

export function AdminSiteQR() {
  const [workplaces, setWorkplaces] = useState([]);
  const [loading, setLoading] = useState(true);
  const [copiedId, setCopiedId] = useState(null);

  useEffect(() => {
    api.get('/workplaces')
      .then((data) => setWorkplaces(data))
      .catch((err) => setError(err.message || 'Failed to load work sites.'))
      .finally(() => setLoading(false));
  }, []);
  const [error, setError] = useState('');

  const handleCopy = (id, token) => {
    navigator.clipboard.writeText(token);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2500);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 text-slate-500 text-sm">
        <div className="w-5 h-5 border-2 border-sky-600 border-t-transparent rounded-full animate-spin mr-2"></div>
        Generating worksite QR passes...
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
                Site Attendance Terminals
              </span>
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-slate-300"></span>
              <span className="text-xs text-slate-500 font-medium">Cryptographic Site Identifiers</span>
            </div>
            <h1 className="text-2xl font-black text-slate-900 mt-1">
              Worksite QR Codes & Posters
            </h1>
            <p className="text-xs text-slate-600 mt-0.5">
              Workers scan these codes at arrival using their FairShift camera. The backend verifies their assigned shift and FatigueGuard eligibility.
            </p>
          </div>
        </div>

        {/* Disclaimer Notice */}
        <div className="mt-4 p-3 bg-amber-50 rounded-xl border border-amber-200 text-xs text-amber-900 flex items-start space-x-2">
          <Info className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
          <p>
            <span className="font-semibold">Verification Boundary: </span>
            Site QR codes identify the site and trigger backend authorization. Verification records worker attendance and audits safety eligibility; it does not physically lock or unlock physical gates or site turnstiles.
          </p>
        </div>
      </div>

      {/* Grid of Workplaces */}
      {error && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {workplaces.map((w) => (
          <div key={w.id} className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  {w.industry_sector === 'construction' ? (
                    <HardHat className="w-4 h-4 text-amber-500" />
                  ) : (
                    <Bike className="w-4 h-4 text-emerald-500" />
                  )}
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-500 capitalize">
                    {w.industry_sector.replace('_', ' ')}
                  </span>
                </div>
                <span className="text-[10px] font-mono text-slate-400">ID: #{w.id.slice(0, 8)}</span>
              </div>

              <h2 className="text-lg font-bold text-slate-900 mt-1">{w.name}</h2>
              <p className="text-xs text-slate-600">{w.address}</p>

              {/* QR Graphic Representation */}
              <div className="mt-4 p-4 bg-slate-50 border border-slate-200 rounded-xl flex flex-col items-center justify-center space-y-2">
                <div className="p-3 bg-white border-2 border-slate-900 rounded-lg shadow-inner">
                  <QRCodeSVG value={w.site_qr_token} size={160} level="M" title={`${w.name} site attendance QR code`} />
                </div>
                <span className="text-[11px] font-semibold text-slate-500">Scan via Worker App Camera</span>
              </div>

              {/* Cryptographic Token */}
              <div className="mt-3">
                <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                  Signed Site Token (Manual Entry Fallback)
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    type="text"
                    readOnly
                    value={w.site_qr_token}
                    className="flex-1 text-xs p-2 bg-slate-100 border border-slate-200 rounded font-mono text-slate-600 select-all"
                  />
                  <button
                    onClick={() => handleCopy(w.id, w.site_qr_token)}
                    className="p-2 bg-slate-900 hover:bg-slate-800 text-white rounded transition"
                    title="Copy Token"
                  >
                    {copiedId === w.id ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 text-[11px] text-slate-400 text-center">
              HMAC SHA-256 Signed • Tamper-resistant
            </div>
          </div>
        ))}
        {workplaces.length === 0 && <p className="rounded-xl border border-dashed p-8 text-center text-slate-500">No work sites have been created for this organization.</p>}
      </div>
    </div>
  );
}
