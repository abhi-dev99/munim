import asyncio
from app.services.supabase_client import get_supabase
async def test():
    db = get_supabase()
    r = db.table('munim_reports').select('*').execute()
    print(r.data)
asyncio.run(test())
