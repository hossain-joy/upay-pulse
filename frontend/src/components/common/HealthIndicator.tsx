import React, { useEffect, useState } from 'react';
import { API_BASE_URL } from '../../api/client';

interface HealthData {
  status: string;
  database?: { status: string; dialect?: string };
  event_bus?: { mode: string; redis_connected?: boolean };
}

export const HealthIndicator: React.FC = () => {
  const [health, setHealth] = useState<HealthData | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const rootUrl = API_BASE_URL.replace(/\/api\/v1\/?$/, '');
        const res = await fetch(`${rootUrl}/ready`);
        if (res.ok) {
          const data = await res.json();
          setHealth(data);
        } else {
          setHealth({ status: 'unhealthy' });
        }
      } catch {
        setHealth({ status: 'offline' });
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const isReady = health?.status === 'ready';
  const dialect = health?.database?.dialect?.toLowerCase();
  const busMode = health?.event_bus?.mode === 'redis' ? 'redis' : 'memory';

  return (
    <div className="hidden md:flex items-center gap-2 text-[11px] font-medium text-slate-400">
      <span className="flex items-center gap-1.5">
        <span
          className={`w-1.5 h-1.5 rounded-full ${isReady ? 'bg-emerald-400' : 'bg-slate-600'}`}
        />
        <span className="text-slate-300">{isReady ? 'Live' : 'Offline'}</span>
      </span>
      <span className="text-slate-700">·</span>
      <span className="font-mono uppercase tracking-wider text-[10px]">
        {dialect || '—'} · {busMode}
      </span>
    </div>
  );
};