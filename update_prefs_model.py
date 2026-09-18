import os
filepath = 'backend/app/api/dashboard.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update PreferencesModel
old_model = """class PreferencesModel(BaseModel):
    dashboard: list[str]
    sidebar: list[str]"""
new_model = """class PreferencesModel(BaseModel):
    dashboard: list[str]
    sidebar: list[str]
    money_meter_top: list[str] | None = None
    money_meter_bottom: list[str] | None = None"""

if old_model in content:
    content = content.replace(old_model, new_model)

# 2. Update default preferences in get_dashboard_preferences
old_default = """return {
            "dashboard": ["supplier_risk", "filing_readiness", "eway_bills", "quick_links"],
            "sidebar": ["money-meter", "suppliers", "actions", "reports"]
        }"""
new_default = """return {
            "dashboard": ["supplier_risk", "filing_readiness", "eway_bills", "quick_links"],
            "sidebar": ["money-meter", "suppliers", "actions", "reports"],
            "money_meter_top": ["confirmed", "at_risk", "recovery"],
            "money_meter_bottom": ["invoices", "suppliers", "issues"]
        }"""
if old_default in content:
    content = content.replace(old_default, new_default)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated PreferencesModel in dashboard.py")
