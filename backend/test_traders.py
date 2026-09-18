import asyncio
from app.services.supabase_client import get_supabase

async def check_traders():
    db = get_supabase()
    response = db.table("traders").select("id, name, business_name, whatsapp_number, ca_whatsapp_number").execute()
    print("ALL TRADERS:")
    for t in response.data:
        print(f"ID: {t['id']} | Name: {t.get('name')} | Phone: {t.get('whatsapp_number')} | CA Phone: {t.get('ca_whatsapp_number')}")

if __name__ == "__main__":
    asyncio.run(check_traders())
