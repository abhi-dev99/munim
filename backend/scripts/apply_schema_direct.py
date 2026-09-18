import psycopg2
import sys
import os

DB_URI = os.environ.get("SUPABASE_DB_URI")
if not DB_URI:
    print("Set SUPABASE_DB_URI (Supabase → Project Settings → Database → Connection string).")
    sys.exit(1)

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
