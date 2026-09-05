-- Add inbound_email to traders
ALTER TABLE traders ADD COLUMN inbound_email VARCHAR(255) UNIQUE;

-- Create an index for fast lookups
CREATE INDEX IF NOT EXISTS traders_inbound_email_idx ON traders(inbound_email);
