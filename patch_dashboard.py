import os
filepath = 'frontend/src/app/dashboard/page.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

prefs_state = """
  const [layoutPrefs, setLayoutPrefs] = useState(null);

  useEffect(() => {
    if (!traderId) return;
    authFetch(`${API_BASE}/api/v1/dashboard/preferences/${traderId}`)
      .then(r => r.json())
      .then(d => {
        if (d.dashboard) setLayoutPrefs(d.dashboard);
      }).catch(console.error);
  }, [traderId]);

  const defaultRightRail = ["supplier_risk", "filing_readiness", "eway_bills", "quick_links"];
  const rightRailOrder = layoutPrefs || defaultRightRail;

  const renderRightRailWidget = (id) => {
    switch (id) {
      case "supplier_risk": return <SupplierRiskCard key="supplier_risk" traderId={traderId} onSwitchTab={setActiveTab} />;
      case "filing_readiness": return <FilingReadinessCard key="filing_readiness" traderId={traderId} summary={summary} onSwitchTab={setActiveTab} />;
      case "eway_bills": return <EWayBillCard key="eway_bills" />;
      case "quick_links": return <QuickLinksCard key="quick_links" traderId={traderId} />;
      default: return null;
    }
  };
"""

if 'const [layoutPrefs, setLayoutPrefs] = useState(null);' not in content:
    content = content.replace('const [actionCount, setActionCount] = useState(0);', 'const [actionCount, setActionCount] = useState(0);\n' + prefs_state)

old_right_rail = """              <SupplierRiskCard traderId={traderId} onSwitchTab={setActiveTab} />
              <FilingReadinessCard traderId={traderId} summary={summary} onSwitchTab={setActiveTab} />
              <EWayBillCard />
              <QuickLinksCard traderId={traderId} />"""

if old_right_rail in content:
    content = content.replace(old_right_rail, "              {rightRailOrder.map(renderRightRailWidget)}")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched dashboard/page.js")
