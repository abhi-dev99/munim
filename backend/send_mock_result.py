import asyncio
import sys
sys.path.insert(0, '.')

async def send_mock_invoice_result():
    from app.services.whatsapp import send_text_message

    phone = "919822062252"

    message = """✅ Invoice process ho gayi!

*Suryakanta Optics* — Bill #301
Taxable: ₹1,050 | Total: ₹1,239

💰 *ITC Confirmed: ₹189*
GSTR-2B match ✅ | GSTIN verified ✅ | No fraud detected 🟢

Dashboard pe baaki details dekh sakte ho."""

    result = await send_text_message(phone, message)
    print(f"Message sent: {result}")

asyncio.run(send_mock_invoice_result())
