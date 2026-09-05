import os

filepath = 'frontend/src/app/components/Sidebar.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add recharts import
if 'import { BarChart, Bar, ResponsiveContainer, Tooltip, Cell } from "recharts";' not in content:
    content = content.replace('import { useLanguage } from "../context/LanguageContext";', 'import { useLanguage } from "../context/LanguageContext";\nimport { BarChart, Bar, ResponsiveContainer, Tooltip, Cell } from "recharts";')

# 2. Replace MiniSparkline
old_mini = """function MiniSparkline({ data = [] }) {
  if (!data.length) return <div className="h-12 flex items-end gap-0.5 px-1">{[...Array(6)].map((_, i) => <div key={i} className="flex-1 bg-gray-200 rounded-sm animate-pulse" style={{ height: `${30 + Math.random() * 20}%` }} />)}</div>;
  const max = Math.max(...data.map(d => d.itc_claimed || 0), 1);
  return (
    <div className="h-12 flex items-end gap-0.5 px-1">
      {data.slice(-6).map((d, i) => (
        <div key={i} className="flex-1 flex flex-col items-center gap-0.5">
          <div
            className="w-full rounded-sm bg-[#10b981] opacity-80"
            style={{ height: `${Math.max(4, ((d.itc_claimed || 0) / max) * 44)}px` }}
            title={`${d.label}: ₹${(d.itc_claimed || 0).toLocaleString("en-IN")}`}
          />
        </div>
      ))}
    </div>
  );
}"""

new_mini = """function MiniSparkline({ data = [] }) {
  if (!data.length) return <div className="h-12 flex items-end gap-0.5 px-1">{[...Array(6)].map((_, i) => <div key={i} className="flex-1 bg-gray-200 rounded-sm animate-pulse" style={{ height: `${30 + Math.random() * 20}%` }} />)}</div>;
  
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white border border-gray-200 rounded shadow-sm px-2 py-1 text-xs">
          <p className="font-semibold text-gray-800">{payload[0].payload.label}</p>
          <p className="text-emerald-600 font-bold">₹{payload[0].value.toLocaleString("en-IN")}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="h-14 px-1 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data.slice(-6)}>
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'transparent' }} />
          <Bar dataKey="itc_claimed" radius={[2, 2, 2, 2]}>
            {data.slice(-6).map((entry, index) => (
              <Cell key={`cell-${index}`} fill="#10b981" fillOpacity={0.8} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}"""

if old_mini in content:
    content = content.replace(old_mini, new_mini)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched Sidebar.js with recharts")
