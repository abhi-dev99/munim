import asyncio
from app.services.supabase_client import get_supabase

async def transfer_phone():
    db = get_supabase()
    trader_id = "205860dc-5fb1-4039-be0c-e5bb705975d2"
    update_resp = db.table("traders").update({"whatsapp_number": "9136875481"}).eq("id", trader_id).execute()
    print(f"Updated trader phone to 9136875481: {update_resp.data}")

if __name__ == "__main__":
    asyncio.run(transfer_phone())
