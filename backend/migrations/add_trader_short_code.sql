-- Adds a short, human-typeable code per trader, used as the CA identifier
-- in QR-code onboarding deep links (wa.me/<number>?text=JOIN-<short_code>).
--
-- There is no separate CAs table -- a "CA" is just a trader row whose own
-- whatsapp_number other traders reference via their ca_whatsapp_number
-- column (see deps.py:verify_trader_access). short_code lives on traders
-- for the same reason: any trader can act as the CA side of this link.
--
-- Generated lazily by GET /api/v1/dashboard/onboard-link on first request
-- per trader, not backfilled here.

ALTER TABLE traders ADD COLUMN IF NOT EXISTS short_code VARCHAR(10) UNIQUE;

CREATE INDEX IF NOT EXISTS idx_traders_short_code ON traders (short_code);
