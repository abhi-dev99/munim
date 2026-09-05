"""
Munim.ai — HSN GST Rate Corrector
Updates HSN codes in Supabase with correct GST rates based on official GST chapter mapping.
The official GST rate schedule groups items by chapter (first 2 digits of HSN code).
Run this ONCE after seeding HSN codes.
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

db = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Official GST rate schedule by HSN chapter (first 2 digits)
# Source: GST Rate Schedule under Notification No. 1/2017-Central Tax (Rate) as amended
# 0% = Essential goods, 5% = Basic necessities, 12% = Standard goods, 18% = Most goods, 28% = Luxury/sin goods

CHAPTER_RATES = {
    # Chapter 1-24: Food, Agriculture, Animals
    "01": 0.0,   "02": 0.0,   "03": 5.0,   "04": 5.0,   "05": 0.0,
    "06": 5.0,   "07": 0.0,   "08": 0.0,   "09": 0.0,   "10": 0.0,
    "11": 0.0,   "12": 0.0,   "13": 0.0,   "14": 0.0,   "15": 5.0,
    "16": 12.0,  "17": 5.0,   "18": 18.0,  "19": 18.0,  "20": 12.0,
    "21": 12.0,  "22": 18.0,  "23": 0.0,   "24": 28.0,

    # Chapter 25-27: Minerals, Fuels
    "25": 5.0,   "26": 0.0,   "27": 5.0,

    # Chapter 28-38: Chemicals
    "28": 18.0,  "29": 18.0,  "30": 12.0,  "31": 5.0,   "32": 18.0,
    "33": 18.0,  "34": 18.0,  "35": 18.0,  "36": 18.0,  "37": 18.0,
    "38": 18.0,

    # Chapter 39-40: Plastics, Rubber
    "39": 18.0,  "40": 18.0,

    # Chapter 41-43: Leather
    "41": 5.0,   "42": 18.0,  "43": 18.0,

    # Chapter 44-46: Wood, Paper
    "44": 12.0,  "45": 12.0,  "46": 12.0,

    # Chapter 47-49: Paper, Printing
    "47": 12.0,  "48": 18.0,  "49": 12.0,

    # Chapter 50-63: Textiles
    "50": 5.0,   "51": 5.0,   "52": 5.0,   "53": 5.0,   "54": 5.0,
    "55": 5.0,   "56": 12.0,  "57": 12.0,  "58": 12.0,  "59": 12.0,
    "60": 5.0,   "61": 5.0,   "62": 5.0,   "63": 5.0,

    # Chapter 64-67: Footwear, Headgear
    "64": 18.0,  "65": 18.0,  "66": 18.0,  "67": 18.0,

    # Chapter 68-70: Stone, Ceramics, Glass
    "68": 18.0,  "69": 18.0,  "70": 18.0,

    # Chapter 71: Gems, Jewellery
    "71": 3.0,

    # Chapter 72-83: Metals
    "72": 18.0,  "73": 18.0,  "74": 18.0,  "75": 18.0,  "76": 18.0,
    "77": 18.0,  "78": 18.0,  "79": 18.0,  "80": 18.0,  "81": 18.0,
    "82": 18.0,  "83": 18.0,

    # Chapter 84-85: Machinery, Electronics
    "84": 18.0,  "85": 18.0,

    # Chapter 86-89: Transport
    "86": 12.0,  "87": 28.0,  "88": 18.0,  "89": 5.0,

    # Chapter 90-92: Instruments, Clocks, Musical instruments
    "90": 18.0,  "91": 18.0,  "92": 28.0,

    # Chapter 93-96: Misc manufactured
    "93": 12.0,  "94": 18.0,  "95": 18.0,  "96": 18.0,

    # Chapter 97-99: Works of art, Special categories
    "97": 12.0,  "98": 0.0,   "99": 18.0,
}

# HSN-specific overrides (key items with non-chapter-default rates)
HSN_OVERRIDES = {
    # Motor vehicles — 28%
    "8703": 28.0, "8704": 28.0, "8711": 28.0,
    # Cement — 28%
    "2523": 28.0,
    # Air conditioners — 28%
    "8415": 28.0,
    # Refrigerators — 28%
    "8418": 28.0,
    # Washing machines — 28%
    "8450": 28.0,
    # Mobile phones — 12%
    "8517": 12.0,
    # Solar panels — 12%
    "8541": 12.0,
    # Medicines (pharma) — 5% or 12%
    "3004": 5.0,  "3003": 5.0,  "3002": 5.0,
    # Fertilizers — 5%
    "3101": 5.0,  "3102": 5.0,  "3103": 5.0,
    # Gold — 3%
    "7108": 3.0,  "7107": 3.0,
    # Petroleum (specific) — 0%
    "2709": 0.0,  "2710": 0.0,
    # Books — 0%
    "4901": 0.0,  "4902": 0.0,  "4903": 0.0,
    # Newspapers — 0%
    "4902": 0.0,
    # Tobacco — 28%
    "2401": 28.0, "2402": 28.0, "2403": 28.0,
    # Coal — 5%
    "2701": 5.0,  "2702": 5.0,
    # LPG/Natural gas — 5%
    "2711": 5.0,
    # Railway locomotives — 5%
    "8601": 5.0,  "8602": 5.0,  "8603": 5.0,
    # Iron ore — 5%
    "2601": 5.0,
    # Cotton yarn — 5%
    "5205": 5.0,  "5206": 5.0,
    # Services (SAC codes starting with 99)
    "9954": 18.0,  # Construction
    "9963": 18.0,  # Accommodation (but blocked under 17(5))
    "9964": 18.0,  # Transport
    "9965": 18.0,  # Support services
    "9971": 18.0,  # Financial/Insurance
    "9972": 18.0,  # Real estate
    "9973": 18.0,  # Leasing
    "9983": 18.0,  # Professional
    "9984": 18.0,  # Telecom
    "9985": 18.0,  # Support services
    "9986": 0.0,   # Agri support (exempt)
    "9987": 18.0,  # Maintenance
    "9988": 5.0,   # Job work (manufacturing) — 5% or 12%
    "9991": 0.0,   # Government services (exempt)
    "9992": 0.0,   # Education (exempt)
    "9993": 5.0,   # Health
    "9995": 18.0,  # Entertainment
    "9996": 28.0,  # Club membership (blocked + 28%)
    "9997": 18.0,  # Other services
}


def get_rate_for_hsn(hsn_code: str) -> float:
    """Get the correct GST rate for an HSN code."""
    hsn = hsn_code.strip()
    
    # Check 4-digit overrides first
    if len(hsn) >= 4:
        override = HSN_OVERRIDES.get(hsn[:4])
        if override is not None:
            return override
    
    # Then 2-digit chapter rate
    chapter = hsn[:2]
    return CHAPTER_RATES.get(chapter, 18.0)


def update_hsn_rates():
    """Fetch all HSN codes and update their GST rates in batches."""
    print("Fetching HSN codes from Supabase...")
    
    # Fetch all in batches of 1000
    page_size = 1000
    offset = 0
    total_updated = 0
    
    while True:
        response = db.table("hsn_codes").select("id, hsn_code, gst_rate").range(offset, offset + page_size - 1).execute()
        records = response.data or []
        
        if not records:
            break
        
        print(f"Processing {len(records)} records (offset {offset})...")
        
        # Group by new rate to minimize DB calls
        updates = {}
        for rec in records:
            new_rate = get_rate_for_hsn(rec["hsn_code"])
            if abs((rec.get("gst_rate") or 18.0) - new_rate) > 0.01:
                updates[rec["id"]] = new_rate
        
        # Update changed records
        for record_id, new_rate in updates.items():
            try:
                db.table("hsn_codes").update({"gst_rate": new_rate}).eq("id", record_id).execute()
                total_updated += 1
            except Exception as e:
                print(f"  Failed to update {record_id}: {e}")
        
        print(f"  Updated {len(updates)} rates in this batch")
        
        offset += page_size
        if len(records) < page_size:
            break
    
    print(f"\n✅ Done! Updated {total_updated} HSN codes with correct GST rates.")
    
    # Verify rate distribution
    print("\nRate distribution after update:")
    for rate in [0.0, 3.0, 5.0, 12.0, 18.0, 28.0]:
        count_resp = db.table("hsn_codes").select("id", count="exact").eq("gst_rate", rate).execute()
        print(f"  {rate}%: {count_resp.count} codes")


if __name__ == "__main__":
    update_hsn_rates()
