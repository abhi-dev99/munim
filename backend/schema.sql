-- =====================================================
-- Munim.ai — Supabase Database Schema
-- Run this in Supabase SQL Editor to set up all tables.
-- =====================================================

-- Enable pgvector for HSN semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- =====================================================
-- TRADERS (primary users)
-- =====================================================
CREATE TABLE IF NOT EXISTS traders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    whatsapp_number VARCHAR(15) UNIQUE NOT NULL,
    name VARCHAR(255),
    gstin VARCHAR(15) UNIQUE,
    business_name VARCHAR(255),
    language_pref VARCHAR(10) DEFAULT 'hi',
    ca_whatsapp_number VARCHAR(15),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- SUPPLIERS (unique per GSTIN, shared across traders)
-- =====================================================
CREATE TABLE IF NOT EXISTS suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gstin VARCHAR(15) UNIQUE NOT NULL,
    legal_name VARCHAR(255),
    trade_name VARCHAR(255),
    taxpayer_type VARCHAR(50),
    registration_date DATE,
    business_category VARCHAR(255),
    is_einvoice_mandated BOOLEAN DEFAULT FALSE,
    health_score INTEGER DEFAULT 100,
    last_verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- SUPPLIER-TRADER LINKS (the compliance graph)
-- =====================================================
CREATE TABLE IF NOT EXISTS supplier_trader_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trader_id UUID REFERENCES traders(id) ON DELETE CASCADE,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE CASCADE,
    first_invoice_date DATE,
    last_invoice_date DATE,
    total_invoice_count INTEGER DEFAULT 0,
    total_itc_claimed DECIMAL(15,2) DEFAULT 0,
    UNIQUE(trader_id, supplier_id)
);

-- =====================================================
-- SUPPLIER BEHAVIORAL FLAGS
-- =====================================================
CREATE TABLE IF NOT EXISTS supplier_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id UUID REFERENCES suppliers(id) ON DELETE CASCADE,
    flag_type VARCHAR(50) NOT NULL,
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE
);

-- =====================================================
-- PROCESSED INVOICES
-- =====================================================
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trader_id UUID REFERENCES traders(id) ON DELETE CASCADE,
    supplier_id UUID REFERENCES suppliers(id),

    -- Raw data
    image_url TEXT,
    raw_ocr_text TEXT,

    -- Extracted fields
    invoice_number VARCHAR(100),
    invoice_date DATE,
    gstin_supplier VARCHAR(15),
    gstin_buyer VARCHAR(15),
    supplier_name VARCHAR(255),   -- Extracted from invoice / GSTIN lookup

    -- Financial
    taxable_amount DECIMAL(15,2),
    cgst_amount DECIMAL(15,2),
    sgst_amount DECIMAL(15,2),
    igst_amount DECIMAL(15,2),
    total_amount DECIMAL(15,2),

    -- Validation status
    status VARCHAR(50) DEFAULT 'pending',
    itc_status VARCHAR(50),
    itc_amount_eligible DECIMAL(15,2),
    itc_amount_blocked DECIMAL(15,2),
    itc_block_reason TEXT,

    -- Reconciliation
    gstr2b_match_status VARCHAR(50),
    gstr2b_match_confidence DECIMAL(5,2),

    -- Fraud scoring
    fraud_score INTEGER DEFAULT 0,
    fraud_signals JSONB,

    -- Hash for duplicate detection
    invoice_hash VARCHAR(64) UNIQUE,

    -- Processing metadata
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    processing_duration_ms INTEGER,
    langgraph_run_id VARCHAR(100),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast historical lookup per supplier (used by fraud scorer)
CREATE INDEX IF NOT EXISTS invoices_gstin_supplier_idx ON invoices(gstin_supplier);

-- =====================================================
-- INVOICE LINE ITEMS
-- =====================================================
CREATE TABLE IF NOT EXISTS invoice_line_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID REFERENCES invoices(id) ON DELETE CASCADE,
    description TEXT,
    hsn_code_extracted VARCHAR(10),
    hsn_code_validated VARCHAR(10),
    hsn_is_valid BOOLEAN,
    hsn_suggestion VARCHAR(10),
    hsn_confidence DECIMAL(5,2),
    quantity DECIMAL(15,3),
    unit VARCHAR(20),
    unit_price DECIMAL(15,2),
    taxable_value DECIMAL(15,2),
    tax_rate_applied DECIMAL(5,2),
    tax_rate_correct DECIMAL(5,2),
    rate_mismatch BOOLEAN DEFAULT FALSE,
    itc_delta DECIMAL(15,2)
);

