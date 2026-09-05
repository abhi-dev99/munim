import os

page_js_path = 'd:/hackathob/kleos-4.0/frontend/src/app/dashboard/page.js'
with open(page_js_path, 'r', encoding='utf-8') as f:
    page_content = f.read()

# 1. Add activeTraderGstin state
if 'const [activeTraderGstin, setActiveTraderGstin] = useState("");' not in page_content:
    page_content = page_content.replace(
        'const [activeBusinessName, setActiveBusinessName] = useState("");',
        'const [activeBusinessName, setActiveBusinessName] = useState("");\n  const [activeTraderGstin, setActiveTraderGstin] = useState("");'
    )

# 2. Set gstin in fetchTraders
if 'setActiveTraderGstin(selected.gstin || "");' not in page_content:
    page_content = page_content.replace(
        'setActiveBusinessName(selected.business_name || selected.name || "");',
        'setActiveBusinessName(selected.business_name || selected.name || "");\n        setActiveTraderGstin(selected.gstin || "");'
    )

# 3. Set gstin in switchTrader
if 'setActiveTraderGstin(trader.gstin || "");' not in page_content:
    page_content = page_content.replace(
        'setActiveBusinessName(trader.business_name || trader.name || "");',
        'setActiveBusinessName(trader.business_name || trader.name || "");\n    setActiveTraderGstin(trader.gstin || "");'
    )

# 4. Add GSTIN display and Copy logic near activeTraderName
gstin_display = """
                  <button
                    onClick={() => setTraderDropdown(!traderDropdown)}
                    className="flex items-center gap-2 hover:bg-gray-100 py-1.5 px-2 rounded-lg transition-colors"
                  >
                    <Users size={15} className="text-gray-400" />
                    <span className="text-sm font-semibold text-gray-800 max-w-[140px] truncate">
                      {activeTraderName}
                    </span>
                    <ChevronDown size={13} className="text-gray-400" />
                  </button>
                  {activeTraderGstin && (
                    <span 
                      onClick={() => {
                        navigator.clipboard.writeText(activeTraderGstin);
                        alert("GSTIN Copied!");
                      }}
                      className="ml-2 text-[10px] font-mono font-bold bg-gray-100 text-gray-500 px-2 py-1 rounded cursor-pointer hover:bg-gray-200 transition-colors"
                      title="Copy GSTIN"
                    >
                      {activeTraderGstin}
                    </span>
                  )}
"""

old_trader_btn = """                  <button
                    onClick={() => setTraderDropdown(!traderDropdown)}
                    className="flex items-center gap-2 hover:bg-gray-100 py-1.5 px-2 rounded-lg transition-colors"
                  >
                    <Users size={15} className="text-gray-400" />
                    <span className="text-sm font-semibold text-gray-800 max-w-[140px] truncate">
                      {activeTraderName}
                    </span>
                    <ChevronDown size={13} className="text-gray-400" />
                  </button>"""
page_content = page_content.replace(old_trader_btn, gstin_display)

# 5. Remove Language Toggle
lang_toggle = """                {/* Language toggle */}
                <button
                  onClick={() => changeLanguage(lang === "en" ? "hi" : "en")}
                  className="flex items-center gap-2 bg-white border border-gray-200 rounded-lg px-3 py-2 hover:bg-gray-50 transition-colors shadow-sm"
                  title="Toggle Language"
                >
                  <Globe size={15} className="text-gray-400" />
                  <span className="text-sm font-semibold text-gray-800">
                    {lang === "en" ? "हिं" : "English"}
                  </span>
                </button>"""
page_content = page_content.replace(lang_toggle, "")

# 6. Remove Take Tour button from header
take_tour_btn = """                <button 
                  onClick={startTour} 
                  className="hidden md:block px-4 py-2 bg-indigo-50 text-indigo-600 rounded-lg text-sm font-semibold hover:bg-indigo-100 transition-colors shadow-sm"
                >
                  Take Tour
                </button>"""
page_content = page_content.replace(take_tour_btn, "")

# 7. Pass onTourClick to Sidebar
old_sidebar = """        <Sidebar
          activeTab={activeTab}
          onTabChange={setActiveTab}
          actionCount={actionCount}
          traderId={traderId}
          apiBase={API_BASE}
        />"""
new_sidebar = """        <Sidebar
          activeTab={activeTab}
          onTabChange={setActiveTab}
          actionCount={actionCount}
          traderId={traderId}
          apiBase={API_BASE}
          onTourClick={startTour}
        />"""
page_content = page_content.replace(old_sidebar, new_sidebar)

with open(page_js_path, 'w', encoding='utf-8') as f:
    f.write(page_content)


sidebar_js_path = 'd:/hackathob/kleos-4.0/frontend/src/app/components/Sidebar.js'
with open(sidebar_js_path, 'r', encoding='utf-8') as f:
    sidebar_content = f.read()

# 1. Add onTourClick to props
sidebar_content = sidebar_content.replace(
    'export default function Sidebar({ activeTab, onTabChange, actionCount, traderId, apiBase }) {',
    'export default function Sidebar({ activeTab, onTabChange, actionCount, traderId, apiBase, onTourClick }) {'
)

# 2. Add Take Tour button
take_tour_sidebar = """        {/* Take Tour */}
        <div className="px-4 pb-2 flex-none">
          <button 
            onClick={onTourClick} 
            className="flex items-center justify-center w-full px-3 py-2 bg-indigo-50 text-indigo-600 rounded-lg text-sm font-semibold hover:bg-indigo-100 transition-colors shadow-sm"
          >
            Take Tour
          </button>
        </div>

        {/* My Profile */}"""
sidebar_content = sidebar_content.replace('{/* My Profile */}', take_tour_sidebar)

with open(sidebar_js_path, 'w', encoding='utf-8') as f:
    f.write(sidebar_content)

print("UI patches applied.")
