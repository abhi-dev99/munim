"""Check and register user's phone number as a trader in Supabase."""
import os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')
from supabase import create_client

db = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])

phone = "919822062252"

# Check existing traders
traders = db.table('traders').select('id, name, whatsapp_number, gstin').execute()
print("Existing traders:")
for t in traders.data:
    print(f"  {t['name']} | WA: {t['whatsapp_number']} | GSTIN: {t['gstin']}")

# Check if already registered
existing = [t for t in traders.data if t.get('whatsapp_number') == phone]
if existing:
    print(f"\nNumber {phone} already registered as: {existing[0]['name']}")
    print(f"Trader ID: {existing[0]['id']}")
else:
    print(f"\nNumber {phone} NOT yet a trader — adding to existing trader Raju...")
    # Update the existing demo trader with this phone number so webhook can find them
    raju = next((t for t in traders.data if 'raju' in t['name'].lower() or t['whatsapp_number'] is None), traders.data[0] if traders.data else None)
    if raju:
        result = db.table('traders').update({'whatsapp_number': phone}).eq('id', raju['id']).execute()
        print(f"Updated trader '{raju['name']}' (ID: {raju['id']}) with WhatsApp number: {phone}")
    else:
        print("No traders found to update!")
