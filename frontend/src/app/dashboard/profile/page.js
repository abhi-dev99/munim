"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  User,
  Building2,
  Phone,
  Mail,
  MapPin,
  CreditCard,
  Save,
  ArrowLeft,
  Users,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Edit3,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function StatCard({ icon: Icon, label, value, color = "gray", sub }) {
  const colors = {
    green:  "bg-emerald-50 border-emerald-200 text-emerald-700",
    red:    "bg-red-50 border-red-200 text-red-700",
    amber:  "bg-amber-50 border-amber-200 text-amber-700",
    gray:   "bg-gray-50 border-gray-200 text-gray-700",
  };
  return (
    <div className={`rounded-xl border p-4 ${colors[color]}`}>
      <div className="flex items-center gap-2 mb-1">
        <Icon size={15} />
        <span className="text-xs font-semibold uppercase tracking-wide">{label}</span>
      </div>
      <p className="text-2xl font-bold mt-1">{value}</p>
      {sub && <p className="text-[11px] mt-0.5 opacity-70">{sub}</p>}
    </div>
  );
}

function InputField({ label, value, onChange, type = "text", disabled = false, icon: Icon }) {
  return (
    <div>
      <label className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">
        {label}
      </label>
      <div className="relative">
        {Icon && <Icon size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />}
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className={`w-full ${Icon ? "pl-9" : "pl-3"} pr-3 py-2.5 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:border-[#10b981] focus:ring-2 focus:ring-[#10b981]/10 transition-all ${disabled ? "bg-gray-50 text-gray-400 cursor-not-allowed" : "text-gray-900"}`}
        />
      </div>
    </div>
  );
}

