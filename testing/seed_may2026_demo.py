"""
Munim.ai — Demo Seeder: May 2026 Test Data
==========================================
Seeds Supabase with all 7+1 invoice scenarios for Suryakant Optics (Nashik).
Also uploads the GSTR-2B records.

Run from project root:
    python testing/seed_may2026_demo.py

What this sets up:
  - 7 processed invoices covering all ITC/reconciliation paths
  - 7 GSTR-2B records (Royal Optica absent → triggers AT_RISK)
  - 6 supplier records with realistic health scores
  - Correct ITC statuses pre-set so dashboard is demo-ready instantly
"""

import os
import sys
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# Load env from backend/.env
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / "backend" / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
db = create_client(SUPABASE_URL, SUPABASE_KEY)

# === TRADER === (Suryakant Optics, already in DB)
TRADER_ID = "6d123264-9325-4a37-b769-274834a04085"
TRADER_GSTIN = "27ACCPS7562H1Z8"

# =====================================================================
# STEP 1 — Upsert all supplier records
# =====================================================================
SUPPLIERS = [
    {
        "gstin": "27AABCN5432P1Z3",
        "legal_name": "Nashik Optical Wholesalers Pvt Ltd",
        "trade_name": "Nashik Optical",
        "taxpayer_type": "Regular",
        "registration_date": "2018-04-15",
        "business_category": "Wholesale — Optical goods",
        "is_einvoice_mandated": False,
        "health_score": 95,
    },
    {
        "gstin": "33AADCS7891K1Z2",
        "legal_name": "SafeVision Lens Manufacturing Co",
        "trade_name": "SafeVision",
        "taxpayer_type": "Regular",
        "registration_date": "2019-07-22",
        "business_category": "Manufacturing — Contact lenses & optical elements",
        "is_einvoice_mandated": False,
        "health_score": 88,
    },
    {
        "gstin": "24AABCR8765H1Z4",
        "legal_name": "Royal Optica Frames",
        "trade_name": "Royal Optica",
        "taxpayer_type": "Regular",
        "registration_date": "2015-10-08",
        "business_category": "Manufacturing — Spectacle frames",
        "is_einvoice_mandated": False,
        "health_score": 52,  # Deducted for NOT filing May 2026
    },
    {
        "gstin": "27AADCW3456P1Z8",
        "legal_name": "Woodland Residency",
        "trade_name": "Woodland Residency Hotel",
        "taxpayer_type": "Regular",
        "registration_date": "2012-06-01",
        "business_category": "Services — Hotel & restaurant",
        "is_einvoice_mandated": False,
        "health_score": 90,
    },
    {
        "gstin": "27ABCPV6789H1Z1",
        "legal_name": "Shree Vinayak Spectacle Works",
        "trade_name": "Shree Vinayak",
        "taxpayer_type": "Regular",
        "registration_date": "2020-03-17",
        "business_category": "Manufacturing — Glass lenses",
        "is_einvoice_mandated": False,
        "health_score": 70,  # Deducted for wrong HSN rate on invoice
    },
    {
        "gstin": "27AADCV3421P1ZN",
        "legal_name": "VisionTech Optical Solutions",
        "trade_name": "VisionTech",
        "taxpayer_type": "Regular",
        "registration_date": "2026-02-14",  # <180 days — fraud signal!
        "business_category": "Trading — Optical goods",
        "is_einvoice_mandated": False,
        "health_score": 30,  # Very low — new + high value
    },
    {
        "gstin": "29AABCT8765P1Z4",
        "legal_name": "Titan Eyeplus Distribution Network",
        "trade_name": "Titan Eyeplus",
        "taxpayer_type": "Regular",
        "registration_date": "2011-09-14",
        "business_category": "Wholesale — Titan brand eyewear",
        "is_einvoice_mandated": True,
        "health_score": 98,
    },
    {
        "gstin": "27AABCA9876H1Z7",
        "legal_name": "Arihant Optics Ltd",
        "trade_name": "Arihant Optics",
        "taxpayer_type": "Regular",
        "registration_date": "2016-02-28",
        "business_category": "Wholesale — Optical frames & accessories",
        "is_einvoice_mandated": False,
        "health_score": 92,
    },
]

print("\n━━━ STEP 1: Upserting suppliers ━━━")
supplier_id_map = {}  # gstin -> uuid

for s in SUPPLIERS:
    resp = db.table("suppliers").upsert(s, on_conflict="gstin").execute()
    sup_id = resp.data[0]["id"]
    supplier_id_map[s["gstin"]] = sup_id
    print(f"  ✓ {s['trade_name']} → {sup_id[:8]}... (health: {s['health_score']})")

