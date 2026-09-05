import asyncio
from app.services.supabase_client import get_supabase

async def check_invoices():
    db = get_supabase()
    response = db.table("invoices").select(
        "id, supplier_name, itc_status, itc_amount_eligible, itc_amount_blocked"
    ).execute()
    
    print("ALL INVOICES:")
    for inv in response.data:
        print(f"{inv['supplier_name']} | {inv['itc_status']} | Elig: {inv['itc_amount_eligible']} | Blocked: {inv['itc_amount_blocked']}")

if __name__ == "__main__":
    asyncio.run(check_invoices())