export default function ProfilePage() {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [traders, setTraders] = useState([]);
  const [profile, setProfile] = useState({
    name: "",
    email: "",
    phone: "",
    firm_name: "",
    membership_no: "",
    city: "",
    state: "",
    gstin: "",
  });

  useEffect(() => {
    const authUser = localStorage.getItem("munim_auth_trader");
    if (!authUser) { router.push("/"); return; }
    const parsed = JSON.parse(authUser);

    // Pre-fill from localStorage
    setProfile(prev => ({
      ...prev,
      name: parsed.name || parsed.business_name || "",
      phone: parsed.whatsapp_number || "",
      email: parsed.email || "",
      gstin: parsed.gstin || "",
      firm_name: parsed.firm_name || parsed.business_name || "",
      membership_no: parsed.membership_no || "",
      city: parsed.city || "",
      state: parsed.state || "",
    }));

    // Fetch all traders managed by this CA
    fetch(`${API_BASE}/api/v1/dashboard/traders`)
      .then(r => r.json())
      .then(d => setTraders(d.traders || []))
      .catch(() => setTraders([]));
  }, []);

  async function handleSave() {
    setSaving(true);
    // Persist locally (backend endpoint can be wired later)
    const authUser = localStorage.getItem("munim_auth_trader");
    if (authUser) {
      const parsed = JSON.parse(authUser);
      localStorage.setItem("munim_auth_trader", JSON.stringify({ ...parsed, ...profile }));
    }
    await new Promise(r => setTimeout(r, 800)); // simulated save
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  }

  const totalClients    = traders.length;
  const withIssues      = traders.filter(t => t.open_issues > 0).length;
  const avgCompliance   = traders.length
    ? Math.round(traders.reduce((s, t) => s + (t.compliance_score || 100), 0) / traders.length)
    : null;

  return (
    <div className="flex h-screen overflow-hidden bg-[#f8f9fa]">
      {/* Minimal sidebar strip */}
      <aside className="w-64 fixed h-full bg-white border-r border-gray-200 z-10 flex flex-col">
        <div className="px-6 h-[65px] flex items-center border-b border-gray-200">
          <button
            onClick={() => router.push("/dashboard")}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
          >
            <ArrowLeft size={16} />
            <span className="font-semibold text-sm">Back to Dashboard</span>
          </button>
        </div>
        <div className="p-6">
          <div className="flex flex-col items-center text-center">
            <div className="w-16 h-16 rounded-full bg-[#10b981] text-white flex items-center justify-center text-2xl font-bold mb-3">
              {profile.name?.charAt(0)?.toUpperCase() || "CA"}
            </div>
            <p className="font-bold text-gray-900 text-sm">{profile.name || "Your Name"}</p>
            <p className="text-xs text-gray-500 mt-0.5">{profile.firm_name || "Your Firm"}</p>
            {profile.membership_no && (
              <p className="text-[10px] text-[#10b981] font-mono mt-1 bg-emerald-50 px-2 py-0.5 rounded">
                ICAI #{profile.membership_no}
              </p>
            )}
          </div>
        </div>
      </aside>

      <main className="flex-1 ml-64 flex flex-col overflow-y-auto">
        {/* Header */}
        <header className="flex-none h-[65px] px-8 border-b border-gray-200 bg-white flex items-center gap-3 sticky top-0 z-10">
          <User size={18} className="text-[#10b981]" />
          <h1 className="text-base font-bold text-gray-900">My Profile</h1>
          <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">CA Dashboard</span>
        </header>

        <div className="p-8 max-w-4xl mx-auto w-full space-y-8">
          {/* Portfolio Overview */}
          <section>
            <h2 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-3">Portfolio Overview</h2>
            <div className="grid grid-cols-3 gap-4">
              <StatCard icon={Users}       label="Total Clients"     value={totalClients || "—"}        color="gray"  />
              <StatCard icon={AlertTriangle} label="With Issues"     value={withIssues || "0"}          color={withIssues > 0 ? "amber" : "green"} sub={withIssues > 0 ? "Click Action Queue to review" : "All clients are compliant"} />
              <StatCard icon={CheckCircle2}  label="Avg Compliance"  value={avgCompliance ? `${avgCompliance}%` : "—"} color={avgCompliance >= 80 ? "green" : avgCompliance >= 50 ? "amber" : "red"} />
            </div>
          </section>

          {/* Client List */}
          {traders.length > 0 && (
            <section>
              <h2 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-3">Clients ({traders.length})</h2>
              <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 bg-gray-50">
                      <th className="text-left px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-gray-500">Business Name</th>
                      <th className="text-left px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-gray-500">GSTIN</th>
                      <th className="text-left px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-gray-500">Phone</th>
                      <th className="text-right px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-gray-500">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {traders.map(t => (
                      <tr key={t.id} className="hover:bg-gray-50/60 transition-colors">
                        <td className="px-4 py-3 font-semibold text-gray-900">{t.name || t.business_name || "—"}</td>
                        <td className="px-4 py-3 font-mono text-xs text-gray-500 bg-gray-50">{t.gstin || "Not set"}</td>
                        <td className="px-4 py-3 text-gray-600">{t.whatsapp_number || "—"}</td>
                        <td className="px-4 py-3 text-right">
                          {(t.open_issues || 0) > 0 ? (
                            <span className="text-xs font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full">
                              {t.open_issues} issues
                            </span>
                          ) : (
                            <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                              Compliant
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* Profile Form */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-bold text-gray-500 uppercase tracking-wider">Personal Details</h2>
              <div className="flex items-center gap-1.5 text-xs text-gray-400">
                <Edit3 size={11} />
                <span>Editable</span>
              </div>
            </div>
            <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-5">
              <div className="grid grid-cols-2 gap-4">
                <InputField label="Full Name"         value={profile.name}           onChange={v => setProfile(p => ({ ...p, name: v }))}           icon={User}      />
                <InputField label="Firm / Practice Name" value={profile.firm_name}    onChange={v => setProfile(p => ({ ...p, firm_name: v }))}        icon={Building2} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <InputField label="Email"             value={profile.email}          onChange={v => setProfile(p => ({ ...p, email: v }))}            type="email" icon={Mail}  />
                <InputField label="WhatsApp / Phone"  value={profile.phone}          onChange={v => setProfile(p => ({ ...p, phone: v }))}            type="tel"   icon={Phone} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <InputField label="ICAI Membership No." value={profile.membership_no} onChange={v => setProfile(p => ({ ...p, membership_no: v }))}   icon={CreditCard} />
                <InputField label="GSTIN (Practice)"  value={profile.gstin}          onChange={v => setProfile(p => ({ ...p, gstin: v }))}            icon={CreditCard} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <InputField label="City"              value={profile.city}           onChange={v => setProfile(p => ({ ...p, city: v }))}             icon={MapPin} />
                <InputField label="State"             value={profile.state}          onChange={v => setProfile(p => ({ ...p, state: v }))}            icon={MapPin} />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2 border-t border-gray-100">
                {saved && (
                  <div className="flex items-center gap-1.5 text-emerald-600 text-sm font-semibold">
                    <CheckCircle2 size={15} />
                    Saved!
                  </div>
                )}
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center gap-2 bg-[#10b981] hover:bg-emerald-600 text-white px-5 py-2.5 rounded-lg text-sm font-bold transition-colors disabled:opacity-60 shadow-sm"
                >
                  {saving ? (
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                  ) : (
                    <Save size={14} />
                  )}
                  {saving ? "Saving…" : "Save Changes"}
                </button>
              </div>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
