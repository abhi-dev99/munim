"use client";
import { useState, useEffect } from "react";
import { Activity, Database, Server, Link as LinkIcon, RefreshCw, MessageSquare } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function DevDashboard() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/admin/system-status`);
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
        setLastUpdated(new Date().toLocaleTimeString());
      } else {
        setStatus({ error: `HTTP ${res.status}` });
      }
    } catch (e) {
      setStatus({ error: e.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000); // Auto-refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (state) => {
    if (!state) return "bg-gray-100 text-gray-500 border-gray-200";
    if (state.status === "online") return "bg-emerald-50 text-emerald-700 border-emerald-200";
    if (state.status === "offline") return "bg-red-50 text-red-700 border-red-200";
    return "bg-amber-50 text-amber-700 border-amber-200";
  };

  const getStatusDot = (state) => {
    if (!state) return "bg-gray-400";
    if (state.status === "online") return "bg-emerald-500";
    if (state.status === "offline") return "bg-red-500";
    return "bg-amber-500";
  };

  const StatusCard = ({ title, icon: Icon, data }) => (
    <div className={`p-4 rounded-xl border ${getStatusColor(data)} transition-all`}>
      <div className="flex justify-between items-start mb-3">
        <div className="flex items-center gap-2">
          <div className={`p-2 rounded-lg bg-white/50`}>
            <Icon size={18} />
          </div>
          <h3 className="font-bold">{title}</h3>
        </div>
        <div className="flex items-center gap-1.5">
          <div className={`w-2 h-2 rounded-full ${getStatusDot(data)} ${data?.status === 'online' ? 'animate-pulse' : ''}`} />
          <span className="text-xs font-semibold uppercase tracking-wider">
            {data?.status || "Unknown"}
          </span>
        </div>
      </div>
      
      <div className="space-y-1">
        <div className="flex justify-between text-sm">
          <span className="opacity-70">Latency</span>
          <span className="font-mono">{data?.latency_ms !== undefined ? `${data.latency_ms}ms` : '—'}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="opacity-70">Message</span>
          <span className="font-mono text-xs truncate ml-2" title={data?.message}>{data?.message || '—'}</span>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50 p-8 font-sans">
      <div className="max-w-4xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="flex justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
          <div>
            <h1 className="text-2xl font-black text-gray-900 flex items-center gap-2">
              <Activity className="text-blue-600" /> System Diagnostics
            </h1>
            <p className="text-sm text-gray-500 mt-1">Monitor external dependencies and diagnose cold start latency.</p>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-xs text-gray-400 font-mono">
              Last check: {lastUpdated || 'Never'}
            </span>
            <button 
              onClick={fetchStatus}
              disabled={loading}
              className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
              {loading ? "Pinging..." : "Wake Up & Ping All"}
            </button>
          </div>
        </div>

        {/* Error State */}
        {status?.error && (
          <div className="bg-red-50 text-red-700 p-4 rounded-xl border border-red-200 font-mono text-sm">
            ❌ Backend Unreachable: {status.error}
          </div>
        )}

        {/* Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <StatusCard 
            title="Supabase Database" 
            icon={Database} 
            data={status?.supabase} 
          />
          <StatusCard 
            title="Gemini API (LLM)" 
            icon={MessageSquare} 
            data={status?.gemini} 
          />
          <StatusCard 
            title="Ngrok Webhook Tunnel" 
            icon={LinkIcon} 
            data={status?.ngrok} 
          />
          <StatusCard 
            title="Backend Server" 
            icon={Server} 
            data={status ? { status: 'online', latency_ms: 0, message: 'Running on :8000' } : null} 
          />
        </div>

      </div>
    </div>
  );
}
