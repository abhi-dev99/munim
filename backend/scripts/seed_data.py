"""
Munim.ai — Demo Seed Data Script
Seeds Supabase with 6 months of synthetic invoice history for "Raju's Kirana".
Run this once before the demo to have realistic data in the dashboard.

Usage: python -m scripts.seed_data
"""

import os
import sys
import random
import hashlib
from datetime import date, timedelta
from uuid import uuid4
import pandas as pd

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from supabase import create_client
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")
    sys.exit(1)

db = create_client(SUPABASE_URL, SUPABASE_KEY)


# --- Demo Suppliers ---

SUPPLIERS = [
    # Healthy suppliers (10)
    {"gstin": "27AABCU9603R1ZM", "legal_name": "Ramesh Trading Co.", "type": "Regular", "category": "Grocery", "health": 95, "age_days": 1200},
    {"gstin": "27AADCS1234P1Z5", "legal_name": "Patel Oil Mills", "type": "Regular", "category": "Edible Oils", "health": 92, "age_days": 2000},
    {"gstin": "09BBBFM5678Q1ZX", "legal_name": "Gupta Flour Industries", "type": "Regular", "category": "Food Products", "health": 88, "age_days": 1800},
    {"gstin": "27CCCGN3456R1Z3", "legal_name": "Mehta Spice Traders", "type": "Regular", "category": "Spices", "health": 90, "age_days": 1500},
    {"gstin": "24DDDHS7890S1Z7", "legal_name": "Gujarat Packaging", "type": "Regular", "category": "Packaging", "health": 85, "age_days": 900},
    {"gstin": "33EEEIJ2345T1ZW", "legal_name": "Chennai Rice Exports", "type": "Regular", "category": "Rice", "health": 93, "age_days": 3000},
    {"gstin": "27FFFKL6789U1Z2", "legal_name": "Mumbai Dairy Products", "type": "Regular", "category": "Dairy", "health": 87, "age_days": 1100},
    {"gstin": "09GGGMN1234V1Z6", "legal_name": "Agra Sugar Mills", "type": "Regular", "category": "Sugar", "health": 91, "age_days": 2500},
    {"gstin": "07HHHOP5678W1ZQ", "legal_name": "Delhi Beverages Ltd", "type": "Regular", "category": "Beverages", "health": 89, "age_days": 1700},
    {"gstin": "29IIIQR9012X1Z1", "legal_name": "Bangalore Pulses Co", "type": "Regular", "category": "Pulses", "health": 94, "age_days": 2200},

    # Flagged suppliers (3)
    {"gstin": "27JJJST3456Y1Z5", "legal_name": "Sharma Trading Pvt Ltd", "type": "Regular", "category": "General Trading", "health": 30, "age_days": 800,
     "flags": ["MISSED_FILING", "ERRATIC_FILER"]},
    {"gstin": "09KKKUV7890Z1ZX", "legal_name": "Verma Iron & Steel", "type": "Regular", "category": "Iron & Steel", "health": 25, "age_days": 400,
     "flags": ["SECTOR_RISK", "HABITUAL_LATE"]},
    {"gstin": "33LLLWX1234A1Z3", "legal_name": "Tamil Textiles Corp", "type": "Composition", "category": "Textiles", "health": 20, "age_days": 600,
     "flags": ["SCHEME_SWITCH"]},

    # At-risk suppliers (2)
    {"gstin": "27MMMYZ5678B1Z7", "legal_name": "New Star Enterprises", "type": "Regular", "category": "Construction Materials", "health": 15, "age_days": 90,
     "flags": ["NEW_GSTIN_RISK", "SECTOR_RISK"]},
    {"gstin": "09NNNAB9012C1ZW", "legal_name": "Quick Deals Trading", "type": "Regular", "category": "General Trading", "health": 10, "age_days": 45,
     "flags": ["NEW_GSTIN_RISK", "ITC_GHOST"]},
]

def seed_hsn_codes():
    """Seed HSN codes from official HSN_SAC.xlsx."""
    print("📦 Seeding official HSN codes from HSN_SAC.xlsx...")
    try:
        df = pd.read_excel('HSN_SAC.xlsx')
        df = df.dropna(subset=['HSN_CD', 'HSN_Description'])
        hsn_codes = []
        for _, row in df.iterrows():
            code = str(row['HSN_CD']).strip().replace('.0', '')
            desc = str(row['HSN_Description']).strip()
            if not code or not desc:
                continue
            hsn_codes.append({
                "hsn_code": code[:10],
                "description": desc,
                "gst_rate": 18.0,  # Default fallback rate
                "category": "General",
            })
        
        batch_size = 500
        total_seeded = 0
        for i in range(0, len(hsn_codes), batch_size):
            batch = hsn_codes[i:i + batch_size]
            db.table("hsn_codes").upsert(batch, on_conflict="hsn_code").execute()
            total_seeded += len(batch)
            print(f"  Inserted {total_seeded} / {len(hsn_codes)} HSN codes...")
            
        print(f"  ✅ {total_seeded} real-world HSN codes seeded successfully")
    except Exception as e:
        print(f"  ❌ Error seeding HSN codes: {e}")


