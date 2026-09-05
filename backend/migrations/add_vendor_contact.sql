-- Migration: Add vendor contact info and CA preferences for automated warnings

-- 1. Add supplier_email and supplier_phone to invoices table
ALTER TABLE public.invoices
ADD COLUMN supplier_email text,
ADD COLUMN supplier_phone text;

-- 2. Add auto_warn_vendors preference to traders table (assuming traders table acts as user profile)
ALTER TABLE public.traders
ADD COLUMN auto_warn_vendors boolean DEFAULT false;
