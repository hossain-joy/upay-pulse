import React from 'react';
import { User, Store, ShieldAlert } from 'lucide-react';

export type UserRole = 'CUSTOMER' | 'AGENT' | 'RISK_ANALYST';

interface RoleSwitcherProps {
  currentRole: UserRole;
  onRoleChange: (role: UserRole) => void;
}

const roles: { id: UserRole; label: string; icon: React.ReactNode }[] = [
  { id: 'CUSTOMER', label: 'Customer', icon: <User className="w-3.5 h-3.5" /> },
  { id: 'AGENT', label: 'Agent', icon: <Store className="w-3.5 h-3.5" /> },
  { id: 'RISK_ANALYST', label: 'Risk', icon: <ShieldAlert className="w-3.5 h-3.5" /> },
];

export const RoleSwitcher: React.FC<RoleSwitcherProps> = ({ currentRole, onRoleChange }) => {
  return (
    <div className="inline-flex items-center bg-slate-900 border border-slate-800 rounded-md p-0.5 max-w-full overflow-x-auto scrollbar-none">
      {roles.map((r) => {
        const isActive = currentRole === r.id;
        return (
          <button
            key={r.id}
            onClick={() => onRoleChange(r.id)}
            aria-pressed={isActive}
            className={`flex items-center gap-1.5 px-3 h-8 rounded text-[12.5px] font-medium whitespace-nowrap focus:outline-none focus-visible:ring-1 focus-visible:ring-slate-500 transition-colors ${
              isActive
                ? 'bg-white text-slate-950'
                : 'text-slate-400 hover:text-slate-200'
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