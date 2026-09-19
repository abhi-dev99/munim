"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2, ShieldCheck, Zap, Smartphone } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// verify-otp matches the submitted number against a trader's own
// whatsapp_number first, falling back to a CA's ca_whatsapp_number on any
// of their clients (see backend/app/api/auth.py) -- it returns whichever
// trader record matched, with no separate flag saying which path it took.
// Comparing the last 10 digits (ignoring a "91"/"+91" country-code prefix,
// same normalization deps.py:verify_trader_access uses) recovers that: a
// match means this number IS that trader, a mismatch means it only got in
// via ca_whatsapp_number, i.e. this is the CA logging in to manage a client.
function last10Digits(phone) {
  const digits = (phone || "").replace(/\D/g, "");
  return digits.slice(-10);
}

// The /trader page is a mobile-first PWA experience (built for a phone-sized
// WhatsApp-style flow) -- opening it in a laptop browser looks unfinished,
// not "responsive." A trader's own account should still land on /dashboard
// when accessed from a desktop rather than showing that mobile view full of
// unused whitespace; /dashboard already handles a single trader with no CA
// clients gracefully (backend/app/api/dashboard.py's /traders endpoint
// returns just that trader's own row when there's nothing else to list), so
// there's a real, working page to send desktop traders to instead. A CA's
// own login already goes to /dashboard regardless of device -- unaffected.
function isMobileDevice() {
  if (typeof navigator === "undefined") return false;
  return /Android|iPhone|iPad|iPod|Mobile|Windows Phone/i.test(navigator.userAgent);
}

function destinationFor(isTraderRole) {
  return isTraderRole && isMobileDevice() ? "/trader" : "/dashboard";
}

