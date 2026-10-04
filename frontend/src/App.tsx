import React, { useState, useEffect } from 'react';
import { Header } from './components/common/Header';
import { UserRole } from './components/common/RoleSwitcher';
import { CustomerPortal } from './components/CustomerPortal';
import { AgentTerminal } from './components/AgentTerminal';
import { RiskConsole } from './components/RiskConsole';
import { setAuthToken, API_BASE_URL, getWebSocketUrl } from './api/client';
import { 
  Sparkles, 
  CheckCircle2, 
  AlertCircle, 
  Info, 
  X,
  Bot
} from 'lucide-react';

interface Toast {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
}

export const App: React.FC = () => {
  const [role, setRole] = useState<UserRole>('CUSTOMER');
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [isWsConnected, setIsWsConnected] = useState(false);

  // Show Toast
  const addToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const [activeUser, setActiveUser] = useState<any>(null);

  // Switch demo token automatically when switching roles
  useEffect(() => {
    const autoLoginPersona = async () => {
      try {
        let endpoint = '/auth/login';
        let body: any = {};

        if (role === 'CUSTOMER') {
          body = { identifier: '+8801700000001', password: 'Demo@1234' };
        } else if (role === 'AGENT') {
          body = { identifier: '+8801800000001', password: 'Demo@1234' };
        } else {
          body = { identifier: 'admin@example.com', password: 'Admin@1234' };
        }

        const res = await fetch(`${API_BASE_URL}${endpoint}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });

        if (res.ok) {
          const data = await res.json();
          if (data.access_token) {
            setAuthToken(data.access_token);
            setActiveUser(data.user || null);
          }
        }
      } catch (e) {
        console.warn('Auto persona token setup notice:', e);
      }
    };

    autoLoginPersona();
  }, [role]);

  // Real-Time Event Bus WebSocket Connection (Phase 16)
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: any = null;

    const connectWs = () => {
      try {
        ws = new WebSocket(getWebSocketUrl());

        ws.onopen = () => {
          setIsWsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === "BUS_EVENT") {
              const { topic, payload } = data;
              if (topic === "transaction.flagged") {
                addToast(`🚨 Security Interception: ${payload.reference || 'Txn'} flagged by LightGBM!`, 'error');
              } else if (topic === "account.freeze.completed") {
                addToast(`🔒 Master Freeze Lockdown: Account secured in sub-300ms.`, 'success');
              } else if (topic === "agent.liquidity.warning") {
                addToast(`⚠️ Agent Liquidity Alert: ${payload.reason || 'Surge expected'}`, 'info');
              } else if (topic === "soundbox.trigger") {
                addToast(`🔊 Soundbox Alert: Payment confirmation received for ৳${payload.amount}`, 'success');
              }
            }
          } catch (e) {}
        };

        ws.onclose = () => {
          setIsWsConnected(false);
          reconnectTimeout = setTimeout(connectWs, 3000);
        };

        ws.onerror = () => {
          ws?.close();
        };
      } catch (err) {
        setIsWsConnected(false);
      }
    };

    connectWs();

    return () => {
      clearTimeout(reconnectTimeout);
      if (ws) ws.close();
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#0B1120] text-slate-100 flex flex-col font-sans selection:bg-cyan-500 selection:text-black">
      {/* Global Header & Role Switcher */}
      <Header currentRole={role} onRoleChange={setRole} />

      {/* Main Workspace Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-3 sm:px-6 lg:px-8 py-4 sm:py-6">
        
        {/* Top Intelligence Banner */}
        <div className="mb-4 sm:mb-6 p-3 sm:p-4 rounded-2xl sm:rounded-3xl bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-indigo-500/20 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4 shadow-xl">
          <div className="flex items-start sm:items-center gap-2.5 sm:gap-3">
            <div className="p-2 sm:p-2.5 rounded-xl sm:rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shrink-0 mt-0.5 sm:mt-0">
              <Bot className="w-4 h-4 sm:w-5 sm:h-5" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
                <h2 className="text-xs sm:text-sm font-bold text-white">Google AI Studio Gemini 2.5 Flash Active</h2>
                <span className="text-[9px] sm:text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-300 border border-emerald-500/30">
                  Exact AI Execution
                </span>
                <span className="text-[9px] sm:text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-950/80 text-cyan-300 border border-cyan-500/30 flex items-center gap-1.5">
                  <span className={`w-1.5 h-1.5 rounded-full ${isWsConnected ? 'bg-cyan-400 animate-ping' : 'bg-slate-500'}`} />
                  {isWsConnected ? 'WebSocket Live' : 'Connecting Stream...'}
                </span>
              </div>
              <p className="text-[11px] sm:text-xs text-slate-400 mt-1">
                Live natural language Bangla Voice Financial Coach • Sub-5ms LightGBM risk scoring • Real-time NetworkX graph intelligence.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
            <span className="text-[11px] sm:text-xs font-mono text-cyan-400 bg-slate-950/80 px-2.5 sm:px-3 py-0.5 sm:py-1 rounded-full border border-cyan-500/30">
              {role === 'CUSTOMER' ? 'CustomerAI Pillar' : role === 'AGENT' ? 'AgentAI Pillar' : 'SecurityAI Pillar'}
            </span>
          </div>
        </div>

        {/* Dynamic Pillar View */}
        {role === 'CUSTOMER' && (
          <CustomerPortal user={activeUser} key={`cust-${activeUser?.id || role}`} onNotify={addToast} />
        )}

        {role === 'AGENT' && (
          <AgentTerminal user={activeUser} key={`agent-${activeUser?.id || role}`} onNotify={addToast} />
        )}

        {role === 'RISK_ANALYST' && (
          <RiskConsole key={`risk-${activeUser?.id || role}`} onNotify={addToast} />
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950/80 py-6 mt-12">
        <div className="max-w-7xl mx-auto px-4 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <div>
            <strong className="text-slate-400">upay Pulse</strong> — AI-powered MFS Intelligence Ecosystem. Educational Prototype.
          </div>
          <div className="flex items-center gap-4">
            <span>PostgreSQL 18</span>
            <span>•</span>
            <span>FastAPI Python 3.14</span>
            <span>•</span>
            <span>Google AI Studio Gemini</span>
            <span>•</span>
            <span>LightGBM & NetworkX</span>
          </div>
        </div>
      </footer>

      {/* Toast Notification Container */}
      <div className="fixed bottom-4 sm:bottom-6 right-4 sm:right-6 left-4 sm:left-auto z-50 space-y-2 max-w-sm w-auto sm:w-full pointer-events-none">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto p-4 rounded-2xl border shadow-2xl backdrop-blur-xl flex items-start gap-3 transition-all duration-300 animate-slide-up ${
              toast.type === 'success'
                ? 'bg-slate-900/95 border-emerald-500/40 text-emerald-300'
                : toast.type === 'error'
                ? 'bg-slate-900/95 border-rose-500/40 text-rose-300'
                : 'bg-slate-900/95 border-cyan-500/40 text-cyan-300'
            }`}
          >
            {toast.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            ) : toast.type === 'error' ? (
              <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            ) : (
              <Info className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
            )}
            <div className="flex-1 text-xs text-slate-200 leading-relaxed font-medium">
              {toast.message}
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              className="text-slate-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default App;
