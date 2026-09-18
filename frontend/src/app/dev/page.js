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
    if (state.status === "online") return "bg-emerald-50/70 text-emerald-800 border-emerald-200";
    if (state.status === "offline") return "bg-red-50 text-red-800 border-red-200";
    return "bg-amber-50 text-amber-800 border-amber-200";
  };

  const getStatusDot = (state) => {
    if (!state) return "bg-gray-400";
    if (state.status === "online") return "bg-[#10b981]";
    if (state.status === "offline") return "bg-red-500";
    return "bg-amber-500";
  };

  const getStepIcon = (status) => {
    if (status === "success") return <CheckCircle2 size={18} className="text-[#10b981]" />;
    if (status === "warning") return <AlertTriangle size={18} className="text-amber-600" />;
    return <XCircle size={18} className="text-red-600" />;
  };

  const StatusCard = ({ id, title, icon: Icon, data, subtitle }) => {
    const isThisPinging = pingingService === id;
    return (
      <div className={`p-5 rounded-2xl border ${getStatusColor(data)} transition-all shadow-sm flex flex-col justify-between bg-white/90`}>
        <div>
          <div className="flex justify-between items-start mb-3">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-gray-50 border border-gray-100">
                <Icon size={18} className="text-gray-700" />
              </div>
              <div>
                <h3 className="font-bold text-gray-900 leading-tight text-sm">{title}</h3>
                <p className="text-[11px] text-gray-500">{subtitle || data?.category || "Service"}</p>
              </div>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-white border border-gray-200/60 shadow-xs">
              <div className={`w-2 h-2 rounded-full ${getStatusDot(data)} ${data?.status === "online" ? "animate-pulse" : ""}`} />
              <span className="text-[10px] font-bold uppercase tracking-wider text-gray-700">
                {data?.status || "Unknown"}
              </span>
            </div>
          </div>
          
          <div className="space-y-1.5 my-3 bg-gray-50/80 p-2.5 rounded-xl border border-gray-100/80">
            <div className="flex justify-between text-xs">
              <span className="text-gray-500 font-medium">Latency</span>
              <span className="font-mono font-bold text-gray-800">{data?.latency_ms !== undefined ? `${data.latency_ms}ms` : "—"}</span>
            </div>
            <div className="flex justify-between text-xs items-center">
              <span className="text-gray-500 font-medium">Message</span>
              <span className="font-mono text-gray-800 truncate ml-2 max-w-[170px]" title={data?.message}>{data?.message || "—"}</span>
            </div>
          </div>
        </div>

        <div className="pt-2 border-t border-gray-200/40 flex justify-end">
          <button
            onClick={() => fetchStatus(id)}
            disabled={isThisPinging || loading}
            className="flex items-center gap-1.5 text-xs font-bold bg-white text-gray-700 hover:text-[#10b981] hover:bg-emerald-50 border border-gray-200 px-3 py-1.5 rounded-lg transition-all shadow-xs disabled:opacity-50"
          >
            <RefreshCw size={12} className={isThisPinging ? "animate-spin text-[#10b981]" : ""} />
            {isThisPinging ? "Pinging..." : "Ping & Test"}
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] flex flex-col font-sans text-gray-900">
      {/* Dev Portal Dedicated Topbar (No Trader Auth / No Sidebar) */}
      <header className="flex-none h-[65px] px-8 border-b border-gray-200 bg-white flex items-center justify-between sticky top-0 z-10 shadow-xs">
        <div className="flex items-center gap-3">
          <a href="/dev" className="flex items-center gap-2.5 text-gray-900 font-extrabold text-lg tracking-tight no-underline">
            <span>Munim.ai</span>
            <span className="text-xs text-emerald-700 font-bold bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded-full uppercase tracking-wider">
              DEV TELEMETRY
            </span>
          </a>
        </div>
        <div className="flex items-center gap-3">
          <a 
            href="http://localhost:8000/docs" 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-xs font-bold text-gray-600 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 no-underline"
          >
            <FileText size={13} className="text-blue-600" />
            <span>API Swagger Reference</span>
          </a>
          <a 
            href="/" 
            className="text-xs font-bold text-gray-600 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 no-underline"
          >
            <span>Trader Portal Login</span>
          </a>
          <span className="text-xs text-gray-400 font-mono hidden sm:inline ml-2">
            Last check: {lastUpdated || "Never"}
          </span>
          <button 
            onClick={() => fetchStatus(null)}
            disabled={loading}
            className="flex items-center gap-2 bg-[#10b981] text-white font-bold px-4 py-2 rounded-lg hover:bg-emerald-600 disabled:opacity-50 transition-all text-xs shadow-sm"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            {loading ? "Checking..." : "Ping All Services"}
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-8 overflow-y-auto space-y-8 max-w-7xl mx-auto w-full">
          {/* Error State */}
          {status?.error && (
            <div className="bg-red-50 text-red-800 p-4 rounded-2xl border border-red-200 font-mono text-sm flex items-center gap-3">
              <XCircle className="text-red-600 shrink-0" />
              <span>Backend Unreachable: {status.error}</span>
            </div>
          )}

          {/* System Diagnostics Grid (7 Core Services) */}
          <div>
            <h2 className="text-base font-extrabold text-gray-900 mb-4 flex items-center gap-2">
              <Layers className="text-[#10b981]" size={18} />
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
          <div className="bg-white p-6 md:p-8 rounded-2xl shadow-sm border border-gray-200 space-y-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-4 border-b border-gray-100">
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-[#10b981] uppercase tracking-wider">
                    Live Test Bench
                  </span>
                  <h2 className="text-lg font-extrabold text-gray-900 flex items-center gap-2">
                    <ShieldCheck className="text-[#10b981]" />
                    LangGraph Autonomous Reconciliation Sandbox
                  </h2>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Test the 7-node autonomous reconciliation pipeline in isolation without needing WhatsApp or external triggers.
                </p>
              </div>
              
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={() => runReconTest("mock")}
                  disabled={runningTest}
                  className="flex items-center gap-2 bg-[#10b981] hover:bg-emerald-600 text-white text-xs font-bold px-4 py-2.5 rounded-xl transition-all shadow-sm disabled:opacity-50"
                >
                  <Play size={14} className={runningTest && testMode === "mock" ? "animate-spin" : ""} />
                  {runningTest && testMode === "mock" ? "Running Test..." : "Run Sample Invoice Test (Mock OCR)"}
                </button>
                <button
                  onClick={() => runReconTest("live")}
                  disabled={runningTest}
                  className="flex items-center gap-2 bg-gray-900 hover:bg-gray-800 text-white text-xs font-bold px-4 py-2.5 rounded-xl transition-all shadow-sm disabled:opacity-50"
                >
                  <Play size={14} className={runningTest && testMode === "live" ? "animate-spin" : ""} />
                  {runningTest && testMode === "live" ? "Running OCR..." : "Run Live Image OCR Test"}
                </button>
              </div>
            </div>

            {/* Error display */}
            {testError && (
              <div className="bg-red-50 text-red-800 p-4 rounded-xl border border-red-200 text-sm flex items-center gap-3">
                <XCircle className="text-red-600 shrink-0" />
                <span>Test execution failed: {testError}</span>
              </div>
            )}

            {/* Test Results Visual Timeline */}
            {testResult && (
              <div className="space-y-6">
                {/* Summary KPIs Banner */}
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 bg-gray-50 p-4 rounded-xl border border-gray-200/70">
                  <div className="p-3 bg-white rounded-xl border border-gray-100">
                    <span className="text-xs text-gray-500 font-medium block">Total Pipeline Time</span>
                    <span className="text-base font-black text-gray-900 font-mono mt-0.5 block">
                      {testResult.total_duration_ms} ms
                    </span>
                  </div>
                  <div className="p-3 bg-white rounded-xl border border-gray-100">
                    <span className="text-xs text-gray-500 font-medium block">Statutory Verdict</span>
                    <span className="text-xs font-black text-[#10b981] mt-0.5 block uppercase">
                      {testResult.verdict?.status || "Unknown"}
                    </span>
                  </div>
                  <div className="p-3 bg-white rounded-xl border border-gray-100">
                    <span className="text-xs text-gray-500 font-medium block">Legal Section Cited</span>
                    <span className="text-xs font-black text-gray-900 mt-0.5 block">
                      Section {testResult.verdict?.legal_section || "16(2)"}
                    </span>
                  </div>
                  <div className="p-3 bg-white rounded-xl border border-gray-100">
                    <span className="text-xs text-gray-500 font-medium block">Fraud Risk Score</span>
                    <span className="text-xs font-black text-gray-900 mt-0.5 block">
                      {testResult.fraud?.total_score || 0} / 100
                    </span>
                  </div>
                </div>

                {/* Step-by-Step Node Execution Trace */}
                <div className="space-y-3">
                  <h3 className="text-xs font-bold text-gray-600 uppercase tracking-wider">
                    Step-by-Step Node Execution Trace ({testResult.steps_count} Nodes)
                  </h3>
                  <div className="space-y-2.5">
                    {testResult.steps?.map((step) => {
                      const isExpanded = expandedStep === step.step_num;
                      return (
                        <div 
                          key={step.step_num} 
                          className="border border-gray-200 rounded-xl overflow-hidden bg-white shadow-xs transition-all"
                        >
                          <button
                            onClick={() => setExpandedStep(isExpanded ? null : step.step_num)}
                            className="w-full p-4 flex items-center justify-between text-left hover:bg-gray-50/50 transition-colors"
                          >
                            <div className="flex items-center gap-3">
                              <span className="w-6 h-6 rounded-full bg-emerald-50 text-[#10b981] font-extrabold text-xs flex items-center justify-center shrink-0 border border-emerald-200">
                                {step.step_num}
                              </span>
                              <div>
                                <div className="flex items-center gap-2">
                                  {getStepIcon(step.status)}
                                  <span className="font-bold text-gray-900 text-sm">
                                    {step.title}
                                  </span>
                                </div>
                                <p className="text-xs text-gray-500 mt-0.5">{step.summary}</p>
                              </div>
                            </div>
                            <div className="flex items-center gap-2 text-gray-400">
                              <span className="text-[10px] font-mono text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                                Node: {step.node}
                              </span>
                              {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
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
                  <div className="bg-emerald-50/70 border border-emerald-200 p-5 rounded-xl space-y-2">
                    <div className="flex items-center gap-2 text-emerald-900 font-bold text-xs uppercase tracking-wider">
                      <Send size={14} /> WhatsApp Diagnosis Preview (Hindi / Hinglish)
                    </div>
                    <pre className="text-xs font-sans whitespace-pre-wrap text-emerald-950 bg-white/80 p-3.5 rounded-xl border border-emerald-100">
                      {testResult.diagnosis_hi || "No Hindi diagnosis generated."}
                    </pre>
                  </div>

                  <div className="bg-gray-50 border border-gray-200 p-5 rounded-xl space-y-2">
                    <div className="flex items-center gap-2 text-gray-900 font-bold text-xs uppercase tracking-wider">
                      <Send size={14} /> Email / Webhook Diagnosis Preview (English)
                    </div>
                    <pre className="text-xs font-sans whitespace-pre-wrap text-gray-900 bg-white/80 p-3.5 rounded-xl border border-gray-200">
                      {testResult.diagnosis_en || "No English diagnosis generated."}
                    </pre>
                  </div>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    );
  }
