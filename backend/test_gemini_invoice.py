import asyncio
import httpx
import sys
sys.path.insert(0, '.')

async def test():
    from app.config import Settings
    settings = Settings()
    from app.services.gemini import client as gemini_client
    from google.genai import types

    from app.services.supabase_client import get_supabase
    db = get_supabase()
    res = db.table("invoices").select("image_url").eq("trader_id", "6d123264-9325-4a37-b769-274834a04085").order("created_at", desc=True).limit(3).execute()
    
    for row in (res.data or []):
        img_url = row.get("image_url")
        if not img_url:
            continue
        print(f"\nTesting: {img_url[:80]}...")
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(img_url, timeout=30)
                image_bytes = resp.content
                content_type = resp.headers.get("content-type", "image/jpeg")
                print(f"  Downloaded {len(image_bytes)} bytes, content-type={content_type}")
                
                # Force jpeg mime type
                mime = "image/jpeg" if "jpeg" in content_type or "jpg" in content_type else content_type
                
                gemini_response = gemini_client.models.generate_content(
                    model=settings.gemini_model,
                    contents=[
                        types.Part.from_bytes(data=image_bytes, mime_type=mime),
                        types.Part.from_text(text="What is the supplier name in this invoice? Reply in one line."),
                    ],
                )
                print(f"  Gemini: {gemini_response.text[:200]}")
            except Exception as e:
                print(f"  ERROR: {e}")

asyncio.run(test())
