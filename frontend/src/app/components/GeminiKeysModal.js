"use client";

import { useState, useEffect } from "react";
import {
  Key,
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  Plus,
  X,
  Cpu,
  CheckCircle2,
  Activity,
  XCircle,
  HelpCircle,
} from "lucide-react";

export default function GeminiKeysModal({ isOpen, onClose, apiBase = "http://localhost:8000" }) {
  const [statusData, setStatusData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [newKey, setNewKey] = useState("");
  const [adding, setAdding] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${apiBase}/api/v1/admin/gemini-keys`);
      if (res.ok) {
        const data = await res.json();
        setStatusData(data);
        setErrorMsg("");
      }
    } catch (err) {
      setErrorMsg("Failed to connect to backend AI telemetry.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, [isOpen, apiBase]);

  const handleAddKey = async (e) => {
    e.preventDefault();
    if (!newKey.trim()) return;
    setAdding(true);
    setErrorMsg("");
    setSuccessMsg("");
    try {
      const res = await fetch(`${apiBase}/api/v1/admin/gemini-keys/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: newKey.trim() }),
      });
      const data = await res.json();
      if (res.ok) {
        setSuccessMsg("API Key added to live rotation pool successfully!");
        setNewKey("");
        fetchStatus();
      } else {
        setErrorMsg(data.detail || "Failed to add API key");
      }
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setAdding(false);
    }
  };

  const handleResetLimits = async () => {
    setResetting(true);
    setErrorMsg("");
    setSuccessMsg("");
    try {
      const res = await fetch(`${apiBase}/api/v1/admin/gemini-keys/reset`, {
        method: "POST",
      });
      if (res.ok) {
        setSuccessMsg("Rate-limit status reset across all keys!");
        fetchStatus();
      } else {
        setErrorMsg("Failed to reset key status");
      }
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setResetting(false);
    }
  };

  if (!isOpen) return null;

  const totalKeys = statusData?.total_keys || 0;
  const rateLimitedCount = statusData?.rate_limited_count || 0;
  const activeCount = totalKeys - rateLimitedCount;
  const allExhausted = statusData?.all_exhausted || false;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] flex flex-col overflow-hidden border border-gray-100">
        {/* Modal Header */}
        <div className="px-6 py-4 bg-gradient-to-r from-gray-900 via-gray-800 to-gray-900 text-white flex items-center justify-between border-b border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-500/20 rounded-xl border border-emerald-500/30 text-[#10b981]">
              <Key size={20} />
            </div>
            <div>
              <h2 className="font-extrabold text-base tracking-tight flex items-center gap-2">
                <span>Gemini API Key Rotation Pool & Telemetry</span>
                {statusData?.model && (
                  <span className="text-xs px-2 py-0.5 bg-gray-700/80 rounded-full font-mono font-normal text-gray-300">
                    {statusData.model}
                  </span>
                )}
              </h2>
              <p className="text-xs text-gray-400">
                Live monitoring, automatic 429 failover, and dynamic key insertion
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchStatus}
              disabled={loading}
              title="Refresh status"
              className="p-2 hover:bg-gray-700/70 rounded-lg text-gray-300 hover:text-white transition-colors"
            >
              <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-700/70 rounded-lg text-gray-300 hover:text-white transition-colors"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Alert Banner for Quota Status */}
        {allExhausted ? (
          <div className="bg-red-500 text-white px-6 py-3 flex items-center justify-between text-xs font-bold shadow-inner">
            <div className="flex items-center gap-2">
              <AlertTriangle size={16} className="animate-pulse" />
              <span>
                🚨 CRITICAL: All {totalKeys} API keys are currently rate-limited (429/Quota Exceeded).
                Inference fallback to Groq Llama-3.3 is active.
              </span>
            </div>
            <button
              onClick={handleResetLimits}
              disabled={resetting}
              className="px-3 py-1 bg-white/20 hover:bg-white/30 rounded text-white font-semibold transition-colors"
            >
              {resetting ? "Resetting..." : "Reset All Quotas"}
            </button>
          </div>
        ) : rateLimitedCount > 0 ? (
          <div className="bg-amber-500 text-white px-6 py-3 flex items-center justify-between text-xs font-bold shadow-inner">
            <div className="flex items-center gap-2">
              <AlertTriangle size={16} />
              <span>
                ⚠️ AI Quota Notice: {rateLimitedCount} of {totalKeys} keys hit rate limits and rotated.
                Pipeline is operating normally on remaining active keys.
              </span>
            </div>
            <button
              onClick={handleResetLimits}
              disabled={resetting}
              className="px-3 py-1 bg-white/20 hover:bg-white/30 rounded text-white font-semibold transition-colors"
            >
              {resetting ? "Resetting..." : "Reset Limited Keys"}
            </button>
          </div>
        ) : (
          <div className="bg-emerald-50 text-emerald-800 px-6 py-2.5 border-b border-emerald-100 flex items-center justify-between text-xs font-semibold">
            <div className="flex items-center gap-2">
              <CheckCircle2 size={15} className="text-[#10b981]" />
              <span>
                All {totalKeys} Gemini API keys are active and healthy. Automatic failover enabled.
              </span>
            </div>
            <span className="text-emerald-700 font-mono text-[11px]">
              Active Slot: #{statusData?.active_key_index ?? 0}
            </span>
          </div>
        )}

        {/* Main Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {errorMsg && (
            <div className="p-3 bg-red-50 text-red-700 text-xs rounded-xl border border-red-200 flex items-center gap-2">
              <XCircle size={15} />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className="p-3 bg-emerald-50 text-emerald-800 text-xs rounded-xl border border-emerald-200 flex items-center gap-2">
              <CheckCircle2 size={15} className="text-[#10b981]" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Quick Metrics Grid */}
          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 bg-gray-50 rounded-xl border border-gray-200/80">
              <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
                Total Keys in Pool
              </div>
              <div className="text-2xl font-extrabold text-gray-900">{totalKeys}</div>
            </div>
            <div className="p-4 bg-emerald-50/50 rounded-xl border border-emerald-200/80">
              <div className="text-xs font-semibold text-emerald-700 uppercase tracking-wider mb-1">
                Active & Healthy
              </div>
              <div className="text-2xl font-extrabold text-emerald-700">{activeCount}</div>
            </div>
            <div className="p-4 bg-amber-50/50 rounded-xl border border-amber-200/80">
              <div className="text-xs font-semibold text-amber-700 uppercase tracking-wider mb-1">
                Rate Limited (429)
              </div>
              <div className="text-2xl font-extrabold text-amber-700">{rateLimitedCount}</div>
            </div>
          </div>

          {/* Keys Table */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-gray-900 flex items-center gap-1.5">
                <Activity size={15} className="text-[#10b981]" />
                <span>Configured Key Roster</span>
              </h3>
              <button
                onClick={handleResetLimits}
                disabled={resetting || rateLimitedCount === 0}
                className="text-xs text-gray-600 hover:text-gray-900 font-semibold disabled:opacity-40 flex items-center gap-1"
              >
                <RefreshCw size={12} />
                <span>Reset All Quotas</span>
              </button>
            </div>

            <div className="border border-gray-200 rounded-xl overflow-hidden shadow-xs bg-white">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-gray-50/80 border-b border-gray-200 text-[11px] font-bold text-gray-500 uppercase tracking-wider">
                    <th className="py-2.5 px-4">Slot</th>
                    <th className="py-2.5 px-4">Key Mask</th>
                    <th className="py-2.5 px-4">Status</th>
                    <th className="py-2.5 px-4 text-right">Total Calls</th>
                    <th className="py-2.5 px-4 text-right">429 Hits</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 text-xs font-medium text-gray-800">
                  {statusData?.keys?.map((keyObj) => {
                    const isActiveSlot = statusData.active_key_index === keyObj.index;
                    const isLimited = keyObj.status === "rate_limited";
                    return (
                      <tr
                        key={keyObj.index}
                        className={`${
                          isActiveSlot ? "bg-emerald-50/30" : "hover:bg-gray-50/50"
                        } transition-colors`}
                      >
                        <td className="py-3 px-4 font-mono font-bold text-gray-600">
                          #{keyObj.index}{" "}
                          {isActiveSlot && (
                            <span className="ml-1 text-[10px] bg-emerald-100 text-emerald-800 font-sans font-bold px-1.5 py-0.5 rounded">
                              ACTIVE SLOT
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 font-mono text-gray-700">{keyObj.key_masked}</td>
                        <td className="py-3 px-4">
                          {isLimited ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-100 text-amber-800 rounded-full font-bold text-[11px]">
                              <AlertTriangle size={11} />
                              <span>Rate Limited (429)</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded-full font-bold text-[11px]">
                              <CheckCircle2 size={11} />
                              <span>Active</span>
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-right font-mono">{keyObj.total_calls}</td>
                        <td className="py-3 px-4 text-right font-mono text-amber-700 font-bold">
                          {keyObj.rate_limit_hits}
                        </td>
                      </tr>
                    );
                  })}
                  {(!statusData?.keys || statusData.keys.length === 0) && (
                    <tr>
                      <td colSpan="5" className="py-6 text-center text-gray-400">
                        {loading ? "Loading API key telemetry..." : "No API keys found."}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Add Key Form */}
          <div className="bg-gray-50/80 p-4 rounded-xl border border-gray-200/80">
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-700 mb-2 flex items-center gap-1.5">
              <Plus size={14} className="text-[#10b981]" />
              <span>Dynamic Key Insertion (No Restarts Needed)</span>
            </h3>
            <p className="text-xs text-gray-500 mb-3">
              Add a new Google AI Studio API Key to expand rotation capacity instantly.
            </p>
            <form onSubmit={handleAddKey} className="flex gap-2">
              <input
                type="text"
                placeholder="Paste Gemini API Key (AQ... or AIza...)"
                value={newKey}
                onChange={(e) => setNewKey(e.target.value)}
                className="flex-1 px-3 py-2 bg-white border border-gray-300 rounded-lg text-xs font-mono text-gray-800 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
              />
              <button
                type="submit"
                disabled={adding || !newKey.trim()}
                className="px-4 py-2 bg-[#10b981] hover:bg-emerald-600 text-white text-xs font-bold rounded-lg transition-colors shadow-sm disabled:opacity-50 flex items-center gap-1.5"
              >
                <Plus size={14} />
                <span>{adding ? "Adding..." : "Add Key to Pool"}</span>
              </button>
            </form>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
          <div className="text-[11px] text-gray-500 flex items-center gap-1.5">
            <ShieldCheck size={14} className="text-[#10b981]" />
            <span>Automatic failover switches keys immediately on 429 errors.</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-gray-200 hover:bg-gray-300 text-gray-700 text-xs font-bold rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
