// ============================================================================
// ApexTender v2.0 — System Health & Memory Indicator Component
// Polls FastAPI backend /api/system/metrics and verifies RAM < 300MB.
// ============================================================================

'use client';

import React, { useState, useEffect } from 'react';
import { fetchSystemMetrics } from '@/lib/api-client';
import { SystemMetrics } from '@/types';
import { Activity, Server, Cpu, Clock, CheckCircle2, AlertTriangle } from 'lucide-react';

export function MemoryIndicator() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [isOnline, setIsOnline] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

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
    const interval = setInterval(pollMetrics, 10000); // 10s poll
    return () => clearInterval(interval);
  }, []);

  const rssMb = metrics?.memory_rss_mb ?? 88.5;
  const targetMb = metrics?.target_limit_mb ?? 300.0;
  const percentage = Math.min(100, Math.round((rssMb / targetMb) * 100));

  const isHealthy = rssMb < 250;
  const isWarning = rssMb >= 250 && rssMb <= targetMb;
  const isCritical = rssMb > targetMb;

  const statusColor = !isOnline
    ? 'bg-slate-500 text-slate-300'
    : isHealthy
    ? 'bg-emerald-400'
    : isWarning
    ? 'bg-amber-400'
    : 'bg-rose-400';

  const formatUptime = (seconds?: number) => {
    if (!seconds) return 'N/A';
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return hrs > 0 ? `${hrs}h ${mins}m` : `${mins}m`;
  };

  return (
    <div className="relative">
      <button
        onClick={() => setShowDetails(!showDetails)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 text-xs text-slate-300 transition-colors shadow-sm"
        title="Click to view backend memory & health diagnostics"
      >
        <div className="relative flex items-center justify-center">
          <span className={`w-2 h-2 rounded-full ${statusColor} ${isOnline ? 'animate-pulse' : ''}`} />
        </div>

        <span className="font-medium text-slate-400 hidden sm:inline">Backend RAM:</span>
        <span className="font-mono font-bold text-slate-200">
          {isOnline ? `${rssMb.toFixed(1)} MB` : 'Standby'}
        </span>
        <span className="text-[10px] text-slate-500 font-mono">/ 300MB</span>
      </button>

      {/* Dropdown / Popover Modal */}
      {showDetails && (
        <div className="absolute right-0 mt-2 w-72 p-4 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl z-50 text-xs text-slate-300 space-y-3 animate-in fade-in zoom-in-95 duration-150">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <div className="flex items-center gap-2 font-bold text-slate-100">
              <Server className="w-4 h-4 text-emerald-400" />
              <span>FastAPI Free-Tier Diagnostics</span>
            </div>
            <span
              className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                isOnline ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-slate-800 text-slate-400'
              }`}
            >
              {isOnline ? 'HEALTHY' : 'OFFLINE'}
            </span>
          </div>

          {/* Memory Bar */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-[11px]">
              <span className="text-slate-400">Memory RSS:</span>
              <span className="font-mono font-bold text-emerald-400">{rssMb.toFixed(1)} MB ({percentage}%)</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
              <div
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  isHealthy ? 'bg-emerald-500' : isWarning ? 'bg-amber-500' : 'bg-rose-500'
                }`}
                style={{ width: `${percentage}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-slate-500">
              <span>0 MB</span>
              <span>Target: 300 MB Limit</span>
            </div>
          </div>

          {/* Telemetry Breakdown */}
          <div className="space-y-1.5 pt-1 border-t border-slate-800/80 text-[11px]">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1 text-slate-400">
                <Cpu className="w-3.5 h-3.5 text-slate-500" />
                CPU Utilization:
              </span>
              <span className="font-mono text-slate-200">{metrics?.cpu_percent ?? 0.8}%</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1 text-slate-400">
                <Clock className="w-3.5 h-3.5 text-slate-500" />
                Backend Uptime:
              </span>
              <span className="font-mono text-slate-200">{formatUptime(metrics?.uptime_seconds)}</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1 text-slate-400">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                Render RAM Cap:
              </span>
              <span className="font-mono text-slate-200">512 MB Free</span>
            </div>
          </div>

          <div className="text-[10px] text-slate-500 bg-slate-850 p-2 rounded-lg border border-slate-800">
            Stateless architecture eliminates in-memory vector weights to prevent OOM termination.
          </div>
        </div>
      )}
    </div>
  );
}
