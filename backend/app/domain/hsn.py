"""
Munim.ai — HSN Code Validation Engine
Exact lookup + pgvector semantic fallback for HSN code validation.
"""

import logging
from typing import Optional

from app.models.invoice import HSNValidationResult, LineItem
from app.services.gemini import embed_text

logger = logging.getLogger(__name__)


# Standard GST rate slabs
VALID_GST_RATES = [0.0, 5.0, 12.0, 18.0, 28.0]


class HSNValidator:
    """
    Validates HSN codes on invoices against the official HSN 2.0 database.
    Two-pass: exact DB lookup → pgvector semantic search on line item description.
    """

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def validate_line_item(self, item: LineItem) -> HSNValidationResult:
        """Validate a single line item's HSN code."""
        hsn_code = (item.hsn_code or "").strip()
        applied_rate = (item.cgst_rate or 0) + (item.sgst_rate or 0) + (item.igst_rate or 0)

        result = HSNValidationResult(
            hsn_code_extracted=hsn_code,
            tax_rate_applied=applied_rate,
        )

        if not hsn_code:
            # No HSN code on invoice — try semantic search
            return await self._semantic_search(item.description, result)

        # --- Pass 1: Exact lookup ---
        try:
            response = self.db.table("hsn_codes").select(
                "hsn_code, description, gst_rate"
            ).eq("hsn_code", hsn_code).execute()

            if response.data and len(response.data) > 0:
                record = response.data[0]
                result.hsn_code_validated = record["hsn_code"]
                result.is_valid = True
                result.tax_rate_correct = record["gst_rate"]

                # Check rate mismatch
                if abs(applied_rate - record["gst_rate"]) > 0.1:
                    result.rate_mismatch = True
                    taxable = item.taxable_value or 0
                    result.itc_delta = (record["gst_rate"] - applied_rate) / 100 * taxable

                return result
        except Exception as e:
            logger.error(f"HSN exact lookup failed: {e}")

        # --- Pass 2: Semantic search ---
        return await self._semantic_search(item.description, result)

    async def _semantic_search(
        self, description: str, result: HSNValidationResult
    ) -> HSNValidationResult:
        """Use pgvector to find the closest HSN code by description embedding."""
        if not description:
            result.is_valid = False
            return result

        try:
            # Generate embedding for the line item description
            embedding = await embed_text(description)
            if not embedding:
                result.is_valid = False
                return result

            # Query pgvector for nearest neighbor
            response = self.db.rpc(
                "match_hsn_codes",
                {
                    "query_embedding": embedding,
                    "match_threshold": 0.5,
                    "match_count": 1,
                },
            ).execute()

            if response.data and len(response.data) > 0:
                match = response.data[0]
                result.suggestion = match.get("hsn_code")
                result.suggestion_description = match.get("description")
                result.confidence = match.get("similarity", 0.0)
                result.tax_rate_correct = match.get("gst_rate")
                result.is_valid = False  # Original code was invalid
                result.hsn_code_validated = match.get("hsn_code")

                # Compute ITC delta if rates differ
                if result.tax_rate_applied is not None and result.tax_rate_correct is not None:
                    if abs(result.tax_rate_applied - result.tax_rate_correct) > 0.1:
                        result.rate_mismatch = True

            return result

        except Exception as e:
            logger.error(f"HSN semantic search failed: {e}")
            result.is_valid = False
            return result

    async def validate_all_line_items(
        self, line_items: list[LineItem]
    ) -> list[HSNValidationResult]:
        """Validate all line items in an invoice."""
        results = []
        for item in line_items:
            validation = await self.validate_line_item(item)
            results.append(validation)
        return results
