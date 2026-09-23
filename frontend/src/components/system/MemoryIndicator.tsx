// ============================================================================
// RFPANDA — Backend health & memory indicator
// Polls /api/system/metrics and shows live RAM / uptime telemetry.
// ============================================================================

'use client';

import React, { useState, useEffect, useRef } from 'react';
import { fetchSystemMetrics } from '@/lib/api-client';
import { SystemMetrics } from '@/types';
import { Server, Cpu, Clock, CheckCircle2, Activity } from 'lucide-react';

export function MemoryIndicator() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [isOnline, setIsOnline] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const pollMetrics = async () => {
    try {
      const data = await fetchSystemMetrics();
      setMetrics(data);
      setIsOnline(true);
    } catch {
      setIsOnline(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    pollMetrics();
    const interval = setInterval(pollMetrics, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!showDetails) return;
    const onClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowDetails(false);
      }
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [showDetails]);

  const rssMb = metrics?.memory_rss_mb ?? 0;
  const targetMb = metrics?.target_limit_mb ?? 300.0;
  const percentage = Math.min(100, Math.round((rssMb / targetMb) * 100));

  const isHealthy = rssMb < 250;
  const isWarning = rssMb >= 250 && rssMb <= targetMb;

  const dotColor = !isOnline
    ? 'bg-zinc-300'
    : isHealthy
    ? 'bg-emerald-500'
    : isWarning
    ? 'bg-amber-400'
    : 'bg-rose-500';

  const formatUptime = (seconds?: number) => {
    if (!seconds) return 'N/A';
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return hrs > 0 ? `${hrs}h ${mins}m` : `${mins}m`;
  };

  return (
    <div className="relative" ref={containerRef}>
      <button
        onClick={() => setShowDetails((v) => !v)}
        className="inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white px-3 py-1.5 text-[11px] font-medium text-zinc-600 shadow-sm transition hover:border-zinc-300 hover:text-zinc-900"
        title="Backend health"
      >
        <span className={`h-1.5 w-1.5 rounded-full ${dotColor} ${isOnline ? 'animate-pulse' : ''}`} />
        <span className="hidden sm:inline text-zinc-400">Backend</span>
        <span className="font-mono font-semibold text-zinc-700">
          {loading ? '…' : isOnline ? `${rssMb.toFixed(0)} MB` : 'Offline'}
        </span>
      </button>

      {showDetails && (
        <div className="absolute right-0 z-50 mt-2 w-72 space-y-3 rounded-2xl border border-zinc-200 bg-white p-4 text-xs text-zinc-600 shadow-lift animate-scale-in">
          <div className="flex items-center justify-between border-b border-zinc-100 pb-2.5">
            <span className="flex items-center gap-2 font-bold text-zinc-900">
              <Server className="h-4 w-4 text-brand-600" />
              Backend health
            </span>
            <span
              className={`rounded-full border px-2 py-0.5 text-[10px] font-bold ${
                isOnline
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                  : 'border-zinc-200 bg-zinc-100 text-zinc-500'
              }`}
            >
              {isOnline ? 'Healthy' : 'Offline'}
            </span>
          </div>

          <div className="space-y-1.5">
            <div className="flex justify-between text-[11px]">
              <span className="text-zinc-500">Memory (RSS)</span>
              <span className="font-mono font-semibold text-zinc-800">
                {rssMb.toFixed(1)} MB · {percentage}%
              </span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-100">
              <div
                className={`h-full rounded-full transition-all duration-300 ${
                  isHealthy ? 'bg-emerald-500' : isWarning ? 'bg-amber-500' : 'bg-rose-500'
                }`}
                style={{ width: `${percentage}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-zinc-400">
              <span>0 MB</span>
              <span>Target {targetMb.toFixed(0)} MB</span>
            </div>
          </div>

          <div className="space-y-2 border-t border-zinc-100 pt-2.5 text-[11px]">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-zinc-500">
                <Cpu className="h-3.5 w-3.5 text-zinc-400" /> CPU
              </span>
              <span className="font-mono text-zinc-700">{metrics?.cpu_percent ?? 0}%</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-zinc-500">
                <Clock className="h-3.5 w-3.5 text-zinc-400" /> Uptime
              </span>
              <span className="font-mono text-zinc-700">{formatUptime(metrics?.uptime_seconds)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-zinc-500">
                <Activity className="h-3.5 w-3.5 text-zinc-400" /> Threads
              </span>
              <span className="font-mono text-zinc-700">{metrics?.threads_count ?? 0}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-zinc-500">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> RAM cap
              </span>
              <span className="font-mono text-zinc-700">512 MB</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
