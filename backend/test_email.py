import os
import resend
from app.config import get_settings

settings = get_settings()
resend.api_key = settings.resend_api_key

html_content = """
<div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h2>Munim AI Test Delivery</h2>
    <p>Hi Aditya,</p>
    <p>This is a test to see if Resend will deliver this HTML block.</p>
    <p>If you see this, then Resend is not blocking HTML entirely.</p>
</div>
"""

try:
    res = resend.Emails.send({
        "from": "onboarding@resend.dev",
        "to": ["shahaditya0710@gmail.com"],
        "subject": "Delivery Test",
        "html": html_content
    })
    print("SUCCESS:", res)
except Exception as e:
    print("ERROR:", e)
