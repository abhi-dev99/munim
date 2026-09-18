"use client";
import { useState, useEffect } from "react";
import { 
  Activity, Database, Server, Link as LinkIcon, RefreshCw, 
  MessageSquare, Cpu, HardDrive, ShieldCheck, Play, 
  CheckCircle2, AlertTriangle, XCircle, Clock, FileText,
  ChevronDown, ChevronUp, Layers, Send
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function DevDashboard() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pingingService, setPingingService] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Reconciliation Engine Sandbox State
  const [testMode, setTestMode] = useState("mock");
  const [runningTest, setRunningTest] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [testError, setTestError] = useState(null);
  const [expandedStep, setExpandedStep] = useState(null);

  const fetchStatus = async (service = null) => {
    if (service) {
      setPingingService(service);
    } else {
      setLoading(true);
    }
    try {
      const url = service 
        ? `${API_BASE}/api/v1/admin/system-status?service=${service}`
        : `${API_BASE}/api/v1/admin/system-status`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setStatus(prev => ({
          ...(prev || {}),
          ...data
        }));
        setLastUpdated(new Date().toLocaleTimeString());
      } else {
        if (!service) setStatus({ error: `HTTP ${res.status}` });
      }
    } catch (e) {
      if (!service) setStatus({ error: e.message });
    } finally {
      setLoading(false);
      setPingingService(null);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(() => fetchStatus(), 30000);
    return () => clearInterval(interval);
  }, []);

  const runReconTest = async (mode = "mock") => {
    setRunningTest(true);
    setTestMode(mode);
    setTestResult(null);
    setTestError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/admin/test-recon-pipeline?mode=${mode}`, {
        method: "POST"
      });
      if (res.ok) {
        const data = await res.json();
        setTestResult(data);
        setExpandedStep(data.steps?.[0]?.step_num || 1);
      } else {
        const err = await res.json();
        setTestError(err.detail || `HTTP Error ${res.status}`);
      }
    } catch (e) {
      setTestError(e.message);
    } finally {
      setRunningTest(false);
    }
  };

  const getStatusColor = (state) => {
    if (!state) return "bg-gray-50 text-gray-500 border-gray-200";
    if (state.status === "online") return "bg-emerald-50 text-emerald-800 border-emerald-200";
    if (state.status === "offline") return "bg-red-50 text-red-800 border-red-200";
    return "bg-amber-50 text-amber-800 border-amber-200";
  };

  const getStatusDot = (state) => {
    if (!state) return "bg-gray-400";
    if (state.status === "online") return "bg-emerald-500";
    if (state.status === "offline") return "bg-red-500";
    return "bg-amber-500";
  };

  const getStepIcon = (status) => {
    if (status === "success") return <CheckCircle2 size={18} className="text-emerald-600" />;
    if (status === "warning") return <AlertTriangle size={18} className="text-amber-600" />;
    return <XCircle size={18} className="text-red-600" />;
  };

  const StatusCard = ({ id, title, icon: Icon, data, subtitle }) => {
    const isThisPinging = pingingService === id;
    return (
      <div className={`p-5 rounded-2xl border ${getStatusColor(data)} transition-all shadow-sm flex flex-col justify-between`}>
        <div>
          <div className="flex justify-between items-start mb-3">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-white/70 shadow-sm border border-gray-100">
                <Icon size={20} className="text-blue-600" />
              </div>
              <div>
                <h3 className="font-bold text-gray-900 leading-tight">{title}</h3>
                <p className="text-xs text-gray-500">{subtitle || data?.category || "Service"}</p>
              </div>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/80 border border-gray-200/60 shadow-sm">
              <div className={`w-2 h-2 rounded-full ${getStatusDot(data)} ${data?.status === "online" ? "animate-pulse" : ""}`} />
              <span className="text-xs font-bold uppercase tracking-wider text-gray-700">
                {data?.status || "Unknown"}
              </span>
            </div>
          </div>
          
          <div className="space-y-1.5 my-3 bg-white/50 p-2.5 rounded-xl border border-gray-100">
            <div className="flex justify-between text-xs">
              <span className="text-gray-500 font-medium">Latency</span>
              <span className="font-mono font-bold text-gray-800">{data?.latency_ms !== undefined ? `${data.latency_ms}ms` : "—"}</span>
            </div>
            <div className="flex justify-between text-xs items-center">
              <span className="text-gray-500 font-medium">Message</span>
              <span className="font-mono text-gray-800 truncate ml-2 max-w-[180px]" title={data?.message}>{data?.message || "—"}</span>
            </div>
          </div>
        </div>

        <div className="pt-2 border-t border-gray-200/50 flex justify-end">
          <button
            onClick={() => fetchStatus(id)}
            disabled={isThisPinging || loading}
            className="flex items-center gap-1.5 text-xs font-bold bg-white text-blue-600 hover:bg-blue-50 border border-blue-200/80 px-3 py-1.5 rounded-lg transition-all shadow-sm disabled:opacity-50"
          >
            <RefreshCw size={13} className={isThisPinging ? "animate-spin" : ""} />
            {isThisPinging ? "Pinging..." : "Ping & Test"}
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50/80 p-6 md:p-10 font-sans">
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center bg-white p-6 rounded-3xl shadow-sm border border-gray-100 gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-100 text-blue-700 uppercase tracking-wider">
                Dev Console
              </span>
              <h1 className="text-2xl font-black text-gray-900 flex items-center gap-2">
                System Diagnostics & Test Bench
              </h1>
            </div>
            <p className="text-sm text-gray-500 mt-1">
              Real-time component telemetry, independent service pinging, and LangGraph pipeline sandbox.
            </p>
          </div>
          <div className="flex items-center gap-4 self-end md:self-auto">
            <span className="text-xs text-gray-400 font-mono">
              Last check: {lastUpdated || "Never"}
            </span>
            <button 
              onClick={() => fetchStatus(null)}
              disabled={loading}
              className="flex items-center gap-2 bg-blue-600 text-white font-bold px-5 py-2.5 rounded-xl hover:bg-blue-700 disabled:opacity-50 transition-all shadow-md shadow-blue-600/20"
            >
              <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
              {loading ? "Checking All..." : "Ping & Test All Services"}
            </button>
          </div>
        </div>

        {/* Error State */}
        {status?.error && (
          <div className="bg-red-50 text-red-800 p-4 rounded-2xl border border-red-200 font-mono text-sm flex items-center gap-3">
            <XCircle className="text-red-600 shrink-0" />
            <span>Backend Unreachable: {status.error}</span>
          </div>
        )}

        {/* System Diagnostics Grid (7 Core Services) */}
        <div>
          <h2 className="text-lg font-extrabold text-gray-900 mb-4 flex items-center gap-2">
            <Layers className="text-blue-600" size={20} />
            Core Infrastructure & AI Engine Health
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <StatusCard 
              id="supabase"
              title="Supabase Database" 
              subtitle="PostgreSQL / Auth / Storage"
              icon={Database} 
              data={status?.supabase} 
            />
            <StatusCard 
              id="gemini"
              title="Gemini Multimodal API" 
              subtitle="Vision OCR & Diagnostic LLM"
              icon={MessageSquare} 
              data={status?.gemini} 
            />
            <StatusCard 
              id="groq"
              title="Groq Llama-3.3 API" 
              subtitle="Low-Latency Inference Fallback"
              icon={Cpu} 
              data={status?.groq} 
            />
            <StatusCard 
              id="redis"
              title="Redis / LRU Cache" 
              subtitle="Distributed State / Resilience"
              icon={HardDrive} 
              data={status?.redis} 
            />
            <StatusCard 
              id="langgraph"
              title="Reconciliation Engine" 
              subtitle="7-Node LangGraph StateGraph"
              icon={Activity} 
              data={status?.langgraph} 
            />
            <StatusCard 
              id="ngrok"
              title="Ngrok Webhook Tunnel" 
              subtitle="Live Meta WhatsApp Webhook"
              icon={LinkIcon} 
              data={status?.ngrok} 
            />
            <StatusCard 
              id="backend"
              title="FastAPI Backend Server" 
              subtitle="API / APScheduler Engine"
              icon={Server} 
              data={status?.backend || { status: "online", latency_ms: 0, message: "Running on port 8000" }} 
            />
          </div>
        </div>

        {/* RECONCILIATION ENGINE TEST BENCH (LIVE SANDBOX) */}
        <div className="bg-white p-6 md:p-8 rounded-3xl shadow-sm border border-gray-100 space-y-6">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-4 border-b border-gray-100">
            <div>
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 uppercase tracking-wider">
                  Live Test Bench
                </span>
                <h2 className="text-xl font-extrabold text-gray-900 flex items-center gap-2">
                  <ShieldCheck className="text-emerald-600" />
                  LangGraph Autonomous Reconciliation Sandbox
                </h2>
              </div>
              <p className="text-sm text-gray-500 mt-1">
                Test the 7-node autonomous reconciliation pipeline in isolation without needing WhatsApp or external triggers.
              </p>
            </div>
            
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => runReconTest("mock")}
                disabled={runningTest}
                className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold px-4 py-2.5 rounded-xl transition-all shadow-md shadow-emerald-600/20 disabled:opacity-50"
              >
                <Play size={14} className={runningTest && testMode === "mock" ? "animate-spin" : ""} />
                {runningTest && testMode === "mock" ? "Running Test..." : "Run Sample Invoice Test (Mock OCR)"}
              </button>
              <button
                onClick={() => runReconTest("live")}
                disabled={runningTest}
                className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold px-4 py-2.5 rounded-xl transition-all shadow-md shadow-blue-600/20 disabled:opacity-50"
              >
                <Play size={14} className={runningTest && testMode === "live" ? "animate-spin" : ""} />
                {runningTest && testMode === "live" ? "Running OCR..." : "Run Live Image OCR Test"}
              </button>
            </div>
          </div>

          {/* Error display */}
          {testError && (
            <div className="bg-red-50 text-red-800 p-4 rounded-2xl border border-red-200 text-sm flex items-center gap-3">
              <XCircle className="text-red-600 shrink-0" />
              <span>Test execution failed: {testError}</span>
            </div>
          )}

          {/* Test Results Visual Timeline */}
          {testResult && (
            <div className="space-y-6">
              {/* Summary KPIs Banner */}
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 bg-gray-50 p-4 rounded-2xl border border-gray-200/70">
                <div className="p-3 bg-white rounded-xl border border-gray-100">
                  <span className="text-xs text-gray-500 font-medium block">Total Pipeline Time</span>
                  <span className="text-lg font-black text-gray-900 font-mono mt-0.5 block">
                    {testResult.total_duration_ms} ms
                  </span>
                </div>
                <div className="p-3 bg-white rounded-xl border border-gray-100">
                  <span className="text-xs text-gray-500 font-medium block">Statutory Verdict</span>
                  <span className="text-sm font-black text-blue-700 mt-0.5 block uppercase">
                    {testResult.verdict?.status || "Unknown"}
                  </span>
                </div>
                <div className="p-3 bg-white rounded-xl border border-gray-100">
                  <span className="text-xs text-gray-500 font-medium block">Legal Section Cited</span>
                  <span className="text-sm font-black text-purple-700 mt-0.5 block">
                    Section {testResult.verdict?.legal_section || "16(2)"}
                  </span>
                </div>
                <div className="p-3 bg-white rounded-xl border border-gray-100">
                  <span className="text-xs text-gray-500 font-medium block">Fraud Risk Score</span>
                  <span className="text-sm font-black text-gray-900 mt-0.5 block">
                    {testResult.fraud?.total_score || 0} / 100
                  </span>
                </div>
              </div>

              {/* Step-by-Step Node Execution Trace */}
              <div className="space-y-3">
                <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider">
                  Step-by-Step Node Execution Trace ({testResult.steps_count} Nodes)
                </h3>
                <div className="space-y-2.5">
                  {testResult.steps?.map((step) => {
                    const isExpanded = expandedStep === step.step_num;
                    return (
                      <div 
                        key={step.step_num} 
                        className="border border-gray-200 rounded-2xl overflow-hidden bg-white shadow-sm transition-all"
                      >
                        <button
                          onClick={() => setExpandedStep(isExpanded ? null : step.step_num)}
                          className="w-full p-4 flex items-center justify-between text-left hover:bg-gray-50/50 transition-colors"
                        >
                          <div className="flex items-center gap-3">
                            <span className="w-7 h-7 rounded-full bg-blue-100 text-blue-800 font-extrabold text-xs flex items-center justify-center shrink-0">
                              {step.step_num}
                            </span>
                            <div>
                              <div className="flex items-center gap-2">
                                {getStepIcon(step.status)}
                                <span className="font-bold text-gray-900 text-sm md:text-base">
                                  {step.title}
                                </span>
                              </div>
                              <p className="text-xs text-gray-500 mt-0.5">{step.summary}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2 text-gray-400">
                            <span className="text-xs font-mono text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                              Node: {step.node}
                            </span>
                            {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                          </div>
                        </button>

                        {/* Expanded Payload & Detailed JSON */}
                        {isExpanded && step.details && (
                          <div className="p-4 bg-gray-50 border-t border-gray-100 text-xs font-mono text-gray-800 overflow-x-auto">
                            <pre className="bg-white p-3 rounded-xl border border-gray-200/70 max-h-60 overflow-y-auto">
                              {JSON.stringify(step.details, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Bilingual Diagnosis Preview Box */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                <div className="bg-emerald-50/70 border border-emerald-200 p-5 rounded-2xl space-y-2">
                  <div className="flex items-center gap-2 text-emerald-900 font-bold text-sm">
                    <Send size={16} /> WhatsApp Diagnosis Preview (Hindi / Hinglish)
                  </div>
                  <pre className="text-xs font-sans whitespace-pre-wrap text-emerald-950 bg-white/80 p-3.5 rounded-xl border border-emerald-100">
                    {testResult.diagnosis_hi || "No Hindi diagnosis generated."}
                  </pre>
                </div>

                <div className="bg-blue-50/70 border border-blue-200 p-5 rounded-2xl space-y-2">
                  <div className="flex items-center gap-2 text-blue-900 font-bold text-sm">
                    <Send size={16} /> Email / Webhook Diagnosis Preview (English)
                  </div>
                  <pre className="text-xs font-sans whitespace-pre-wrap text-blue-950 bg-white/80 p-3.5 rounded-xl border border-blue-100">
                    {testResult.diagnosis_en || "No English diagnosis generated."}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
