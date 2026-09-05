import os
filepath = 'frontend/src/app/dashboard/profile/page.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the config grid
search_str = """
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
"""

replace_str = """
        <div className="grid grid-cols-2 gap-8">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-4">Left Sidebar</h3>
            {renderList("sidebar", allSidebarWidgets)}
          </div>
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-4">Dashboard Right Rail</h3>
            {renderList("dashboard", allDashboardWidgets)}
          </div>
        </div>
"""

if search_str.strip() in content:
    content = content.replace(search_str.strip(), replace_str.strip())
elif "Dashboard Right Rail" in content and "Left Sidebar" in content:
    content = content.replace(
        '<div>\n            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-4">Dashboard Right Rail</h3>\n            {renderList("dashboard", allDashboardWidgets)}\n          </div>', 
        '<!-- TEMP -->'
    )
    content = content.replace(
        '<div>\n            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-4">Left Sidebar</h3>\n            {renderList("sidebar", allSidebarWidgets)}\n          </div>',
        '<div>\n            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-4">Dashboard Right Rail</h3>\n            {renderList("dashboard", allDashboardWidgets)}\n          </div>'
    )
    content = content.replace(
        '<!-- TEMP -->',
        '<div>\n            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-4">Left Sidebar</h3>\n            {renderList("sidebar", allSidebarWidgets)}\n          </div>'
    )

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Swapped config columns.")
