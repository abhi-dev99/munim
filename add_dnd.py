import os
filepath = 'frontend/src/app/dashboard/page.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add useRef to imports
if 'useRef' not in content:
    content = content.replace('import { useState, useEffect } from "react";', 'import { useState, useEffect, useRef } from "react";')
elif 'useRef' not in content and 'import React' in content:
    content = content.replace('import React', 'import React, { useRef }')

# Replace layoutPrefs state with full prefs state and add DND logic
dnd_logic = """
  const [fullPrefs, setFullPrefs] = useState(null);
  const dragItem = useRef(null);
  const dragOverItem = useRef(null);

  useEffect(() => {
    if (!traderId) return;
    authFetch(`${API_BASE}/api/v1/dashboard/preferences/${traderId}`)
      .then(r => r.json())
      .then(d => {
        if (d.dashboard) setFullPrefs(d);
      }).catch(console.error);
  }, [traderId]);

  const defaultRightRail = ["supplier_risk", "filing_readiness", "eway_bills", "quick_links"];
  const rightRailOrder = fullPrefs?.dashboard || defaultRightRail;

  const handleSort = async () => {
    let _rightRailOrder = [...rightRailOrder];
    const draggedItemContent = _rightRailOrder.splice(dragItem.current, 1)[0];
    _rightRailOrder.splice(dragOverItem.current, 0, draggedItemContent);
    dragItem.current = null;
    dragOverItem.current = null;
    
    const newPrefs = { ...fullPrefs, dashboard: _rightRailOrder };
    if (!newPrefs.sidebar) newPrefs.sidebar = ["money-meter", "suppliers", "actions", "reports"]; // fallback
    
    setFullPrefs(newPrefs);
    
    // Save to backend
    try {
      await authFetch(`${API_BASE}/api/v1/dashboard/preferences/${traderId}`, {
        method: "POST",
        body: JSON.stringify(newPrefs)
      });
    } catch(e) {
      console.error("Failed to save new layout order:", e);
    }
  };

  const renderRightRailWidget = (id, index) => {
    let widget = null;
    switch (id) {
      case "supplier_risk": widget = <SupplierRiskCard traderId={traderId} onSwitchTab={setActiveTab} />; break;
      case "filing_readiness": widget = <FilingReadinessCard traderId={traderId} summary={summary} onSwitchTab={setActiveTab} />; break;
      case "eway_bills": widget = <EWayBillCard />; break;
      case "quick_links": widget = <QuickLinksCard traderId={traderId} />; break;
      default: return null;
    }
    
    return (
      <div 
        key={id}
        draggable
        onDragStart={(e) => { dragItem.current = index; }}
        onDragEnter={(e) => { dragOverItem.current = index; e.preventDefault(); }}
        onDragOver={(e) => e.preventDefault()}
        onDragEnd={handleSort}
        className="cursor-grab active:cursor-grabbing hover:ring-2 hover:ring-gray-200 transition-all rounded-xl relative"
        title="Drag to reorder"
      >
        <div className="absolute top-2 right-2 opacity-0 hover:opacity-100 z-10 p-1 bg-white/80 rounded backdrop-blur-sm pointer-events-none transition-opacity">
           <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-gray-400"><circle cx="9" cy="12" r="1"></circle><circle cx="9" cy="5" r="1"></circle><circle cx="9" cy="19" r="1"></circle><circle cx="15" cy="12" r="1"></circle><circle cx="15" cy="5" r="1"></circle><circle cx="15" cy="19" r="1"></circle></svg>
        </div>
        {widget}
      </div>
    );
  };
"""

# Replace the old logic
search_old = """
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

# And we also need to change `{rightRailOrder.map(renderRightRailWidget)}` to passing index: `{rightRailOrder.map((id, idx) => renderRightRailWidget(id, idx))}`
if search_old.strip() in content:
    content = content.replace(search_old.strip(), dnd_logic.strip())
    content = content.replace('{rightRailOrder.map(renderRightRailWidget)}', '{rightRailOrder.map((id, idx) => renderRightRailWidget(id, idx))}')
else:
    print("Could not find old layoutPrefs logic!")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Added DND to dashboard/page.js")
