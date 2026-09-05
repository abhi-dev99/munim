import os

filepath = 'frontend/src/app/components/SupplierHealth.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update the loading wireframe
old_loader = """  if (loading) return (
    <div className="space-y-3">
      {[1,2,3].map(i => <div key={i} className="h-14 bg-gray-100 rounded-xl animate-pulse" />)}
    </div>
  );"""

new_loader = """  if (loading) return (
    <div className="flex flex-col h-[calc(100vh-80px)] w-full">
      <div className="grid grid-cols-4 gap-3 mb-4">
        {[1,2,3,4].map(i => <div key={i} className="h-20 bg-gray-100 rounded-xl animate-pulse" />)}
      </div>
      <div className="h-12 bg-gray-100 rounded-xl animate-pulse mb-6" />
      <div className="flex-1 space-y-3">
        {[1,2,3,4,5].map(i => <div key={i} className="h-14 bg-gray-50 rounded-lg animate-pulse" />)}
      </div>
    </div>
  );"""

if old_loader in content:
    content = content.replace(old_loader, new_loader)
else:
    print("WARNING: Loader not found")

# 2. Add drag-and-drop state & sticky headers
old_return_start = """  return (
    <>
      <div className="space-y-4 w-full">
        {/* Summary stat cards */}
        <div className="grid grid-cols-4 gap-3">
          {["ALL", "GOOD", "RISK", "CRITICAL"].map((f) => ("""

new_return_start = """  const dragItem = React.useRef(null);
  const dragOverItem = React.useRef(null);
  const [cardOrder, setCardOrder] = useState(["ALL", "GOOD", "RISK", "CRITICAL"]);

  const handleSort = () => {
    if (dragItem.current === null || dragOverItem.current === null) return;
    let _order = [...cardOrder];
    const draggedItemContent = _order.splice(dragItem.current, 1)[0];
    _order.splice(dragOverItem.current, 0, draggedItemContent);
    dragItem.current = null;
    dragOverItem.current = null;
    setCardOrder(_order);
  };

  return (
    <div className="flex flex-col h-full w-full">
      <div className="sticky top-0 z-10 bg-[#f8fafc] pt-2 pb-4 space-y-4">
        {/* Summary stat cards */}
        <div className="grid grid-cols-4 gap-3">
          {cardOrder.map((f, idx) => ("""

if old_return_start in content:
    content = content.replace(old_return_start, new_return_start)
    
    # We also need to add React import if it's missing, but it's likely we can just use `useRef` directly if imported, else `React.useRef`. Let's import useRef.
    if 'useRef' not in content:
        content = content.replace('import { useState, useEffect }', 'import React, { useState, useEffect, useRef }')
else:
    print("WARNING: Return start not found")

# 3. Add draggable props to the cards
old_card_button = """            <button
              key={f}
              onClick={() => setFilterStatus(f)}
              className={`text-left bg-white rounded-xl border p-3 transition-all hover:shadow-sm ${"""

new_card_button = """            <button
              key={f}
              draggable
              onDragStart={() => { dragItem.current = idx; }}
              onDragEnter={(e) => { dragOverItem.current = idx; e.preventDefault(); }}
              onDragOver={(e) => e.preventDefault()}
              onDragEnd={handleSort}
              onClick={() => setFilterStatus(f)}
              className={`text-left bg-white rounded-xl border p-3 transition-all hover:shadow-sm cursor-grab active:cursor-grabbing ${"""

if old_card_button in content:
    content = content.replace(old_card_button, new_card_button)
else:
    print("WARNING: Card button not found")

# 4. Make the table scrollable
old_table_header = """        {/* Table Header */}
        <div className="grid grid-cols-[3fr_2fr_2fr_2fr_2fr_1fr_1fr] items-center px-4 py-3 bg-gray-50 border-y border-gray-200 text-[10px] font-bold text-gray-500 uppercase tracking-widest">"""

new_table_header = """      </div> {/* End sticky section */}
      
      <div className="flex-1 overflow-y-auto pb-8">
        {/* Table Header */}
        <div className="grid grid-cols-[3fr_2fr_2fr_2fr_2fr_1fr_1fr] items-center px-4 py-3 bg-gray-50 border-y border-gray-200 text-[10px] font-bold text-gray-500 uppercase tracking-widest sticky top-0 z-0">"""

if old_table_header in content:
    content = content.replace(old_table_header, new_table_header)
else:
    print("WARNING: Table header not found")

# Fix the closing tags at the very bottom
content = content.replace('      </div>\n      {activeSupplier', '      </div>\n      </div>\n      {activeSupplier')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("SupplierHealth.js refactored")
