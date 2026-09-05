import os
filepath = 'frontend/src/app/dashboard/page.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add driver imports
if 'import { driver }' not in content:
    content = content.replace('import MoneyMeter from "../components/MoneyMeter";', 'import MoneyMeter from "../components/MoneyMeter";\nimport { driver } from "driver.js";\nimport "driver.js/dist/driver.css";')

# 2. Add handlers and tour logic
logic = """
  const handleMoneyMeterSortTop = async (newOrder) => {
    const newPrefs = { ...fullPrefs, money_meter_top: newOrder };
    setFullPrefs(newPrefs);
    try {
      await authFetch(`${API_BASE}/api/v1/dashboard/preferences/${traderId}`, { method: "POST", body: JSON.stringify(newPrefs) });
    } catch(e) { console.error(e); }
  };

  const handleMoneyMeterSortBottom = async (newOrder) => {
    const newPrefs = { ...fullPrefs, money_meter_bottom: newOrder };
    setFullPrefs(newPrefs);
    try {
      await authFetch(`${API_BASE}/api/v1/dashboard/preferences/${traderId}`, { method: "POST", body: JSON.stringify(newPrefs) });
    } catch(e) { console.error(e); }
  };

  const startTour = () => {
    const driverObj = driver({
      showProgress: true,
      steps: [
        { popover: { title: 'Welcome to the CA Dashboard', description: 'Let us show you around your new workspace.', side: "bottom", align: 'start' } },
        { element: '#money-meter-top', popover: { title: 'ITC Metrics', description: 'These are your core ITC metrics. You can drag and drop these cards to reorder them based on what you want to see first!', side: "bottom", align: 'start' } },
        { element: '#money-meter-bottom', popover: { title: 'Quick Stats', description: 'Track your processed invoices and open issues. These are also fully drag-and-drop enabled.', side: "bottom", align: 'start' } },
        { popover: { title: 'Right Rail Widgets', description: 'All the widgets on the right side of your dashboard can also be dragged and dropped into any order you prefer.', side: "left", align: 'start' } }
      ]
    });
    driverObj.drive();
  };
"""

if 'const handleMoneyMeterSortTop' not in content:
    content = content.replace('const handleSort = async () => {', logic + '\n  const handleSort = async () => {')

# 3. Add tour button
tour_btn = """<div className="flex items-center gap-3">
              <button onClick={startTour} className="px-4 py-2 bg-indigo-50 text-indigo-600 rounded-lg text-sm font-semibold hover:bg-indigo-100 transition-colors">
                Take Tour
              </button>
              {profile && ("""
if '{profile && (' in content and 'Take Tour' not in content:
    content = content.replace('{profile && (', tour_btn)

# 4. Update MoneyMeter props
old_mm = '<MoneyMeter summary={summary} apiBase={API_BASE} isComposition={isComposition} onSwitchTab={setActiveTab} />'
new_mm = '<MoneyMeter summary={summary} apiBase={API_BASE} isComposition={isComposition} onSwitchTab={setActiveTab} prefs={fullPrefs} onSortTop={handleMoneyMeterSortTop} onSortBottom={handleMoneyMeterSortBottom} />'
if old_mm in content:
    content = content.replace(old_mm, new_mm)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched dashboard/page.js")
