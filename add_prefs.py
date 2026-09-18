import os
import json

filepath = 'backend/app/api/dashboard.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

endpoints_code = """
import json
import os
from pydantic import BaseModel

class PreferencesModel(BaseModel):
    dashboard: list[str]
    sidebar: list[str]

PREF_FILE = "preferences.json"

def _load_prefs():
    if os.path.exists(PREF_FILE):
        with open(PREF_FILE, "r") as f:
            return json.load(f)
    return {}

def _save_prefs(prefs):
    with open(PREF_FILE, "w") as f:
        json.dump(prefs, f)

@router.get("/preferences/{trader_id}")
async def get_preferences(trader_id: str = Depends(verify_trader_access)):
    prefs = _load_prefs()
    if trader_id in prefs:
        return prefs[trader_id]
    return {
        "dashboard": ["quick_links", "supplier_risk", "filing_readiness", "eway_bills"],
        "sidebar": ["dashboard", "money_meter", "reconcile_2b", "suppliers", "reports", "profile"]
    }

@router.post("/preferences/{trader_id}")
async def save_preferences(payload: PreferencesModel, trader_id: str = Depends(verify_trader_access)):
    prefs = _load_prefs()
    prefs[trader_id] = {
        "dashboard": payload.dashboard,
        "sidebar": payload.sidebar
    }
    _save_prefs(prefs)
    return {"message": "Preferences saved successfully"}

"""

# Append to the end of dashboard.py
if 'class PreferencesModel(BaseModel):' not in content:
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write("\n" + endpoints_code)
    print("Added preferences endpoints")
else:
    print("Endpoints already exist")