export default function LoginPage() {
  const router = useRouter();
  const [mobileNumber, setMobileNumber] = useState("");
  const [otp, setOtp] = useState("");
  const [step, setStep] = useState(1); // 1 = mobile, 2 = otp, 3 = choose role (dual-role accounts only)
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [roleChoices, setRoleChoices] = useState([]);

  useEffect(() => {
    // Auto-redirect if already logged in (need BOTH token and trader data)
    const token = localStorage.getItem("munim_auth_token");
    const trader = localStorage.getItem("munim_auth_trader");
    if (token && trader) {
      // munim_auth_role is set at login time (see handleVerifyOtp) — a
      // session from before this fix existed won't have it, so default to
      // the old always-/dashboard behavior rather than guessing.
      const role = localStorage.getItem("munim_auth_role");
      router.push(destinationFor(role === "trader"));
    } else if (token && !trader) {
      // Orphaned token from a bad logout — clean it up
      localStorage.removeItem("munim_auth_token");
    }
  }, [router]);

  const handleRequestOtp = async (e) => {
    e.preventDefault();
    if (!mobileNumber || mobileNumber.length < 10) {
      setError("Please enter a valid mobile number.");
      return;
    }
    
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/request-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mobile_number: mobileNumber }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to send OTP.");
      }

      setStep(2);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    if (!otp || otp.length < 4) {
      setError("Please enter a valid OTP.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/verify-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mobile_number: mobileNumber, otp }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Invalid OTP.");
      }

      // Store auth state for dashboard protection
      if (data.trader) {
        localStorage.setItem("munim_auth_trader", JSON.stringify(data.trader));
      }
      if (data.token) {
        localStorage.setItem("munim_auth_token", data.token);
      }

      // verify-otp now tells us directly which role(s) this phone number
      // actually has (backend/app/api/auth.py) -- own trader account, CA for
      // someone else's, or both -- instead of us re-deriving it from a
      // number comparison here. Most logins have exactly one role and go
      // straight through; a genuine dual-role account (real in the seed
      // data, see CLAUDE.md) gets a one-time "log in as" choice instead of
      // silently picking one.
      const roles = data.roles || [];
      if (roles.length > 1) {
        setRoleChoices(roles);
        setStep(3);
        setLoading(false);
        return;
      }

      const role = roles[0] || "trader";
      localStorage.setItem("munim_auth_role", role);
      router.push(destinationFor(role === "trader"));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleChooseRole = (role) => {
    localStorage.setItem("munim_auth_role", role);
    router.push(destinationFor(role === "trader"));
  };

  return (
    <div className="min-h-screen flex w-full">
      {/* Left Side: Marketing/Value Prop (White) */}
      <div className="hidden lg:flex w-1/2 bg-white flex-col justify-center px-20">
        <div className="max-w-xl">
          <div className="font-bold text-4xl tracking-tight text-black mb-10">
            Munim.ai
          </div>
          <h1 className="text-6xl font-black text-black tracking-tighter leading-none mb-6">
            The CA in your pocket.
          </h1>
          <p className="text-xl text-[var(--text-secondary)] font-medium mb-12 max-w-md">
            Automate your GST compliance, instantly reconcile ITC, and never miss a filing deadline again.
          </p>

          <div className="space-y-6">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center flex-shrink-0">
                <Zap size={20} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-black">Lightning Fast Sync</h3>
                <p className="text-[var(--text-secondary)] font-medium text-sm">Pull your GSTR-2B and invoices directly from the GST Portal in seconds.</p>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-full bg-green-50 text-[var(--green-primary)] flex items-center justify-center flex-shrink-0">
                <ShieldCheck size={20} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-black">Bulletproof Compliance</h3>
                <p className="text-[var(--text-secondary)] font-medium text-sm">Smart AI detects HSN rate mismatches and blocked ITC before you file.</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right Side: Login Portal (Dark Grey/Black) */}
      <div className="w-full lg:w-1/2 bg-[#0a0a0a] flex flex-col justify-center px-8 sm:px-20 relative">
        <div className="max-w-sm mx-auto w-full">
          <h2 className="text-3xl font-bold text-white mb-2">Welcome back</h2>
          <p className="text-gray-400 mb-8 font-medium">Log in to your Munim.ai portal.</p>

          <div className="bg-[#171717] border border-[#2a2a2a] p-8 rounded-2xl shadow-2xl">
            {step === 1 ? (
              <form onSubmit={handleRequestOtp} className="space-y-5">
                <div>
                  <label className="block text-sm font-semibold text-gray-300 mb-2">
                    Mobile Number
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Smartphone size={18} className="text-gray-500" />
                    </div>
                    <input
                      type="tel"
                      value={mobileNumber}
                      onChange={(e) => setMobileNumber(e.target.value)}
                      placeholder="Enter WhatsApp number"
                      className="w-full pl-10 pr-4 py-3 bg-[#0a0a0a] border border-[#2a2a2a] text-white rounded-lg focus:ring-2 focus:ring-[#25D366] focus:border-transparent outline-none transition-all placeholder-gray-600 font-medium"
                      required
                    />
                  </div>
                </div>

                {error && <p className="text-red-400 text-xs font-bold bg-red-400/10 p-2 rounded">{error}</p>}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3 bg-white text-black font-bold rounded-lg hover:bg-gray-200 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {loading ? <Loader2 size={18} className="animate-spin" /> : "Send OTP via WhatsApp"}
                </button>
              </form>
            ) : step === 2 ? (
              <form onSubmit={handleVerifyOtp} className="space-y-5">
                <div>
                  <label className="block text-sm font-semibold text-gray-300 mb-2">
                    Verification Code
                  </label>
                  <input
                    type="text"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value)}
                    placeholder="Enter 6-digit OTP"
                    className="w-full px-4 py-3 bg-[#0a0a0a] border border-[#2a2a2a] text-white rounded-lg focus:ring-2 focus:ring-[#25D366] focus:border-transparent outline-none transition-all placeholder-gray-600 font-mono tracking-widest text-center"
                    maxLength={6}
                    required
                  />
                  <p className="text-xs text-gray-500 mt-2 text-center">
                    Sent to {mobileNumber}
                  </p>
                </div>

                {error && <p className="text-red-400 text-xs font-bold bg-red-400/10 p-2 rounded">{error}</p>}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3 bg-[#25D366] text-black font-bold rounded-lg hover:bg-[#20b858] transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {loading ? <Loader2 size={18} className="animate-spin" /> : "Verify & Login"}
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setStep(1);
                    setError("");
                  }}
                  className="w-full text-center text-sm font-medium text-gray-400 hover:text-white transition-colors"
                >
                  Back to mobile number
                </button>
              </form>
            ) : (
              // Only reached for a genuine dual-role phone number (their own
              // trader account AND someone else's CA identifier -- both real
              // roles, not a guess) -- see auth.py's verify-otp `roles`.
              <div className="space-y-5">
                <div>
                  <h3 className="text-lg font-bold text-white mb-1">Log in as</h3>
                  <p className="text-sm text-gray-400">This number is linked to both a trader account and a CA account.</p>
                </div>
                <div className="flex bg-[#0a0a0a] border border-[#2a2a2a] rounded-full p-1">
                  {roleChoices.includes("trader") && (
                    <button
                      onClick={() => handleChooseRole("trader")}
                      className="flex-1 py-2.5 rounded-full text-sm font-bold text-white hover:bg-[#25D366] hover:text-black transition-colors"
                    >
                      Trader
                    </button>
                  )}
                  {roleChoices.includes("ca") && (
                    <button
                      onClick={() => handleChooseRole("ca")}
                      className="flex-1 py-2.5 rounded-full text-sm font-bold text-white hover:bg-[#25D366] hover:text-black transition-colors"
                    >
                      CA
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

