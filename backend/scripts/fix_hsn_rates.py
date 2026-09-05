"""
Munim.ai — Fast HSN Rate Fix (Batch by chapter using Supabase filter)
Instead of updating row-by-row, this uses Supabase's bulk filter+update.
Updates all HSN codes of a given chapter prefix in one API call per chapter.
"""

import os
import sys
import time

_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _backend_dir)
from dotenv import load_dotenv
load_dotenv(os.path.join(_backend_dir, ".env"))

from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
db = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Chapter → rate mapping (official GST schedule)
CHAPTER_RATES = {
    0.0:  ['01','02','05','07','08','09','10','11','12','13','14','23','26'],
    5.0:  ['03','04','06','15','17','25','27','31','41','50','51','52','53','54','55','60','61','62','63','89'],
    12.0: ['16','20','21','30','44','45','46','47','49','56','57','58','59','86','93','97'],
    18.0: ['18','19','22','28','29','32','33','34','35','36','37','38','39','40','42','43','48',
           '64','65','66','67','68','69','70','72','73','74','75','76','77','78','79','80','81',
           '82','83','84','85','88','90','91','94','95','96','99'],
    28.0: ['24','92'],
    3.0:  ['71'],
}

# Specific HSN prefix overrides (4-digit, applied after chapter)
HSN_OVERRIDES = [
    # (hsn_prefix_like, rate)
    ('8703', 28.0), ('8704', 28.0), ('8711', 28.0),  # Motor vehicles
    ('2523', 28.0),                                    # Cement
    ('8415', 28.0), ('8418', 28.0), ('8450', 28.0),  # AC, fridge, washing machine
    ('8517', 12.0),                                    # Mobile phones
    ('8541', 12.0),                                    # Solar panels
    ('3004', 5.0),  ('3003', 5.0),  ('3002', 5.0),   # Pharma
    ('3101', 5.0),  ('3102', 5.0),  ('3103', 5.0),   # Fertilizers
    ('7108', 3.0),  ('7107', 3.0),                    # Gold
    ('2709', 0.0),  ('2710', 0.0),                    # Petroleum (exempt)
    ('4901', 0.0),  ('4902', 0.0),  ('4903', 0.0),   # Books
    ('2401', 28.0), ('2402', 28.0), ('2403', 28.0),  # Tobacco
    ('2701', 5.0),  ('2702', 5.0),                    # Coal
    ('2711', 5.0),                                     # LPG/Natural gas
    ('2601', 5.0),                                     # Iron ore
    ('5205', 5.0),  ('5206', 5.0),                    # Cotton yarn
    ('8601', 5.0),  ('8602', 5.0),  ('8603', 5.0),   # Railway
    # SAC codes
    ('9954', 18.0), ('9963', 18.0), ('9964', 18.0),
    ('9965', 18.0), ('9971', 18.0), ('9972', 18.0),
    ('9973', 18.0), ('9983', 18.0), ('9984', 18.0),
    ('9985', 18.0), ('9986', 0.0),  ('9987', 18.0),
    ('9988', 5.0),  ('9991', 0.0),  ('9992', 0.0),
    ('9993', 5.0),  ('9995', 18.0), ('9996', 28.0),
    ('9997', 18.0),
]


def update_by_chapter():
    total = 0
    print("Phase 1: Updating by chapter...")
    for rate, chapters in CHAPTER_RATES.items():
        for chapter in chapters:
            try:
                # Supabase: filter hsn_code starting with chapter (2-digit prefix)
                resp = db.table("hsn_codes").update(
                    {"gst_rate": rate}
                ).like("hsn_code", f"{chapter}%").neq("gst_rate", rate).execute()
                count = len(resp.data) if resp.data else 0
                if count > 0:
                    total += count
                    print(f"  Chapter {chapter}: {count} rows → {rate}%")
            except Exception as e:
                print(f"  Chapter {chapter} failed: {e}")
    print(f"Phase 1 done. Updated {total} rows.\n")


def update_overrides():
    total = 0
    print("Phase 2: Applying specific HSN overrides...")
    for prefix, rate in HSN_OVERRIDES:
        try:
            resp = db.table("hsn_codes").update(
                {"gst_rate": rate}
            ).like("hsn_code", f"{prefix}%").execute()
            count = len(resp.data) if resp.data else 0
            if count > 0:
                total += count
                print(f"  {prefix}%: {count} rows → {rate}%")
        except Exception as e:
            print(f"  Override {prefix} failed: {e}")
    print(f"Phase 2 done. Updated {total} override rows.\n")


def verify():
    print("Verifying rate distribution...")
    for rate in [0.0, 3.0, 5.0, 12.0, 18.0, 28.0]:
        try:
            resp = db.table("hsn_codes").select("id", count="exact").eq("gst_rate", rate).execute()
            print(f"  {rate}%: {resp.count or 0} codes")
        except Exception as e:
            print(f"  Rate {rate} count failed: {e}")


if __name__ == "__main__":
    update_by_chapter()
    update_overrides()
    verify()
    print("\n✅ HSN rate fix complete!")
