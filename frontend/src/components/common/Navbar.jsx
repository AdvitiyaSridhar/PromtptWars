import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { Shield, LogOut, HardHat, Bike } from 'lucide-react';

export function Navbar() {
  const { user, logout } = useAuth();

  if (!user) return null;

  return (
    <header className="bg-slate-900 text-white shadow-md border-b border-slate-800 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-sky-500 flex items-center justify-center font-bold text-white shadow-md">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <span className="text-xl font-black tracking-tight text-white flex items-center space-x-1">
                <span>Fair</span>
                <span className="text-sky-400">Shift</span>
              </span>
              <p className="text-[10px] text-slate-400 font-medium uppercase tracking-wider hidden sm:block">
                Worker Protection & FatigueGuard
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 bg-slate-800/80 px-3 py-1.5 rounded-full border border-slate-700 text-xs">
              {user.industry_sector === 'construction' ? (
                <HardHat className="w-4 h-4 text-amber-400" />
              ) : (
                <Bike className="w-4 h-4 text-emerald-400" />
              )}
              <span className="font-semibold text-white truncate max-w-[120px] sm:max-w-none">
                {user.full_name}
              </span>
              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-sky-900/80 text-sky-300 border border-sky-700/50">
                {user.role.replace('_', ' ')}
              </span>
            </div>

            <button
              onClick={logout}
              className="p-2 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition"
              title="Sign Out"
              aria-label="Sign out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
