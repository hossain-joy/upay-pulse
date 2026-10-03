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
    <header className="sticky top-0 z-50 glass-panel border-b border-slate-800/80 px-4 lg:px-8 py-3.5">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 via-indigo-500 to-rose-500 p-0.5 shadow-lg shadow-cyan-500/20">
            <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
              <Zap className="w-5 h-5 text-cyan-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-cyan-400 via-sky-200 to-white bg-clip-text text-transparent">
                upay Pulse
              </span>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-cyan-950 border border-cyan-500/30 text-cyan-300">
                AI Ecosystem
              </span>
            </div>
            <p className="text-xs text-slate-400">SecurityAI • CustomerAI • AgentAI</p>
          </div>
        </div>

        {/* Role Switcher */}
        <RoleSwitcher currentRole={currentRole} onRoleChange={onRoleChange} />

        {/* Health & Observability */}
        <div className="flex items-center gap-3">
          <HealthIndicator />
          <div className="hidden lg:flex items-center gap-1.5 text-xs text-slate-400 bg-slate-900/60 border border-slate-800 px-3 py-1 rounded-full">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Simulated MFS Sandbox</span>
          </div>
        </div>
      </div>
    </header>
  );
};
