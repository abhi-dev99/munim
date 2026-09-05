"""
Run the Munim.ai schema against Supabase.
Uses the Supabase Management API to execute raw SQL.
"""
import httpx
import sys

SUPABASE_URL = "https://agxfxqwfnazwrtnfamiz.supabase.co"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFneGZ4cXdmbmF6d3J0bmZhbWl6Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTcwMTE2MywiZXhwIjoyMDk3Mjc3MTYzfQ.g0vknyydAa9hmjaO3a5iJvG6iAv_8uU1iJWRBAJv0zk"
PROJECT_REF = "agxfxqwfnazwrtnfamiz"

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
