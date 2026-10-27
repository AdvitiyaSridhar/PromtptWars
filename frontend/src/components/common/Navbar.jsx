import React from 'react';
import { useAuth, DEMO_USERS } from '../../context/AuthContext';
import { Shield, User, LogOut, ArrowRightLeft, HardHat, Bike } from 'lucide-react';

export function Navbar() {
  const { user, logout, switchDemoUser } = useAuth();

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

          {/* User profile & Quick Switcher */}
          <div className="flex items-center space-x-3">
            {/* Quick Demo Switcher Dropdown */}
            <div className="relative group">
              <button
                className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 transition"
                title="Switch demo role instantly"
              >
                <ArrowRightLeft className="w-3.5 h-3.5 text-sky-400" />
                <span className="hidden md:inline">Switch Demo Role</span>
              </button>
              <div className="absolute right-0 mt-1 w-64 bg-slate-800 border border-slate-700 rounded-lg shadow-xl py-1.5 hidden group-hover:block z-50">
                <div className="px-3 py-1 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Test Personas
                </div>
                {DEMO_USERS.map((demo) => (
                  <button
                    key={demo.email}
                    onClick={() => switchDemoUser(demo)}
                    className={`w-full text-left px-3 py-2 text-xs flex flex-col hover:bg-slate-700 transition ${
                      user.email === demo.email ? 'bg-sky-950/60 text-sky-300 font-semibold' : 'text-slate-200'
                    }`}
                  >
                    <span>{demo.name}</span>
                    <span className="text-[10px] text-slate-400">{demo.tag}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Current Role Pill */}
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

            {/* Logout */}
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
