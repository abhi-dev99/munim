import os
import re

def secure_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add imports
    if 'from app.api.deps import' not in content:
        content = content.replace('from fastapi import APIRouter', 'from fastapi import APIRouter, Depends\nfrom app.api.deps import verify_trader_access, get_current_trader_id')

    # Replace specific endpoints
    content = re.sub(r'async def (.*?)\(trader_id: str\):', r'async def \1(trader_id: str = Depends(verify_trader_access)):', content)
    content = re.sub(r'async def (.*?)\(trader_id: str, (.*?)\):', r'async def \1(trader_id: str = Depends(verify_trader_access), \2):', content)
    
    # list_traders special case
    content = content.replace('async def list_traders():', 'async def list_traders(current_trader_id: str = Depends(get_current_trader_id)):')
    content = content.replace('response = db.table("traders").select("id, name, business_name, gstin, whatsapp_number").execute()', 'response = db.table("traders").select("id, name, business_name, gstin, whatsapp_number").eq("id", current_trader_id).execute()')
    
    # specific to gstr2b
    content = content.replace('async def upload_gstr2b_json(payload: GSTR2BBulkUpload):', 'async def upload_gstr2b_json(payload: GSTR2BBulkUpload, current_trader_id: str = Depends(get_current_trader_id)):\n    if payload.trader_id != current_trader_id:\n        raise HTTPException(status_code=403, detail="Not authorized")')

    # specific to communications
    content = content.replace('async def email_vendor_warning(invoice_id: str):', 'async def email_vendor_warning(invoice_id: str, current_trader_id: str = Depends(get_current_trader_id)):')
    content = content.replace('async def whatsapp_vendor_warning(invoice_id: str, lang: str = "en"):', 'async def whatsapp_vendor_warning(invoice_id: str, lang: str = "en", current_trader_id: str = Depends(get_current_trader_id)):')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Secured {filepath}')

for f in ['backend/app/api/dashboard.py', 'backend/app/api/gstr2b.py', 'backend/app/api/reports.py', 'backend/app/api/communications.py']:
    secure_file(f)
