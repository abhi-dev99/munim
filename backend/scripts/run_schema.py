"""
Run the Munim.ai schema against Supabase.
Uses the Supabase Management API to execute raw SQL.
"""
import httpx
import os
import sys

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
if not SUPABASE_URL or not SERVICE_ROLE_KEY:
    print("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (see backend/.env).")
    sys.exit(1)
PROJECT_REF = SUPABASE_URL.split("//")[-1].split(".")[0]

# Read schema
with open("backend/schema.sql", "r") as f:
    schema_sql = f.read()

# Split into individual statements (rough split on semicolons)
# We'll send as one block via the pg endpoint
headers = {
    "apikey": SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
}

# Use the Supabase SQL execution endpoint
print("Running schema against Supabase...")
resp = httpx.post(
    f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
    headers=headers,
    json={"query": schema_sql},
    timeout=30,
)
print(f"Status: {resp.status_code}")
print(resp.text[:500])
