"""
Munim-AI — data backend switch.

Every api/*.py file imports from here instead of supabase_client or
dynamodb_client directly, so the choice of backend is made once, in one
place, based on settings.data_backend -- never scattered across call sites.

Both backends export the identical function set with identical signatures
and return shapes (see dynamodb_client.py's module docstring for the exact
contract it was built to match). Swapping DATA_BACKEND=dynamodb in the
environment is the entire cutover -- no code changes needed anywhere else.

get_supabase() is intentionally NOT re-exported here: it's a Supabase-only
concept (the raw client, for the handful of call sites -- mostly auth.py --
that still build their own .table(...) queries instead of going through a
named function). Those call sites are exactly the ones still being ported;
until they are, this module only backs the api/*.py files that were
rewritten to use named functions everywhere.
"""

from app.config import get_settings

_settings = get_settings()

if _settings.data_backend == "dynamodb":
    from app.services.dynamodb_client import (  # noqa: F401
        get_trader_by_phone,
        get_trader_by_short_code,
        get_trader_by_inbound_email,
        get_trader_by_id,
        create_trader,
        update_trader,
        store_invoice,
        store_invoice_line_items,
        get_invoices_for_trader,
        get_recent_invoice_locations,
        check_duplicate_invoice,
        get_invoices_by_gstin_suppliers,
        get_or_create_supplier,
        link_supplier_to_trader,
        get_all_suppliers_for_trader,
        get_all_supplier_gstins,
        update_supplier,
        add_supplier_flag,
        get_active_supplier_flags,
        get_gstr2b_records,
        mark_gstr2b_record_matched,
        upsert_gstr2b_record,
        delete_gstr2b_b2b_record,
        delete_gstr2b_records_for_period,
        get_supplier_by_gstin,
        get_recent_invoices,
        get_itc_summary,
        upload_file,
        resolve_trader_rows,
        get_reports_for_trader,
        upsert_report,
        update_invoice_by_id,
        get_invoice_by_id,
        get_invoice_by_id_for_trader,
        get_traders_by_ids,
        get_invoices_for_traders,
        get_gstr2b_records_for_traders,
    )
else:
    from app.services.supabase_client import (  # noqa: F401
        get_trader_by_phone,
        get_trader_by_short_code,
        get_trader_by_inbound_email,
        get_trader_by_id,
        create_trader,
        update_trader,
        store_invoice,
        store_invoice_line_items,
        get_invoices_for_trader,
        get_recent_invoice_locations,
        check_duplicate_invoice,
        get_invoices_by_gstin_suppliers,
        get_or_create_supplier,
        link_supplier_to_trader,
        get_all_suppliers_for_trader,
        get_all_supplier_gstins,
        update_supplier,
        add_supplier_flag,
        get_active_supplier_flags,
        get_gstr2b_records,
        mark_gstr2b_record_matched,
        upsert_gstr2b_record,
        delete_gstr2b_b2b_record,
        delete_gstr2b_records_for_period,
        get_supplier_by_gstin,
        get_recent_invoices,
        get_itc_summary,
        upload_file,
        resolve_trader_rows,
        get_reports_for_trader,
        upsert_report,
        update_invoice_by_id,
        get_invoice_by_id,
        get_invoice_by_id_for_trader,
        get_traders_by_ids,
        get_invoices_for_traders,
        get_gstr2b_records_for_traders,
    )
