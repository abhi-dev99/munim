import psycopg2
import sys
import os

# Connect string using the password you provided earlier
DB_URI = "postgresql://postgres.agxfxqwfnazwrtnfamiz:nW7C8WPKyYJD4bM7@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres"

print("Connecting to Supabase Postgres...")
try:
    conn = psycopg2.connect(DB_URI)
    conn.autocommit = True
    cursor = conn.cursor()
    print("Connected successfully!")
    
    # Read the schema file
    with open("backend/schema.sql", "r", encoding="utf-8") as f:
        schema_sql = f.read()
        
    print("Executing schema.sql...")
    cursor.execute(schema_sql)
    print("Schema applied successfully! All tables created.")
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
