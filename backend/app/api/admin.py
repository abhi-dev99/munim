import logging
from fastapi import APIRouter, HTTPException
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

@router.delete("/invoices/{invoice_id}")
async def delete_invoice(invoice_id: str):
    """Delete an invoice by ID (for demo admin purposes)."""
    db = get_supabase()
    try:
        db.table("invoices").delete().eq("id", invoice_id).execute()
        return {"status": "success", "deleted_id": invoice_id}
    except Exception as e:
        logger.error(f"Failed to delete invoice {invoice_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
