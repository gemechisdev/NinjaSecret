import os
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

# Setup logging
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize Supabase client
supabase_url = os.environ.get("SUPABASE_URL")
# Use SERVICE_ROLE_KEY for backend operations to bypass RLS
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    logger.warning(
        "Missing Supabase credentials. Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables.")
    supabase = None
else:
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        supabase = None

# SQL for creating the tables in Supabase
"""
-- Run this in the Supabase SQL editor to create your tables

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS public.users (
    id BIGINT PRIMARY KEY,
    target_user JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Whispers table  
CREATE TABLE IF NOT EXISTS public.whispers (
    inline_message_id VARCHAR PRIMARY KEY,
    message TEXT NOT NULL,
    sender_id BIGINT REFERENCES public.users(id),
    recipient_ids BIGINT[] NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '7 days')
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_users_target ON public.users USING GIN (target_user);
CREATE INDEX IF NOT EXISTS idx_whispers_sender ON public.whispers (sender_id);
CREATE INDEX IF NOT EXISTS idx_whispers_expires ON public.whispers (expires_at);
CREATE INDEX IF NOT EXISTS idx_whispers_recipients ON public.whispers USING GIN (recipient_ids);

-- Updated at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to users table
DROP TRIGGER IF EXISTS update_users_updated_at ON public.users;
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON public.users 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whispers ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Service role can do everything on users" ON public.users;
DROP POLICY IF EXISTS "Service role can do everything on whispers" ON public.whispers;

-- RLS Policies for service role (allows all operations)
CREATE POLICY "Service role can do everything on users" 
ON public.users FOR ALL 
TO service_role 
USING (true) 
WITH CHECK (true);

CREATE POLICY "Service role can do everything on whispers" 
ON public.whispers FOR ALL 
TO service_role 
USING (true) 
WITH CHECK (true);

-- Allow anon role to read for public access if needed
CREATE POLICY "Allow anon read users" 
ON public.users FOR SELECT 
TO anon 
USING (true);

CREATE POLICY "Allow anon read whispers" 
ON public.whispers FOR SELECT 
TO anon 
USING (true);

-- Function to cleanup expired whispers
CREATE OR REPLACE FUNCTION cleanup_expired_whispers()
RETURNS void AS $$
BEGIN
    DELETE FROM public.whispers WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission on cleanup function
GRANT EXECUTE ON FUNCTION cleanup_expired_whispers() TO service_role;

-- Schedule cleanup (requires pg_cron extension - enable in Supabase extensions)
-- SELECT cron.schedule('cleanup-whispers', '0 0 * * *', 'SELECT cleanup_expired_whispers();');
"""
