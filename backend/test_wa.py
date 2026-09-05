import asyncio
from app.config import get_settings
from app.services import whatsapp

async def main():
    settings = get_settings()
    # The phone number in the screenshot is 919822062252
    phone = "919822062252"
    msg = "Test message from Munim.ai"
    print(f"Sending to {phone}...")
    success = await whatsapp.send_text_message(phone, msg)
    print(f"Success: {success}")

if __name__ == "__main__":
    asyncio.run(main())