def seed_trader():
    """Seed the demo trader — Raju's Kirana."""
    print("👤 Seeding demo trader...")
    trader = db.table("traders").upsert({
        "whatsapp_number": "919876543210",
        "name": "Raju",
        "gstin": "27AABCU9603R1ZM",  # Using first supplier GSTIN as demo
        "business_name": "Raju's Kirana Store, Lucknow",
        "language_pref": "hi",
    }, on_conflict="whatsapp_number").execute()
    trader_id = trader.data[0]["id"]
    print(f"  ✅ Trader: {trader_id}")
    return trader_id


def seed_suppliers():
    """Seed all demo suppliers."""
    print("🏭 Seeding suppliers...")
    supplier_ids = {}

    for s in SUPPLIERS:
        try:
            result = db.table("suppliers").upsert({
                "gstin": s["gstin"],
                "legal_name": s["legal_name"],
                "taxpayer_type": s["type"],
                "business_category": s["category"],
                "health_score": s["health"],
                "registration_date": (date.today() - timedelta(days=s["age_days"])).isoformat(),
            }, on_conflict="gstin").execute()

            supplier_id = result.data[0]["id"]
            supplier_ids[s["gstin"]] = supplier_id

            # Add flags
            for flag in s.get("flags", []):
                db.table("supplier_flags").insert({
                    "supplier_id": supplier_id,
                    "flag_type": flag,
                    "metadata": {"detail": f"Demo flag: {flag}"},
                    "is_active": True,
                }).execute()

        except Exception as e:
            print(f"  ⚠️ Supplier {s['legal_name']}: {e}")

    print(f"  ✅ {len(SUPPLIERS)} suppliers seeded")
    return supplier_ids


def seed_invoices(trader_id: str, supplier_ids: dict):
    """Seed 6 months of invoice history."""
    print("📄 Seeding invoices (6 months)...")
    today = date.today()
    invoice_count = 0

    for month_offset in range(6, 0, -1):
        month_date = today - timedelta(days=month_offset * 30)
        month = month_date.month
        year = month_date.year

        # 30-80 invoices per month
        num_invoices = random.randint(30, 80)

        for _ in range(num_invoices):
            supplier = random.choice(SUPPLIERS)
            supplier_id = supplier_ids.get(supplier["gstin"])
            if not supplier_id:
                continue

            # Random HSN and amount
            hsn_code, hsn_desc, gst_rate, hsn_cat = random.choice(HSN_DATA[:15])  # Skip blocked categories
            taxable = round(random.uniform(500, 50000), 2)

            # Determine tax type (CGST+SGST for intra-state, IGST for inter-state)
            if supplier["gstin"][:2] == "27":  # Maharashtra (same state as trader)
                cgst = round(taxable * gst_rate / 200, 2)
                sgst = cgst
                igst = 0
            else:
                cgst = 0
                sgst = 0
                igst = round(taxable * gst_rate / 100, 2)

            total_tax = cgst + sgst + igst
            total = round(taxable + total_tax, 2)

            # Determine ITC status based on supplier health
            if supplier["health"] >= 80:
                itc_status = "CONFIRMED"
                itc_eligible = total_tax
                itc_blocked = 0
                block_reason = None
            elif supplier["health"] >= 40:
                itc_status = random.choice(["CONFIRMED", "AT_RISK"])
                itc_eligible = total_tax if itc_status == "CONFIRMED" else 0
                itc_blocked = total_tax if itc_status == "AT_RISK" else 0
                block_reason = "Supplier compliance issue" if itc_status == "AT_RISK" else None
            else:
                itc_status = random.choice(["AT_RISK", "FIXABLE_BLOCKED"])
                itc_eligible = 0
                itc_blocked = total_tax
                block_reason = "Supplier non-compliant" if itc_status == "AT_RISK" else "HSN rate mismatch"

            # Occasionally create HSN mismatches (for demo realism)
            fraud_score = 0
            if random.random() < 0.05:
                itc_status = "FIXABLE_BLOCKED"
                itc_eligible = 0
                itc_blocked = total_tax
                block_reason = f"HSN mismatch: {hsn_code} incorrect"

            if random.random() < 0.02:
                fraud_score = random.randint(45, 85)
                if fraud_score >= 70:
                    itc_status = "FRAUD_FLAGGED"

            inv_number = f"INV-{year}{month:02d}-{random.randint(1000, 9999)}"
            inv_date = date(year, month, random.randint(1, 28))
            inv_hash = hashlib.sha256(
                f"{supplier['gstin']}|{inv_number}|{inv_date.isoformat()}".encode()
            ).hexdigest()

            try:
                db.table("invoices").insert({
                    "trader_id": trader_id,
                    "supplier_id": supplier_id,
                    "invoice_number": inv_number,
                    "invoice_date": inv_date.isoformat(),
                    "gstin_supplier": supplier["gstin"],
                    "gstin_buyer": "27AABCU9603R1ZM",
                    "taxable_amount": taxable,
                    "cgst_amount": cgst,
                    "sgst_amount": sgst,
                    "igst_amount": igst,
                    "total_amount": total,
                    "status": "validated",
                    "itc_status": itc_status,
                    "itc_amount_eligible": itc_eligible,
                    "itc_amount_blocked": itc_blocked,
                    "itc_block_reason": block_reason,
                    "fraud_score": fraud_score,
                    "invoice_hash": inv_hash,
                    "processing_duration_ms": random.randint(5000, 25000),
                }).execute()
                invoice_count += 1
            except Exception:
                pass  # Duplicate hash, skip

        # Link suppliers to trader
        for supplier in SUPPLIERS:
            sid = supplier_ids.get(supplier["gstin"])
            if sid:
                try:
                    db.table("supplier_trader_links").upsert({
                        "trader_id": trader_id,
                        "supplier_id": sid,
                        "total_invoice_count": random.randint(5, 50),
                    }, on_conflict="trader_id,supplier_id").execute()
                except Exception:
                    pass

    print(f"  ✅ {invoice_count} invoices seeded across 6 months")


