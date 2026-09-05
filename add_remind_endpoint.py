import os
filepath = 'backend/app/api/communications.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_endpoint = """
@router.post("/remind-gstin/{trader_id}")
async def remind_gstin_whatsapp(trader_id: str, lang: str = "en", current_trader_id: str = Depends(get_current_trader_id)):
    db = get_supabase()
    res = db.table("traders").select("*").eq("id", trader_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Client not found")
        
    client = res.data[0]
    phone = client.get("whatsapp_number")
    if not phone:
        raise HTTPException(status_code=400, detail="Client does not have a registered WhatsApp number")
        
    # Send WhatsApp reminder
    msg = f"Hello {client.get('name', 'there')}!\\n\\nThis is a gentle reminder from your Chartered Accountant to please update your GSTIN in the Munim.ai portal so we can automate your compliance checks and ITC reconciliation.\\n\\nPlease reply to this message with your 15-digit GSTIN."
    try:
        await send_whatsapp_message(phone, msg)
        return {"status": "success", "message": "GSTIN reminder sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
"""

if '@router.post("/remind-gstin/{trader_id}")' not in content:
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write("\n" + new_endpoint)
    print("Added remind-gstin endpoint")
else:
    print("Endpoint already exists")
