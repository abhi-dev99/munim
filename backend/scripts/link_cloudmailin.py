import asyncio
from app.services.supabase_client import get_supabase

async def update():
    supabase = get_supabase()
    # Let's get the first trader
    response = supabase.table("traders").select("*").limit(1).execute()
    traders = response.data
    if traders:
        trader_id = traders[0]["id"]
        whatsapp_number = traders[0]["whatsapp_number"]
        # Update inbound_email and ca_whatsapp_number
        # Using the same whatsapp number for CA for testing purposes
        update_data = {
            "inbound_email": "c3ae630f3938b8b98d8b@cloudmailin.net",
            "ca_whatsapp_number": whatsapp_number
        }
        res = supabase.table("traders").update(update_data).eq("id", trader_id).execute()
        print(f"Updated trader {trader_id}: {res.data}")
    else:
        print("No traders found!")

if __name__ == "__main__":
    asyncio.run(update())