def seed_gstr2b(trader_id: str):
    """Seed GSTR-2B records (some matching, some orphaned for MISSED_ITC demo)."""
    print("📋 Seeding GSTR-2B records...")
    today = date.today()
    count = 0

    for month_offset in range(6, 0, -1):
        month_date = today - timedelta(days=month_offset * 30)
        month = month_date.month
        year = month_date.year

        # Get invoices for this month
        invoices = db.table("invoices").select(
            "gstin_supplier, invoice_number, invoice_date, taxable_amount, cgst_amount, sgst_amount, igst_amount"
        ).eq("trader_id", trader_id).execute()

        # Add 80% of invoices to GSTR-2B (matched)
        for inv in (invoices.data or [])[:int(len(invoices.data or []) * 0.8)]:
            try:
                db.table("gstr2b_records").upsert({
                    "trader_id": trader_id,
                    "month": month,
                    "year": year,
                    "supplier_gstin": inv["gstin_supplier"],
                    "invoice_number": inv["invoice_number"],
                    "invoice_date": inv["invoice_date"],
                    "taxable_value": inv["taxable_amount"],
                    "igst": inv.get("igst_amount", 0),
                    "cgst": inv.get("cgst_amount", 0),
                    "sgst": inv.get("sgst_amount", 0),
                }, on_conflict="trader_id,month,year,supplier_gstin,invoice_number").execute()
                count += 1
            except Exception:
                pass

        # Add some orphaned records (MISSED_ITC — in 2B but not in trader's books)
        for i in range(random.randint(2, 5)):
            supplier = random.choice(SUPPLIERS[:10])
            try:
                db.table("gstr2b_records").insert({
                    "trader_id": trader_id,
                    "month": month,
                    "year": year,
                    "supplier_gstin": supplier["gstin"],
                    "invoice_number": f"ORPHAN-{year}{month:02d}-{random.randint(100, 999)}",
                    "invoice_date": date(year, month, random.randint(1, 28)).isoformat(),
                    "taxable_value": round(random.uniform(1000, 20000), 2),
                    "cgst": round(random.uniform(50, 1500), 2),
                    "sgst": round(random.uniform(50, 1500), 2),
                }).execute()
                count += 1
            except Exception:
                pass

    print(f"  ✅ {count} GSTR-2B records seeded")


def main():
    print("=" * 60)
    print("🔵 Munim.ai — Demo Data Seeder")
    print("=" * 60)

    seed_hsn_codes()
    trader_id = seed_trader()
    supplier_ids = seed_suppliers()
    seed_invoices(trader_id, supplier_ids)
    seed_gstr2b(trader_id)

    print()
    print("=" * 60)
    print("✅ Seeding complete!")
    print(f"   Trader ID: {trader_id}")
    print("   Use this ID for dashboard API calls")
    print("=" * 60)


if __name__ == "__main__":
    main()
