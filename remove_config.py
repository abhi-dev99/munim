import os
filepath = 'frontend/src/app/dashboard/profile/page.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# I will find the ConfigDashboard component block and remove it entirely.
# I will also remove the <ConfigDashboard traderId={...} /> invocation.

start_str = "function ConfigDashboard({ traderId }) {"
end_str = "</section>\n  );\n}"

start_idx = content.find(start_str)
end_idx = content.find(end_str, start_idx) + len(end_str)

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + content[end_idx:]

content = content.replace('<ConfigDashboard traderId={traders.length > 0 ? traders[0].ca_whatsapp_number || traders[0].whatsapp_number || profile.phone : profile.phone} />', '')

# Also remove Eye, EyeOff, ArrowUp, ArrowDown from imports to clean up
content = content.replace('  ArrowUp,\n  ArrowDown,\n  Eye,\n  EyeOff,\n', '')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Removed ConfigDashboard from profile/page.js")
