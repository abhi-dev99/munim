-- Optional GPS tag for a scanned invoice photo, set only when the trader's
-- device granted location permission and a fix resolved before the native
-- capture screen finished (mobile/components/SteadyCameraCapture.tsx via
-- mobile/modules/bridge.ts -- see mobile/BRIDGE.md). Nullable and additive:
-- every existing invoice, and every upload from a plain browser (no native
-- shell, no GPS), simply has both columns NULL, exactly as before this
-- migration existed.
--
-- Backs the soft "scan location anomaly" signal in
-- backend/app/api/webhook.py (upload_invoice_direct / _check_location_anomaly)
-- -- a geographic centroid-distance check in the same statistical-signal
-- spirit as app/domain/fraud.py's six signals, kept out of FraudScorer's
-- weighted score on purpose (see that function's comment for why).
--
-- Until this is applied, upload_invoice_direct still works exactly as
-- before for every scan -- latitude/longitude are only added to the insert
-- dict when a scan actually carries them, so a scan with no location is
-- completely unaffected. A scan that *does* carry coordinates will fail to
-- store (store_invoice() logs and returns None, same as any other
-- schema-drift write CLAUDE.md documents) until this migration is applied.

ALTER TABLE invoices ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;
