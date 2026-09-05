import asyncio
from app.services.supabase_client import get_supabase
async def test():
    db = get_supabase()
    db.table('munim_reports').update({
        'total_invoices_processed': 27,
        'total_issues_count': 5
    }).eq('trader_id', '6d123264-9325-4a37-b769-274834a04085').execute()
    print("updated")
asyncio.run(test())