-- =====================================================
-- HSN MASTER TABLE (12,167 codes + pgvector embeddings)
-- =====================================================
CREATE TABLE IF NOT EXISTS hsn_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hsn_code VARCHAR(10) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    description_hindi TEXT,
    gst_rate DECIMAL(5,2) NOT NULL,
    category VARCHAR(100),
    section VARCHAR(100),
    embedding vector(768)  -- Gemini text-embedding-004 dimension
);

-- HNSW index for fast approximate nearest neighbour search
CREATE INDEX IF NOT EXISTS hsn_embedding_idx ON hsn_codes
USING hnsw (embedding vector_cosine_ops);

-- =====================================================
-- GSTR-2B IMPORTS (monthly uploads / dummy for demo)
-- =====================================================
CREATE TABLE IF NOT EXISTS gstr2b_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trader_id UUID REFERENCES traders(id) ON DELETE CASCADE,
    month INTEGER NOT NULL,
    year INTEGER NOT NULL,
    supplier_gstin VARCHAR(15),
    invoice_number VARCHAR(100),
    invoice_date DATE,
    taxable_value DECIMAL(15,2),
    igst DECIMAL(15,2) DEFAULT 0,
    cgst DECIMAL(15,2) DEFAULT 0,
    sgst DECIMAL(15,2) DEFAULT 0,
    itc_eligible BOOLEAN DEFAULT TRUE,
    matched_invoice_id UUID REFERENCES invoices(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(trader_id, month, year, supplier_gstin, invoice_number)
);

-- =====================================================
-- MUNIM REPORTS (monthly PDF)
-- =====================================================
CREATE TABLE IF NOT EXISTS munim_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trader_id UUID REFERENCES traders(id) ON DELETE CASCADE,
    month INTEGER NOT NULL,
    year INTEGER NOT NULL,
    pdf_url TEXT,
    total_invoices_processed INTEGER,
    total_itc_confirmed DECIMAL(15,2),
    total_itc_blocked DECIMAL(15,2),
    total_itc_at_risk DECIMAL(15,2),
    total_itc_missed DECIMAL(15,2),
    total_itc_ineligible DECIMAL(15,2),
    total_issues_count INTEGER,
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    delivered_to_trader_at TIMESTAMPTZ,
    delivered_to_ca_at TIMESTAMPTZ,
    UNIQUE(trader_id, month, year)
);

-- =====================================================
-- CONVERSATION STATES (Redis-backed, DB for persistence)
-- =====================================================
CREATE TABLE IF NOT EXISTS conversation_states (
    trader_id UUID REFERENCES traders(id) ON DELETE CASCADE PRIMARY KEY,
    state VARCHAR(50) DEFAULT 'idle',
    current_invoice_id UUID REFERENCES invoices(id),
    context JSONB DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- AUDIT LOG
-- =====================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trader_id UUID REFERENCES traders(id),
    event_type VARCHAR(100),
    event_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- FUNCTION: pgvector HSN semantic search
-- Used by HSN validator for nearest-neighbour matching
-- =====================================================
CREATE OR REPLACE FUNCTION match_hsn_codes(
    query_embedding vector(768),
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 3
)
RETURNS TABLE (
    hsn_code VARCHAR(10),
    description TEXT,
    gst_rate DECIMAL(5,2),
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        h.hsn_code,
        h.description,
        h.gst_rate,
        1 - (h.embedding <=> query_embedding) AS similarity
    FROM hsn_codes h
    WHERE
        h.embedding IS NOT NULL
        AND 1 - (h.embedding <=> query_embedding) > match_threshold
    ORDER BY h.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- =====================================================
-- ROW LEVEL SECURITY (RLS) — basic setup
-- =====================================================
ALTER TABLE traders ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE suppliers ENABLE ROW LEVEL SECURITY;

-- Allow service role full access (backend uses service role key)
CREATE POLICY "Service role has full access to traders"
    ON traders FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role has full access to invoices"
    ON invoices FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role has full access to suppliers"
    ON suppliers FOR ALL
    USING (true)
    WITH CHECK (true);

-- =====================================================
-- STORAGE BUCKETS (run in Supabase dashboard)
-- =====================================================
-- Create these buckets manually in Supabase Dashboard > Storage:
-- 1. "invoices" — for uploaded invoice images
-- 2. "reports"  — for generated Munim Report PDFs