# =====================================================================
# STEP 2 — Add supplier flags
# =====================================================================
print("\n━━━ STEP 2: Adding supplier flags ━━━")

def set_flag(supplier_id, flag_type, metadata):
    """Delete existing flag of same type then insert fresh."""
    db.table("supplier_flags").delete().eq("supplier_id", supplier_id).eq("flag_type", flag_type).execute()
    db.table("supplier_flags").insert({
        "supplier_id": supplier_id,
        "flag_type": flag_type,
        "metadata": metadata,
        "is_active": True,
    }).execute()

# Royal Optica — non-filer
royal_id = supplier_id_map["24AABCR8765H1Z4"]
set_flag(royal_id, "NON_FILER", {"month": 5, "year": 2026, "return_type": "GSTR1"})
print("  ⚠️  Royal Optica → NON_FILER flag")

# Shree Vinayak — HSN mismatch
vinayak_id = supplier_id_map["27ABCPV6789H1Z1"]
set_flag(vinayak_id, "HSN_MISMATCH", {"invoice": "SVSW/2526/344", "hsn": "9004", "charged_rate": 18, "correct_rate": 12})
print("  ⚠️  Shree Vinayak → HSN_MISMATCH flag")

# VisionTech — new entity + high value
vtech_id = supplier_id_map["27AADCV3421P1ZN"]
set_flag(vtech_id, "NEW_ENTITY_HIGH_VALUE", {"gstin_age_days": 100, "invoice_value": 476000, "registration_date": "2026-02-14"})
print("  🚨 VisionTech → NEW_ENTITY_HIGH_VALUE flag")

# =====================================================================
# STEP 3 — Link suppliers to trader
# =====================================================================
print("\n━━━ STEP 3: Linking suppliers to trader ━━━")
for gstin, sup_id in supplier_id_map.items():
    try:
        db.table("supplier_trader_links").upsert({
            "trader_id": TRADER_ID,
            "supplier_id": sup_id,
            "total_invoice_count": 1,
        }, on_conflict="trader_id,supplier_id").execute()
        print(f"  ✓ {gstin[:14]}... linked")
    except Exception as e:
        print(f"  – {gstin[:14]}... already linked or error: {e}")

# =====================================================================
# STEP 4 — Upsert GSTR-2B records (7 entries, Royal Optica ABSENT)
# =====================================================================
GSTR2B_RECORDS = [
    # Scenario 1 — perfect match
    {"supplier_gstin": "27AABCN5432P1Z3", "invoice_number": "NOL/2025-26/1847", "invoice_date": "2026-05-08", "taxable_value": 22500.00, "cgst": 1350.00, "sgst": 1350.00, "igst": 0.00, "itc_eligible": True},
    # Scenario 2 — fuzzy match (typo: missing leading zeros)
    {"supplier_gstin": "33AADCS7891K1Z2", "invoice_number": "SVLC/MAY/2026/892", "invoice_date": "2026-05-14", "taxable_value": 19000.00, "cgst": 0.00, "sgst": 0.00, "igst": 2280.00, "itc_eligible": True},
    # Scenario 3 — Royal Optica ABSENT (ITC at risk)
    # NO record for 24AABCR8765H1Z4 — this is intentional
    # Scenario 4 — Woodland (restaurant, ITC blocked by law despite filing)
    {"supplier_gstin": "27AADCW3456P1Z8", "invoice_number": "WR/MAY/2026/4521", "invoice_date": "2026-05-22", "taxable_value": 3500.00, "cgst": 315.00, "sgst": 315.00, "igst": 0.00, "itc_eligible": True},
    # Scenario 5 — Shree Vinayak (filed with wrong HSN rate)
    {"supplier_gstin": "27ABCPV6789H1Z1", "invoice_number": "SVSW/2526/344", "invoice_date": "2026-05-05", "taxable_value": 24000.00, "cgst": 2160.00, "sgst": 2160.00, "igst": 0.00, "itc_eligible": True},
    # Scenario 6 — VisionTech (new GSTIN, fraud risk)
    {"supplier_gstin": "27AADCV3421P1ZN", "invoice_number": "VTOS/2026/001", "invoice_date": "2026-05-25", "taxable_value": 425000.00, "cgst": 25500.00, "sgst": 25500.00, "igst": 0.00, "itc_eligible": True},
    # Scenario 7 — Titan (different invoice number format)
    {"supplier_gstin": "29AABCT8765P1Z4", "invoice_number": "TITANB00040320", "invoice_date": "2026-05-12", "taxable_value": 36000.00, "cgst": 0.00, "sgst": 0.00, "igst": 4320.00, "itc_eligible": True},
    # Scenario 8 — Arihant (MISSED ITC — filed in 2B, never scanned by trader)
    {"supplier_gstin": "27AABCA9876H1Z7", "invoice_number": "AOL/2526/0847", "invoice_date": "2026-05-02", "taxable_value": 38000.00, "cgst": 2280.00, "sgst": 2280.00, "igst": 0.00, "itc_eligible": True},
]

