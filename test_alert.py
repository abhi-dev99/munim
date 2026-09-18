import asyncio
import os
import sys

# Add backend to python path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from app.api.communications import send_test_alert

async def main():
    try:
        await send_test_alert("demo", "en")
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
