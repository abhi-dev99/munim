import os
import re

filepath = 'd:/hackathob/kleos-4.0/frontend/src/app/dashboard/page.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the supplier step
old_supplier = """element: () => { setActiveTab("suppliers"); return '#supplier-table-row-0'; },"""
new_supplier = """element: '#sidebar-nav-suppliers',"""
content = content.replace(old_supplier, new_supplier)

old_supplier_popover = """popover: { title: 'Supplier Trust', description: 'Click any supplier row to view a detailed breakdown of all their invoices and pinpoint exactly which ones are causing blocked ITC.', side: "bottom", align: 'start' }"""
new_supplier_popover = """popover: { title: 'Supplier Trust', description: 'Navigate to the Supplier Trust tab to view a detailed breakdown of all supplier invoices and pinpoint exactly which ones are causing blocked ITC.', side: "right", align: 'start' }"""
content = content.replace(old_supplier_popover, new_supplier_popover)

# Replace the actions step
old_actions = """element: () => { setActiveTab("actions"); return '#action-queue-card-0'; },"""
new_actions = """element: '#sidebar-nav-actions',"""
content = content.replace(old_actions, new_actions)

old_actions_popover = """popover: { title: 'Action Queue', description: 'This is your triage center. Any discrepancies, mismatching invoices, or blocked ITC that require your immediate attention will be queued here.', side: "bottom", align: 'start' }"""
new_actions_popover = """popover: { title: 'Action Queue', description: 'This is your triage center. Any discrepancies, mismatching invoices, or blocked ITC that require your immediate attention will be queued here.', side: "right", align: 'start' }"""
content = content.replace(old_actions_popover, new_actions_popover)

# Also fix the right panel widget step!
old_right_panel = """popover: { title: 'Right Panel Widgets', description: 'All the widgets on the right panel of your dashboard can also be dragged and dropped into any order you prefer.', side: "left", align: 'start' }"""
new_right_panel = """element: '#right-panel',\n            popover: { title: 'Right Panel Widgets', description: 'All the widgets on the right panel of your dashboard can also be dragged and dropped into any order you prefer.', side: "left", align: 'start' }"""
content = content.replace(old_right_panel, new_right_panel)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Tour steps updated successfully.")