print("\n━━━ STEP 4: Inserting GSTR-2B records (month=5, year=2026) ━━━")

# First clear existing May 2026 records for this trader
db.table("gstr2b_records").delete().eq("trader_id", TRADER_ID).eq("month", 5).eq("year", 2026).execute()
print("  – Cleared existing May 2026 GSTR-2B records")

for rec in GSTR2B_RECORDS:
    db.table("gstr2b_records").insert({
        "trader_id": TRADER_ID,
        "month": 5,
        "year": 2026,
        **rec,
    }).execute()
    total = rec["taxable_value"] + rec["cgst"] + rec["sgst"] + rec["igst"]
    print(f"  ✓ {rec['supplier_gstin']} | {rec['invoice_number']} | ₹{total:,.0f}")

# =====================================================================
# STEP 5 — Upsert processed invoice records
# =====================================================================
def make_hash(gstin, inv_num, date):
    return hashlib.sha256(f"{gstin}|{inv_num}|{date}".encode()).hexdigest()

now_ts = datetime.now(timezone.utc).isoformat()

INVOICES = [
    {
        "trader_id": TRADER_ID,
        "supplier_id": supplier_id_map["27AABCN5432P1Z3"],
        "invoice_number": "NOL/2025-26/1847",
        "invoice_date": "2026-05-08",
        "gstin_supplier": "27AABCN5432P1Z3",
        "gstin_buyer": TRADER_GSTIN,
        "supplier_name": "NASHIK OPTICAL WHOLESALERS PVT LTD",
        "taxable_amount": 22500.00,
        "cgst_amount": 1350.00,
        "sgst_amount": 1350.00,
        "igst_amount": 0.00,
        "total_amount": 25200.00,
        "status": "validated",
        "itc_status": "CONFIRMED",
        "itc_amount_eligible": 2700.00,
        "itc_amount_blocked": 0.00,
        "itc_block_reason": None,
        "gstr2b_match_status": "MATCHED",
        "gstr2b_match_confidence": 1.0,
        "fraud_score": 5,
        "fraud_signals": {"signals": []},
        "processing_duration_ms": 1840,
        "invoice_hash": make_hash("27AABCN5432P1Z3", "NOL/2025-26/1847", "2026-05-08"),
        "processed_at": now_ts,
    },
    {
        "trader_id": TRADER_ID,
        "supplier_id": supplier_id_map["33AADCS7891K1Z2"],
        "invoice_number": "SVLC/MAY/2026/00892",
        "invoice_date": "2026-05-14",
        "gstin_supplier": "33AADCS7891K1Z2",
        "gstin_buyer": TRADER_GSTIN,
        "supplier_name": "SAFEVISION LENS MANUFACTURING CO",
        "taxable_amount": 19000.00,
        "cgst_amount": 0.00,
        "sgst_amount": 0.00,
        "igst_amount": 2280.00,
        "total_amount": 21280.00,
        "status": "validated",
        "itc_status": "CONFIRMED",
        "itc_amount_eligible": 2280.00,
        "itc_amount_blocked": 0.00,
        "itc_block_reason": "GSTR-2B probable match (invoice no. format mismatch, Levenshtein dist=2). ITC proceeding.",
        "gstr2b_match_status": "PROBABLE_MATCH",
        "gstr2b_match_confidence": 0.70,
        "fraud_score": 8,
        "fraud_signals": {"signals": []},
        "processing_duration_ms": 2210,
        "invoice_hash": make_hash("33AADCS7891K1Z2", "SVLC/MAY/2026/00892", "2026-05-14"),
        "processed_at": now_ts,
    },
    {
        "trader_id": TRADER_ID,
        "supplier_id": supplier_id_map["24AABCR8765H1Z4"],
        "invoice_number": "ROF/2526/MAY/0156",
        "invoice_date": "2026-05-19",
        "gstin_supplier": "24AABCR8765H1Z4",
        "gstin_buyer": TRADER_GSTIN,
        "supplier_name": "ROYAL OPTICA FRAMES",
        "taxable_amount": 32000.00,
        "cgst_amount": 0.00,
        "sgst_amount": 0.00,
        "igst_amount": 3840.00,
        "total_amount": 35840.00,
        "status": "flagged",
        "itc_status": "AT_RISK",
        "itc_amount_eligible": 3840.00,
        "itc_amount_blocked": 0.00,
        "itc_block_reason": "Invoice not found in GSTR-2B — Royal Optica Frames has not filed GSTR-1 for May 2026",
        "gstr2b_match_status": "ITC_AT_RISK",
        "gstr2b_match_confidence": 0.0,
        "fraud_score": 12,
        "fraud_signals": {"signals": []},
        "processing_duration_ms": 1950,
        "invoice_hash": make_hash("24AABCR8765H1Z4", "ROF/2526/MAY/0156", "2026-05-19"),
        "processed_at": now_ts,
    },
    {
        "trader_id": TRADER_ID,
        "supplier_id": supplier_id_map["27AADCW3456P1Z8"],
        "invoice_number": "WR/MAY/2026/4521",
        "invoice_date": "2026-05-22",
        "gstin_supplier": "27AADCW3456P1Z8",
        "gstin_buyer": TRADER_GSTIN,
        "supplier_name": "WOODLAND RESIDENCY",
        "taxable_amount": 3500.00,
        "cgst_amount": 315.00,
        "sgst_amount": 315.00,
        "igst_amount": 0.00,
        "total_amount": 4130.00,
        "status": "flagged",
        "itc_status": "INELIGIBLE",
        "itc_amount_eligible": 0.00,
        "itc_amount_blocked": 630.00,
        "itc_block_reason": "Section 17(5)(b): Restaurant/food & beverage services — ITC not available under GST law",
        "gstr2b_match_status": "MATCHED",
        "gstr2b_match_confidence": 1.0,
        "fraud_score": 2,
        "fraud_signals": {"signals": []},
        "processing_duration_ms": 1620,
        "invoice_hash": make_hash("27AADCW3456P1Z8", "WR/MAY/2026/4521", "2026-05-22"),
        "processed_at": now_ts,
    },
    {
        "trader_id": TRADER_ID,
        "supplier_id": supplier_id_map["27ABCPV6789H1Z1"],
        "invoice_number": "SVSW/2526/344",
        "invoice_date": "2026-05-05",
        "gstin_supplier": "27ABCPV6789H1Z1",
        "gstin_buyer": TRADER_GSTIN,
        "supplier_name": "SHREE VINAYAK SPECTACLE WORKS",
        "taxable_amount": 24000.00,
        "cgst_amount": 2160.00,
        "sgst_amount": 2160.00,
        "igst_amount": 0.00,
        "total_amount": 28320.00,
        "status": "flagged",
        "itc_status": "FIXABLE_BLOCKED",
        "itc_amount_eligible": 2880.00,
        "itc_amount_blocked": 1440.00,
        "itc_block_reason": "HSN 9004 rate mismatch: charged 18%, correct rate is 12% for spectacle frames. Excess CGST+SGST of ₹1,440 blocked.",
        "gstr2b_match_status": "MATCHED",
        "gstr2b_match_confidence": 1.0,
        "fraud_score": 10,
        "fraud_signals": {"signals": [{"name": "hsn_mismatch", "detail": "18% charged vs 12% correct"}]},
        "processing_duration_ms": 2050,
        "invoice_hash": make_hash("27ABCPV6789H1Z1", "SVSW/2526/344", "2026-05-05"),
        "processed_at": now_ts,
    },
    {
        "trader_id": TRADER_ID,
        "supplier_id": supplier_id_map["27AADCV3421P1ZN"],
        "invoice_number": "VTOS/2026/001",
        "invoice_date": "2026-05-25",
        "gstin_supplier": "27AADCV3421P1ZN",
        "gstin_buyer": TRADER_GSTIN,
        "supplier_name": "VISIONTECH OPTICAL SOLUTIONS",
        "taxable_amount": 425000.00,
        "cgst_amount": 25500.00,
        "sgst_amount": 25500.00,
        "igst_amount": 0.00,
        "total_amount": 476000.00,
        "status": "flagged",
        "itc_status": "FRAUD_FLAGGED",
        "itc_amount_eligible": 0.00,
        "itc_amount_blocked": 51000.00,
        "itc_block_reason": "Fraud score 72/100 — GSTIN registered 100 days ago (threshold: 180), invoice value ₹4.76L, sequential invoice #001. Manual CA review required.",
        "gstr2b_match_status": "MATCHED",
        "gstr2b_match_confidence": 1.0,
        "fraud_score": 72,
        "fraud_signals": {
            "signals": [
                {"name": "gstin_age", "triggered": True, "score": 20, "detail": "GSTIN 100 days old with ₹4,76,000 invoice (threshold: 180 days, ₹50,000)"},
                {"name": "sequential_invoices", "triggered": True, "score": 15, "detail": "Invoice number VTOS/2026/001 — first invoice from this supplier"}
            ],
            "total_score": 72,
            "is_hard_flag": True
        },
        "processing_duration_ms": 2890,
        "invoice_hash": make_hash("27AADCV3421P1ZN", "VTOS/2026/001", "2026-05-25"),
        "processed_at": now_ts,
    },
    {
        "trader_id": TRADER_ID,
        "supplier_id": supplier_id_map["29AABCT8765P1Z4"],
        "invoice_number": "TET/NAS/0512/2026",
        "invoice_date": "2026-05-12",
        "gstin_supplier": "29AABCT8765P1Z4",
        "gstin_buyer": TRADER_GSTIN,
        "supplier_name": "TITAN EYEPLUS DISTRIBUTION NETWORK",
        "taxable_amount": 36000.00,
        "cgst_amount": 0.00,
        "sgst_amount": 0.00,
        "igst_amount": 4320.00,
        "total_amount": 40320.00,
        "status": "validated",
        "itc_status": "CONFIRMED",
        "itc_amount_eligible": 4320.00,
        "itc_amount_blocked": 0.00,
        "itc_block_reason": "GSTR-2B possible match (amount+date match, invoice number format differs). ITC proceeding with CA verification recommended.",
        "gstr2b_match_status": "POSSIBLE_MATCH",
        "gstr2b_match_confidence": 0.6,
        "fraud_score": 5,
        "fraud_signals": {"signals": []},
        "processing_duration_ms": 1780,
        "invoice_hash": make_hash("29AABCT8765P1Z4", "TET/NAS/0512/2026", "2026-05-12"),
        "processed_at": now_ts,
    },
]

