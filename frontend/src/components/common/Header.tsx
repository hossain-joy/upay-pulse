import React from 'react';
import { RoleSwitcher, UserRole } from './RoleSwitcher';
import { HealthIndicator } from './HealthIndicator';

interface HeaderProps {
  currentRole: UserRole;
  onRoleChange: (role: UserRole) => void;
}

export const Header: React.FC<HeaderProps> = ({ currentRole, onRoleChange }) => {
  return (
    <header className="sticky top-0 z-40 bg-slate-950 border-b border-slate-800/80">
      <div className="max-w-7xl mx-auto h-14 px-4 lg:px-8 flex items-center justify-between gap-6">
        {/* Brand */}
        <div className="flex items-center gap-2.5 shrink-0">
          <div className="w-7 h-7 rounded-md bg-white text-slate-950 flex items-center justify-center font-bold text-[13px] tracking-tight select-none">
            u
          </div>
          <div className="hidden sm:flex items-baseline gap-2">
            <span className="text-[15px] font-semibold text-white tracking-tight leading-none">
              upay Pulse
            </span>
            <span className="text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500 leading-none">
              Beta
            </span>
          </div>
        </div>

        {/* Role Switcher — center */}
        <div className="flex-1 flex justify-center min-w-0">
          <RoleSwitcher currentRole={currentRole} onRoleChange={onRoleChange} />
        </div>

        {/* Right side */}
        <div className="flex items-center gap-3 shrink-0">
          <HealthIndicator />
        </div>
      </div>
    </header>
  );
};