import React from 'react';
import { ShieldCheck, Zap } from 'lucide-react';
import { RoleSwitcher, UserRole } from './RoleSwitcher';
import { HealthIndicator } from './HealthIndicator';

interface HeaderProps {
  currentRole: UserRole;
  onRoleChange: (role: UserRole) => void;
}

export const Header: React.FC<HeaderProps> = ({ currentRole, onRoleChange }) => {
  return (
    <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-xl border-b border-slate-800/60 px-2.5 sm:px-4 lg:px-8 py-2 sm:py-3">
      {/* Subtle top accent line */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent" />

      <div className="max-w-7xl mx-auto flex items-center justify-between gap-2 sm:gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="relative w-9 h-9">
            <div className="absolute inset-0 rounded-xl bg-gradient-to-tr from-cyan-500 via-indigo-500 to-rose-500 blur-sm opacity-60" />
            <div className="relative w-9 h-9 rounded-xl bg-slate-950 border border-slate-700/60 flex items-center justify-center">
              <Zap className="w-4 h-4 text-cyan-400" />
            </div>
          </div>
          <div className="hidden sm:block">
            <span className="text-lg font-extrabold tracking-tight bg-gradient-to-r from-cyan-400 via-sky-200 to-white bg-clip-text text-transparent">
              upay Pulse
            </span>
            <p className="text-[10px] text-slate-500 leading-none mt-0.5">MFS Intelligence Platform</p>
          </div>
        </div>

        {/* Role Switcher — center */}
        <div className="flex-1 flex justify-center">
          <RoleSwitcher currentRole={currentRole} onRoleChange={onRoleChange} />
        </div>

        {/* Right side */}
        <div className="flex items-center gap-2 shrink-0">
          <HealthIndicator />
          <div className="hidden lg:flex items-center gap-1.5 text-[11px] text-slate-500 bg-slate-900/60 border border-slate-800 px-2.5 py-1 rounded-full">
            <ShieldCheck className="w-3 h-3 text-emerald-400" />
            <span>Sandbox</span>
          </div>
        </div>
      </div>
    </header>
  );
};
