import React from 'react';
import { User, Store, ShieldAlert } from 'lucide-react';

export type UserRole = 'CUSTOMER' | 'AGENT' | 'RISK_ANALYST';

interface RoleSwitcherProps {
  currentRole: UserRole;
  onRoleChange: (role: UserRole) => void;
}

const roles: { id: UserRole; label: string; sub: string; icon: React.ReactNode; accent: string; glow: string }[] = [
  {
    id: 'CUSTOMER',
    label: 'Customer',
    sub: 'Financial Portal',
    icon: <User className="w-4 h-4" />,
    accent: 'from-cyan-500 to-blue-500',
    glow: 'shadow-cyan-500/30',
  },
  {
    id: 'AGENT',
    label: 'Agent',
    sub: 'Liquidity Terminal',
    icon: <Store className="w-4 h-4" />,
    accent: 'from-emerald-500 to-teal-500',
    glow: 'shadow-emerald-500/30',
  },
  {
    id: 'RISK_ANALYST',
    label: 'Risk',
    sub: 'Security Console',
    icon: <ShieldAlert className="w-4 h-4" />,
    accent: 'from-rose-500 to-orange-500',
    glow: 'shadow-rose-500/30',
  },
];

export const RoleSwitcher: React.FC<RoleSwitcherProps> = ({ currentRole, onRoleChange }) => {
  return (
    <nav className="flex items-center gap-1.5 p-1 rounded-2xl bg-slate-900/80 border border-slate-700/60 backdrop-blur-md shadow-xl">
      {roles.map((r) => {
        const isActive = currentRole === r.id;
        return (
          <button
            key={r.id}
            onClick={() => onRoleChange(r.id)}
            className={`relative flex items-center gap-2.5 px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-300 ${
              isActive
                ? `bg-gradient-to-r ${r.accent} text-white shadow-lg ${r.glow} scale-[1.03]`
                : 'text-slate-400 hover:text-white hover:bg-slate-800/70'
            }`}
          >
            <span className={`transition-transform duration-300 ${isActive ? 'scale-110' : ''}`}>
              {r.icon}
            </span>
            <span className="flex flex-col items-start leading-none gap-0.5">
              <span className="font-bold tracking-wide">{r.label}</span>
              <span className={`text-[10px] font-normal transition-opacity ${isActive ? 'opacity-80' : 'opacity-0 group-hover:opacity-60'}`}>
                {r.sub}
              </span>
            </span>
            {isActive && (
              <span className="absolute -bottom-0.5 left-1/2 -translate-x-1/2 w-6 h-0.5 rounded-full bg-white/60" />
            )}
          </button>
        );
      })}
    </nav>
  );
};
