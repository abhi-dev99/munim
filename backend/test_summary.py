import asyncio
import httpx

async def test_summary():
    async with httpx.AsyncClient() as client:
        # Assuming we need to get trader_id from DB
        from app.services.supabase_client import get_supabase
        db = get_supabase()
        res = db.table("traders").select("id").eq("whatsapp_number", "919822062252").execute()
        trader_id = res.data[0]['id']
        
        url = f"http://localhost:8000/api/v1/dashboard/summary/{trader_id}"
        # Wait, dashboard APIs are secured by JWT!
        from app.config import get_settings
        import jwt
        from datetime import datetime, timedelta
        settings = get_settings()
        token = jwt.encode({"sub": trader_id, "exp": datetime.utcnow() + timedelta(days=1)}, settings.jwt_secret, algorithm="HS256")
        
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get(url, headers=headers)
        print("SUMMARY STATUS:", resp.status_code)
        print("SUMMARY JSON:", resp.json())
        
        act_url = f"http://localhost:8000/api/v1/dashboard/actions/{trader_id}"
        act_resp = await client.get(act_url, headers=headers)
        print("ACTIONS JSON:", act_resp.json())

if __name__ == "__main__":
    asyncio.run(test_summary())
