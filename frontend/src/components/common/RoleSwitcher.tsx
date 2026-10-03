import React from 'react';
import { User, Store, ShieldAlert } from 'lucide-react';

export type UserRole = 'CUSTOMER' | 'AGENT' | 'RISK_ANALYST';

interface RoleSwitcherProps {
  currentRole: UserRole;
  onRoleChange: (role: UserRole) => void;
}

export const RoleSwitcher: React.FC<RoleSwitcherProps> = ({ currentRole, onRoleChange }) => {
  const roles: { id: UserRole; label: string; icon: React.ReactNode; color: string }[] = [
    {
      id: 'CUSTOMER',
      label: 'Customer App',
      icon: <User className="w-4 h-4" />,
      color: 'from-cyan-500 to-blue-600'
    },
    {
      id: 'AGENT',
      label: 'Agent Terminal',
      icon: <Store className="w-4 h-4" />,
      color: 'from-emerald-500 to-teal-600'
    },
    {
      id: 'RISK_ANALYST',
      label: 'Risk Console',
      icon: <ShieldAlert className="w-4 h-4" />,
      color: 'from-amber-500 to-rose-600'
    }
  ];

  return (
    <div className="flex items-center p-1 bg-slate-900/90 border border-slate-800 rounded-xl shadow-inner">
      {roles.map((r) => {
        const isActive = currentRole === r.id;
        return (
          <button
            key={r.id}
            onClick={() => onRoleChange(r.id)}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${
              isActive
                ? 'bg-gradient-to-r text-white shadow-md ' + r.color
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            {r.icon}
            <span>{r.label}</span>
          </button>
        );
      })}
    </div>
  );
};
