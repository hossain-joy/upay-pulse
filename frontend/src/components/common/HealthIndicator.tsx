import React, { useEffect, useState } from 'react';
import { Activity, Database, Radio, CheckCircle, AlertTriangle } from 'lucide-react';

interface HealthData {
  status: string;
  database?: { status: string; dialect?: string };
  event_bus?: { mode: string; redis_connected?: boolean };
}

export const HealthIndicator: React.FC = () => {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await fetch('/ready');
        if (res.ok) {
          const data = await res.json();
          setHealth(data);
        } else {
          setHealth({ status: 'unhealthy' });
        }
      } catch (err) {
        setHealth({ status: 'offline' });
      } finally {
        setLoading(false);
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/80 border border-slate-700 text-xs text-slate-400">
        <Activity className="w-3.5 h-3.5 animate-spin text-cyan-400" />
        <span>Connecting Core...</span>
      </div>
    );
  }

  const isHealthy = health?.status === 'ready';

  return (
    <div className="flex items-center gap-3">
      <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border ${
        isHealthy 
          ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-300' 
          : 'bg-amber-950/60 border-amber-500/40 text-amber-300'
      }`}>
        <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
        <span>Backend {isHealthy ? 'Live' : 'Standby'}</span>
      </div>

      <div className="hidden sm:flex items-center gap-2 text-xs text-slate-400 border border-slate-800 rounded-lg px-2.5 py-1 bg-slate-900/60">
        <Database className="w-3.5 h-3.5 text-cyan-400" />
        <span>{health?.database?.dialect?.toUpperCase() || 'POSTGRES'}</span>
        <span className="text-slate-600">|</span>
        <Radio className="w-3.5 h-3.5 text-indigo-400" />
        <span>{health?.event_bus?.mode === 'redis' ? 'REDIS' : 'EVENT-BUS'}</span>
      </div>
    </div>
  );
};
