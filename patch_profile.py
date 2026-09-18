import os
filepath = 'frontend/src/app/dashboard/profile/page.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add imports for ArrowUp, ArrowDown, Eye, EyeOff
if 'EyeOff' not in content:
    content = content.replace('Edit3,\n} from "lucide-react";', 'Edit3,\n  ArrowUp,\n  ArrowDown,\n  Eye,\n  EyeOff,\n} from "lucide-react";')

# Add ConfigDashboardComponent
config_component = """
function ConfigDashboard({ traderId }) {
  const [prefs, setPrefs] = useState({
    dashboard: ["quick_links", "supplier_risk", "filing_readiness", "eway_bills"],
    sidebar: ["dashboard", "money_meter", "reconcile_2b", "suppliers", "reports", "profile"]
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!traderId) return;
    authFetch(`${API_BASE}/api/v1/dashboard/preferences/${traderId}`)
      .then(r => r.json())
      .then(d => {
        if (d.dashboard && d.sidebar) setPrefs(d);
      }).catch(console.error);
  }, [traderId]);

  const toggleVisibility = (listKey, item) => {
    setPrefs(p => {
      const current = p[listKey];
      const isVisible = current.includes(item);
      const updated = isVisible ? current.filter(i => i !== item) : [...current, item];
      return { ...p, [listKey]: updated };
    });
  };

  const moveItem = (listKey, item, dir) => {
    setPrefs(p => {
      const current = [...p[listKey]];
      const idx = current.indexOf(item);
      if (idx === -1) return p;
      if (dir === -1 && idx > 0) {
        const temp = current[idx]; current[idx] = current[idx-1]; current[idx-1] = temp;
      } else if (dir === 1 && idx < current.length - 1) {
        const temp = current[idx]; current[idx] = current[idx+1]; current[idx+1] = temp;
      }
      return { ...p, [listKey]: current };
    });
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await authFetch(`${API_BASE}/api/v1/dashboard/preferences/${traderId}`, {
        method: "POST",
        body: JSON.stringify(prefs)
      });
      alert("Preferences saved successfully! Changes will reflect on refresh.");
    } catch(e) {
      console.error(e);
      alert("Failed to save preferences.");
    } finally {
      setSaving(false);
    }
  };

  const allDashboardWidgets = [
    { id: "quick_links", label: "Quick Links" },
    { id: "supplier_risk", label: "Supplier Risk" },
    { id: "filing_readiness", label: "GSTR-3B Readiness" },
    { id: "eway_bills", label: "E-Way Bills" }
  ];

  const allSidebarWidgets = [
    { id: "dashboard", label: "Dashboard" },
    { id: "money_meter", label: "Money Meter" },
    { id: "reconcile_2b", label: "Reconcile 2B" },
    { id: "suppliers", label: "Suppliers" },
    { id: "reports", label: "Reports" },
    { id: "profile", label: "Profile" }
  ];

  const renderList = (listKey, allItems) => {
    // Sort allItems: active items in order, then inactive items
    const active = prefs[listKey];
    const sorted = [...active, ...allItems.map(i => i.id).filter(id => !active.includes(id))];

    return (
      <div className="space-y-2">
        {sorted.map(id => {
          const item = allItems.find(i => i.id === id);
          if(!item) return null;
          const isVisible = active.includes(id);
          const index = active.indexOf(id);
          return (
            <div key={id} className={`flex items-center justify-between p-3 border rounded-lg ${isVisible ? "bg-white border-gray-200 shadow-sm" : "bg-gray-50 border-gray-100 opacity-60"}`}>
              <div className="flex items-center gap-3">
                <button onClick={() => toggleVisibility(listKey, id)} className="text-gray-400 hover:text-gray-900">
                  {isVisible ? <Eye size={16} className="text-green-600"/> : <EyeOff size={16} />}
                </button>
                <span className={`text-sm font-semibold ${isVisible ? "text-gray-900" : "text-gray-500"}`}>{item.label}</span>
              </div>
              {isVisible && (
                <div className="flex gap-1">
                  <button onClick={() => moveItem(listKey, id, -1)} disabled={index === 0} className="p-1 text-gray-400 hover:bg-gray-100 rounded disabled:opacity-30"><ArrowUp size={14}/></button>
                  <button onClick={() => moveItem(listKey, id, 1)} disabled={index === active.length - 1} className="p-1 text-gray-400 hover:bg-gray-100 rounded disabled:opacity-30"><ArrowDown size={14}/></button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <section className="mb-8">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-bold text-gray-500 uppercase tracking-wider">Configure Layout</h2>
      </div>
      <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <div className="grid grid-cols-2 gap-8">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-4">Dashboard Right Rail</h3>
            {renderList("dashboard", allDashboardWidgets)}
          </div>
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-4">Left Sidebar</h3>
            {renderList("sidebar", allSidebarWidgets)}
          </div>
        </div>
        <div className="mt-6 flex justify-end pt-4 border-t border-gray-100">
          <button onClick={handleSave} disabled={saving} className="bg-black hover:bg-gray-800 text-white px-5 py-2.5 rounded-lg text-sm font-bold shadow-sm transition-colors">
            {saving ? "Saving..." : "Save Configuration"}
          </button>
        </div>
      </div>
    </section>
  );
}
"""

if 'function ConfigDashboard' not in content:
    content = content.replace('export default function ProfilePage() {', config_component + '\nexport default function ProfilePage() {')

# Find where to render it. I'll put it right before Personal Details
if '<ConfigDashboard' not in content:
    trader_id_logic = """
          {/* Profile Form */}
          <ConfigDashboard traderId={traders.length > 0 ? traders[0].ca_whatsapp_number || traders[0].whatsapp_number || profile.phone : profile.phone} />
"""
    content = content.replace('{/* Profile Form */}', trader_id_logic)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched profile/page.js")
