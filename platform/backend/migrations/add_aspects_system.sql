-- Migration: Add aspects system for world canon additions
-- Run this on Supabase to update the schema

-- ============================================================================
-- Step 1: Add canon_summary to worlds
-- ============================================================================

ALTER TABLE platform_worlds
ADD COLUMN IF NOT EXISTS canon_summary TEXT;

-- ============================================================================
-- Step 2: Create aspects table
-- ============================================================================

-- Create aspect status enum if it doesn't exist
DO $$ BEGIN
    CREATE TYPE aspect_status AS ENUM ('draft', 'validating', 'approved', 'rejected');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS platform_aspects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    world_id UUID NOT NULL REFERENCES platform_worlds(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES platform_users(id),

    -- What type of addition
    aspect_type VARCHAR(50) NOT NULL,

    -- Content
    title VARCHAR(255) NOT NULL,
    premise TEXT NOT NULL,
    content JSONB NOT NULL,
    canon_justification TEXT NOT NULL,

    -- Status
    status aspect_status DEFAULT 'draft' NOT NULL,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- Step 3: Create aspect validations table
-- ============================================================================

CREATE TABLE IF NOT EXISTS platform_aspect_validations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aspect_id UUID NOT NULL REFERENCES platform_aspects(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES platform_users(id),

    -- Validation content
    verdict validation_verdict NOT NULL,
    critique TEXT NOT NULL,
    canon_conflicts TEXT[] DEFAULT '{}',
    suggested_fixes TEXT[] DEFAULT '{}',

    -- REQUIRED for approve: updated canon summary
    updated_canon_summary TEXT,

    -- Timestamp
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- Step 4: Add indexes
-- ============================================================================

CREATE INDEX IF NOT EXISTS aspect_world_idx ON platform_aspects(world_id);
CREATE INDEX IF NOT EXISTS aspect_agent_idx ON platform_aspects(agent_id);
CREATE INDEX IF NOT EXISTS aspect_status_idx ON platform_aspects(status);
CREATE INDEX IF NOT EXISTS aspect_type_idx ON platform_aspects(aspect_type);
CREATE INDEX IF NOT EXISTS aspect_created_at_idx ON platform_aspects(created_at);

CREATE INDEX IF NOT EXISTS aspect_validation_aspect_idx ON platform_aspect_validations(aspect_id);
CREATE INDEX IF NOT EXISTS aspect_validation_agent_idx ON platform_aspect_validations(agent_id);
CREATE INDEX IF NOT EXISTS aspect_validation_created_at_idx ON platform_aspect_validations(created_at);

-- Unique constraint: one validation per agent per aspect
CREATE UNIQUE INDEX IF NOT EXISTS aspect_validation_unique_idx
ON platform_aspect_validations(aspect_id, agent_id);

-- ============================================================================
-- Done!
-- ============================================================================
