-- Adds three invoice columns the application code already writes but that
-- exist in no schema file and no prior migration.
--
-- credit_note_applied / credit_note_reason: the credit-note netting loop in
-- app/api/gstr2b.py:trigger_reconciliation() writes both on every CDNR match.
-- Without them the update raises "column ... does not exist", the per-update
-- try/except swallows it, and the ITC reduction is never persisted either —
-- the whole update statement fails, itc_amount_eligible included. So a CDNR
-- that should cut a trader's claimed ITC silently does nothing.
--
-- last_vendor_notified_at: app/api/communications.py stamps it after every
-- vendor email/WhatsApp warning and reads it in _check_rate_limit() for the
-- 7-day VENDOR_ALERT_COOLDOWN_DAYS window. The stamp fails into a logged
-- warning and the read returns None, so the cooldown has never once fired —
-- every re-run of reconciliation with auto_warn_vendors on can re-mail the
-- same supplier about the same invoice.
--
-- Existing rows predate all three: no credit note was ever netted and no
-- vendor warning was ever recorded, so the defaults below are correct.

ALTER TABLE invoices
    ADD COLUMN IF NOT EXISTS credit_note_applied BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE invoices
    ADD COLUMN IF NOT EXISTS credit_note_reason TEXT;

ALTER TABLE invoices
    ADD COLUMN IF NOT EXISTS last_vendor_notified_at TIMESTAMPTZ;
