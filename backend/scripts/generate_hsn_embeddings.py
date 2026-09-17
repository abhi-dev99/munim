"""
Munim.ai — HSN Embeddings Generator
Generates Gemini text-embedding-004 embeddings for all HSN codes and stores in Supabase pgvector.
This enables semantic HSN search: "steel pipes" → finds 7304 automatically.

Run this ONCE after seeding HSN codes. Takes ~30-60 mins for 21,934 codes.
Uses batch processing with rate-limit handling.
"""

import os
import sys
import time
import asyncio

# Add backend to path
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(_backend_dir, ".env"))

import google.generativeai as genai
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

genai.configure(api_key=GEMINI_API_KEY)
db = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

EMBEDDING_MODEL = "models/text-embedding-004"
BATCH_SIZE = 20        # Gemini batch embed limit
REQUESTS_PER_MINUTE = 1500  # Free tier: 1500 RPM
SLEEP_BETWEEN_BATCHES = 60 / (REQUESTS_PER_MINUTE / BATCH_SIZE)  # ~0.8s per batch


def embed_texts_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts using Gemini text-embedding-004."""
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=texts,
        task_type="retrieval_document",
    )
    return result["embedding"]


def generate_hsn_embeddings():
    """Main function: fetch HSN codes without embeddings, generate and store."""
    print("🚀 Starting HSN embedding generation...")
    print(f"   Model: {EMBEDDING_MODEL}")
    print(f"   Batch size: {BATCH_SIZE}")
    print()

    # Count total to process
    total_resp = db.table("hsn_codes").select("id", count="exact").is_("embedding", "null").execute()
    total_missing = total_resp.count or 0
    print(f"📊 HSN codes missing embeddings: {total_missing}")

    if total_missing == 0:
        print("✅ All HSN codes already have embeddings!")
        return

    total_processed = 0
    total_errors = 0
    page_size = 200
    offset = 0

    while True:
        # Fetch a page of HSN codes without embeddings
        response = db.table("hsn_codes").select(
            "id, hsn_code, description, gst_rate"
        ).is_("embedding", "null").range(offset, offset + page_size - 1).execute()

        records = response.data or []
        if not records:
            break

        print(f"\n📦 Processing {len(records)} records (offset {offset})...")

        # Process in batches of BATCH_SIZE
        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i:i + BATCH_SIZE]

            # Build text representation for each HSN code
            texts = []
            for rec in batch:
                # Rich text: HSN code + description + rate
                text = f"HSN {rec['hsn_code']}: {rec['description']}. GST rate: {rec.get('gst_rate', 18)}%"
                texts.append(text)

            # Generate embeddings with retry
            embeddings = None
            for attempt in range(3):
                try:
                    embeddings = embed_texts_batch(texts)
                    break
                except Exception as e:
                    if attempt < 2:
                        print(f"  ⚠️ Attempt {attempt+1} failed: {e}. Retrying in 5s...")
                        time.sleep(5)
                    else:
                        print(f"  ❌ Failed after 3 attempts: {e}")
                        total_errors += len(batch)

            if not embeddings:
                continue

            # Store embeddings back to Supabase
            for rec, embedding in zip(batch, embeddings):
                try:
                    db.table("hsn_codes").update({
                        "embedding": embedding
                    }).eq("id", rec["id"]).execute()
                    total_processed += 1
                except Exception as e:
                    print(f"  ❌ Store failed for {rec['hsn_code']}: {e}")
                    total_errors += 1

            # Rate limiting
            time.sleep(SLEEP_BETWEEN_BATCHES)

        # Progress report
        pct = (total_processed / max(total_missing, 1)) * 100
        print(f"  ✅ Progress: {total_processed}/{total_missing} ({pct:.1f}%) | Errors: {total_errors}")

        offset += page_size
        if len(records) < page_size:
            break

    print(f"\n🏁 Done! Processed {total_processed} HSN embeddings. Errors: {total_errors}")

    # Verify
    remaining = db.table("hsn_codes").select("id", count="exact").is_("embedding", "null").execute()
    print(f"   Remaining without embedding: {remaining.count or 0}")


if __name__ == "__main__":
    generate_hsn_embeddings()
