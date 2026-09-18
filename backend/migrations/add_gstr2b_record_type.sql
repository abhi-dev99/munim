-- Adds the record_type column the GSTR-2B upload path already writes.
--
-- Without this column every upsert in app/api/gstr2b.py raises "column
-- record_type does not exist"; the per-record try/except swallows it, so the
-- endpoint returns 200 with inserted:0 and stores nothing. It also leaves
-- net_credit_notes() (CDNR) and the B2BA amendment preference in
-- app/domain/reconciler.py permanently inert, since every row reads back as
-- the "B2B" default.
--
-- Existing rows predate CDNR/B2BA parsing and are all plain B2B invoices.

ALTER TABLE gstr2b_records
    ADD COLUMN IF NOT EXISTS record_type VARCHAR(10) NOT NULL DEFAULT 'B2B';

CREATE INDEX IF NOT EXISTS idx_gstr2b_record_type
    ON gstr2b_records (trader_id, record_type);
