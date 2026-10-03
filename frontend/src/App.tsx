import React, { useState } from 'react';
import { Header } from './components/common/Header';
import { UserRole } from './components/common/RoleSwitcher';
import { 
  ShieldAlert, 
  Lock, 
  Cpu, 
  TrendingUp, 
  Zap, 
  Volume2, 
  QrCode, 
  Layers, 
  Sparkles, 
  ArrowRight,
  AlertCircle,
  Clock,
  CheckCircle2
} from 'lucide-react';

export const App: React.FC = () => {
  const [role, setRole] = useState<UserRole>('CUSTOMER');

  return (
    <div className="min-h-screen bg-[#0B1120] text-slate-100 flex flex-col">
      <Header currentRole={role} onRoleChange={setRole} />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 lg:px-8 py-8">
        
        {/* Banner: Simulated Disclaimer */}
        <div className="mb-8 p-4 rounded-2xl bg-gradient-to-r from-cyan-950/40 via-indigo-950/30 to-slate-900 border border-cyan-500/20 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-slate-200">Educational & Hackathon Prototype Active</h2>
              <p className="text-xs text-slate-400">Operating in safe simulated sandbox mode using synthetic Bangladeshi MFS data.</p>
            </div>
          </div>
          <span className="text-xs font-mono text-cyan-400/90 bg-slate-950/80 px-3 py-1 rounded-full border border-cyan-500/30">
            Phase 2: Foundation Verified
          </span>
        </div>

        {/* Dynamic View based on Active Role */}
        {role === 'CUSTOMER' && (
          <div className="space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
              <div>
                <h1 className="text-2xl font-bold text-white tracking-tight">Customer Financial Intelligence</h1>
                <p className="text-sm text-slate-400">Real-time balances, spending forecasts, emergency freeze & voice coaching.</p>
              </div>
              <div className="flex items-center gap-3">
                <button className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold flex items-center gap-2 shadow-lg shadow-rose-600/20 transition">
                  <Lock className="w-4 h-4" />
                  <span>Master Freeze PIN</span>
                </button>
                <button className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold flex items-center gap-2 shadow-lg shadow-cyan-600/20 transition">
                  <Zap className="w-4 h-4" />
                  <span>Send Money</span>
                </button>
              </div>
            </div>

            {/* Pillar Snapshot Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <div className="glass-panel p-6 rounded-2xl border border-slate-800/80 hover:border-cyan-500/40 transition">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-semibold text-cyan-400 uppercase tracking-wider">Simulated Wallet</span>
                  <span className="text-xs text-slate-500">Live Ledger</span>
                </div>
                <div className="text-3xl font-extrabold text-white mb-1">৳ 500.00</div>
                <p className="text-xs text-slate-400 mb-4">Eligible for upay Grace overdraft: up to ৳50.00</p>
                <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-slate-300 flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-emerald-400" />
                  <span>Cash-flow projected safe for next 18 days</span>
                </div>
              </div>

              <div className="glass-panel p-6 rounded-2xl border border-slate-800/80 hover:border-cyan-500/40 transition">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">Bangla Voice Coach</span>
                  <Volume2 className="w-4 h-4 text-indigo-400" />
                </div>
                <p className="text-xs text-slate-300 mb-3 italic">"এই মাসে আপনার খরচ কেমন হলো? কোনো বাজেট সমস্যা হবে কি?"</p>
                <button className="w-full py-2.5 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-300 text-xs font-semibold flex items-center justify-center gap-2 transition">
                  <span>Start Voice Session</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="glass-panel p-6 rounded-2xl border border-slate-800/80 hover:border-cyan-500/40 transition">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-semibold text-rose-400 uppercase tracking-wider">Security Guard</span>
                  <ShieldAlert className="w-4 h-4 text-rose-400" />
                </div>
                <div className="text-xs text-slate-300 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Account Status:</span>
                    <span className="text-emerald-400 font-semibold flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" /> ACTIVE
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">LightGBM Anomaly Filter:</span>
                    <span className="text-cyan-400 font-mono">0.08 (Low Risk)</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Scam Report Integration:</span>
                    <span className="text-slate-400">Radar Connected</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {role === 'AGENT' && (
          <div className="space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
              <div>
                <h1 className="text-2xl font-bold text-white tracking-tight">Agent / Merchant Intelligence Terminal</h1>
                <p className="text-sm text-slate-400">Cash & float monitoring, surge forecasts, software soundbox & payment badge verification.</p>
              </div>
              <div className="flex items-center gap-3">
                <button className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-2 shadow-lg shadow-emerald-600/20 transition">
                  <Volume2 className="w-4 h-4" />
                  <span>Test Soundbox</span>
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <div className="glass-panel p-6 rounded-2xl border border-slate-800/80">
                <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Current Liquidity</span>
                <div className="mt-3 flex items-baseline justify-between">
                  <div>
                    <div className="text-2xl font-bold text-white">৳ 45,000</div>
                    <div className="text-xs text-slate-400">Physical Cash</div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-emerald-400">৳ 120,000</div>
                    <div className="text-xs text-slate-400">Digital Float</div>
                  </div>
                </div>
              </div>

              <div className="glass-panel p-6 rounded-2xl border border-slate-800/80">
                <span className="text-xs font-semibold text-amber-400 uppercase tracking-wider">XGBoost Surge Forecast</span>
                <p className="text-xs text-slate-300 mt-2 font-medium">Garment Zone Salary Surge (+280%)</p>
                <div className="mt-2 p-2.5 rounded-lg bg-amber-950/40 border border-amber-500/30 text-xs text-amber-200">
                  Recommended action: Add ৳80,000 float by Thursday morning.
                </div>
              </div>

              <div className="glass-panel p-6 rounded-2xl border border-slate-800/80">
                <span className="text-xs font-semibold text-cyan-400 uppercase tracking-wider">Anti-Screenshot Token</span>
                <div className="mt-2 flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-slate-900 border border-cyan-500/40 text-cyan-400">
                    <QrCode className="w-8 h-8 animate-pulse" />
                  </div>
                  <div>
                    <div className="text-xs font-mono text-cyan-300 font-bold">NONCE-8472-A9</div>
                    <div className="text-[11px] text-slate-400">Dynamic animated verification badge active.</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {role === 'RISK_ANALYST' && (
          <div className="space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
              <div>
                <h1 className="text-2xl font-bold text-white tracking-tight">Central Risk Console & Radar</h1>
                <p className="text-sm text-slate-400">Live transaction scoring, NetworkX money-mule topology & emergency lockdown audits.</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="flex h-2.5 w-2.5 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-rose-500"></span>
                </span>
                <span className="text-xs font-semibold text-slate-300">Live Event Feed</span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="glass-panel p-5 rounded-2xl border border-slate-800/80">
                <span className="text-xs text-slate-400">Transactions Scored</span>
                <div className="text-2xl font-extrabold text-white mt-1">50,000</div>
                <span className="text-[11px] text-emerald-400">Synthetic stream ready</span>
              </div>
              <div className="glass-panel p-5 rounded-2xl border border-slate-800/80">
                <span className="text-xs text-slate-400">High-Risk Intercepted</span>
                <div className="text-2xl font-extrabold text-rose-400 mt-1">142</div>
                <span className="text-[11px] text-rose-400">Risk &gt;= 0.75</span>
              </div>
              <div className="glass-panel p-5 rounded-2xl border border-slate-800/80">
                <span className="text-xs text-slate-400">Mule Rings Detected</span>
                <div className="text-2xl font-extrabold text-amber-400 mt-1">6 Clusters</div>
                <span className="text-[11px] text-amber-300">NetworkX topological</span>
              </div>
              <div className="glass-panel p-5 rounded-2xl border border-slate-800/80">
                <span className="text-xs text-slate-400">Master Freeze Latency</span>
                <div className="text-2xl font-extrabold text-cyan-400 mt-1">&lt; 42ms</div>
                <span className="text-[11px] text-cyan-300">Sub-300ms SLA target met</span>
              </div>
            </div>
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 px-4 py-6 text-center text-xs text-slate-500">
        <p>upay Pulse — AI-powered Mobile Financial Services (MFS) Intelligence Ecosystem</p>
        <p className="mt-1 text-slate-600 font-mono">FastAPI • PostgreSQL 18 • LightGBM • XGBoost • NetworkX • React 18</p>
      </footer>
    </div>
  );
};

export default App;
