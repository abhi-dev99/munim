import os

# 1. Update SupplierHealth.js
filepath = 'frontend/src/app/components/SupplierHealth.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the row rendering
old_row = """              return (
                <div key={s.id} className="grid grid-cols-[3fr_2fr_2fr_2fr_2fr_1fr_1fr] items-center px-4 py-3 border-b border-gray-100 hover:bg-gray-50 transition-colors">"""
new_row = """              return (
                <div key={s.id} id={`supplier-table-row-${idx}`} className="grid grid-cols-[3fr_2fr_2fr_2fr_2fr_1fr_1fr] items-center px-4 py-3 border-b border-gray-100 hover:bg-gray-50 transition-colors">"""

if old_row in content:
    content = content.replace(old_row, new_row)
else:
    print("WARNING: Could not find SupplierHealth.js row")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

# 2. Update ActionQueue.js
filepath = 'frontend/src/app/components/ActionQueue.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_card = """            {displayed.map((action, idx) => {
              const isOpen = expanded === action.id;
              return (
                <motion.div layout key={action.id} className="bg-white">"""
new_card = """            {displayed.map((action, idx) => {
              const isOpen = expanded === action.id;
              return (
                <motion.div layout key={action.id} id={`action-queue-card-${idx}`} className="bg-white">"""

if old_card in content:
    content = content.replace(old_card, new_card)
else:
    print("WARNING: Could not find ActionQueue.js card")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Injected IDs into SupplierHealth and ActionQueue")