print("\n━━━ STEP 5: Inserting invoice records ━━━")
for inv in INVOICES:
    # Delete any existing record with same hash to allow re-seeding
    db.table("invoices").delete().eq("invoice_hash", inv["invoice_hash"]).execute()
    resp = db.table("invoices").insert(inv).execute()
    inv_id = resp.data[0]["id"]
    status_icon = {"CONFIRMED": "✅", "AT_RISK": "🔴", "INELIGIBLE": "🚫", "FIXABLE_BLOCKED": "🔧", "FRAUD_FLAGGED": "🚨"}.get(inv["itc_status"], "⚠️")
    print(f"  {status_icon} {inv['supplier_name'][:30]:30s} | {inv['itc_status']:16s} | ₹{inv['total_amount']:>10,.0f}")

# =====================================================================
# SUMMARY
# =====================================================================
confirmed = sum(i["itc_amount_eligible"] for i in INVOICES if i["itc_status"] == "CONFIRMED")
at_risk = sum(i["itc_amount_eligible"] for i in INVOICES if i["itc_status"] == "AT_RISK")
fixable = sum(i["itc_amount_blocked"] for i in INVOICES if i["itc_status"] == "FIXABLE_BLOCKED")
ineligible = sum(i["itc_amount_blocked"] for i in INVOICES if i["itc_status"] == "INELIGIBLE")
fraud = sum(i["itc_amount_blocked"] for i in INVOICES if i["itc_status"] == "FRAUD_FLAGGED")

print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DEMO SEED COMPLETE — May 2026, Suryakant Optics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Invoices seeded : {len(INVOICES)}
  GSTR-2B records : {len(GSTR2B_RECORDS)} (Royal Optica ABSENT)
  Suppliers       : {len(SUPPLIERS)}

  ITC SUMMARY
  ✅ Confirmed ITC   : ₹{confirmed:>10,.0f}
  🔴 At Risk         : ₹{at_risk:>10,.0f}  ← contact Royal Optica
  🔧 Fixable Blocked : ₹{fixable:>10,.0f}  ← Shree Vinayak credit note
  🚫 Ineligible      : ₹{ineligible:>10,.0f}  ← Sec 17(5) restaurant bill
  🚨 Fraud Flagged   : ₹{fraud:>10,.0f}  ← VisionTech manual review
  💸 Missed ITC      : ₹   4,560.00  ← Arihant Optics (in GSTR-2B, not scanned)

  POTENTIAL RECOVERY: ₹{fixable + at_risk:>10,.0f}

  → Open http://localhost:3000 to see the dashboard
  → Upload gstr2b_may2026.json to also trigger live reconciliation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
