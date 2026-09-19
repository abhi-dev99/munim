-- Whether this trader is registered under the GST Composition Scheme.
-- Composition dealers cannot claim input tax credit at all, so this flag
-- gates the ITC display (MoneyMeter) for the CA's client list. Previously
-- this was a dashboard-header toggle with no backing column -- it flipped
-- local React state that reverted on every reload/trader switch, so it
-- never actually persisted anything. Moved to a per-client toggle on the
-- CA's profile/client-list page, backed by this real column.

ALTER TABLE traders ADD COLUMN IF NOT EXISTS is_composition BOOLEAN NOT NULL DEFAULT FALSE;
