import httpx
import asyncio

import sys
import os

async def test_email_webhook(file_path: str = None):
    print("Testing Email Agent Webhook with Resend Format...")
    
    url = "http://localhost:8000/api/v1/webhook/email"
    
    import base64
    
    # Read the real file if provided, otherwise fallback to dummy
    if file_path and os.path.exists(file_path):
        print(f"Reading file: {file_path}")
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        filename = os.path.basename(file_path)
        mime_type = "application/pdf" if filename.endswith(".pdf") else "image/png"
    else:
        print("No real file provided, using dummy PDF...")
        dummy_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        file_bytes = dummy_pdf
        filename = "invoice_12345.pdf"
        mime_type = "application/pdf"

    file_b64 = base64.b64encode(file_bytes).decode('utf-8')
    
    # Simulate a CloudMailin JSON Normalized payload
    data = {
        "headers": {
            "to": "c3ae630f3938b8b98d8b@cloudmailin.net",
            "from": "distributor@example.com",
            "subject": "Invoice 12345 for Aditya Test"
        },
        "envelope": {
            "to": "c3ae630f3938b8b98d8b@cloudmailin.net",
            "from": "distributor@example.com"
        },
        "attachments": [
            {
                "file_name": filename,
                "content_type": mime_type,
                "content": file_b64
            }
        ]
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, timeout=30.0)
            print(f"Response Status: {response.status_code}")
            print(f"Response Text: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(test_email_webhook(file_path))
