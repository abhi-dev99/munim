import os
filepath = 'frontend/src/app/components/Sidebar.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

sidebar_logic = """
  const [prefs, setPrefs] = useState(null);

  useEffect(() => {
    if (!traderId || !apiBase) return;
    authFetch(`${apiBase}/api/v1/dashboard/preferences/${traderId}`)
      .then(r => r.json())
      .then(d => {
        if (d.sidebar) setPrefs(d.sidebar);
      }).catch(console.error);
  }, [traderId, apiBase]);

  // Default nav items are defined as navItems above. We filter and sort based on prefs.
  const visibleNavItems = prefs 
    ? prefs.map(id => navItems.find(i => i.id === id)).filter(Boolean)
    : navItems;
"""

# add logic inside Sidebar component
if 'const [prefs, setPrefs] = useState(null);' not in content:
    content = content.replace('const [testAlertError, setTestAlertError] = useState(null);', 'const [testAlertError, setTestAlertError] = useState(null);\n' + sidebar_logic)

# Replace the map of navItems
content = content.replace('{navItems.map((item) => {', '{visibleNavItems.map((item) => {')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched Sidebar.js")
