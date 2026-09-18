import os
filepath = 'frontend/src/app/dashboard/profile/page.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add MessageCircle to lucide-react imports if not there
if 'MessageCircle' not in content:
    content = content.replace('AlertTriangle,\n} from "lucide-react";', 'AlertTriangle,\n  MessageCircle,\n} from "lucide-react";')
elif 'MessageCircle' not in content and 'import { ' in content:
    content = content.replace('import {\n', 'import {\n  MessageCircle,\n')

# 2. Add handleSendReminder function inside ProfilePage
func_logic = """
  const handleSendReminder = async (traderId) => {
    try {
      const res = await authFetch(`${API_BASE}/api/v1/communications/remind-gstin/${traderId}`, { method: "POST" });
      if (res.ok) alert("WhatsApp reminder sent to client!");
      else alert("Failed to send reminder. Check client's phone number.");
    } catch (e) {
      alert("Failed to send reminder.");
    }
  };
"""

if 'const handleSendReminder = async' not in content:
    # Find a good place to insert it, e.g., after const [traders, setTraders]
    content = content.replace('const [traders, setTraders] = useState([]);', 'const [traders, setTraders] = useState([]);\n' + func_logic)

# 3. Add the button in the table row
# Search for the GSTIN table cell
cell_old = '<td className="px-4 py-3 font-mono text-xs text-gray-500 bg-gray-50">{t.gstin || "Not set"}</td>'
cell_new = """<td className="px-4 py-3 font-mono text-xs text-gray-500 bg-gray-50">
                          <div className="flex items-center justify-between">
                            <span>{t.gstin || "Not set"}</span>
                            {!t.gstin && (
                              <button onClick={() => handleSendReminder(t.id)} className="ml-2 p-1 text-green-600 hover:bg-green-100 rounded" title="Send WhatsApp Reminder">
                                <MessageCircle size={14} />
                              </button>
                            )}
                          </div>
                        </td>"""

if cell_old in content:
    content = content.replace(cell_old, cell_new)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Added reminder UI to profile/page.js")
