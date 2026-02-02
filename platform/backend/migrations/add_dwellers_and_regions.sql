-- Migration: Add dweller inhabitation system and world regions
-- Run this on Supabase to update the schema

-- ============================================================================
-- Step 1: Add regions column to worlds
-- ============================================================================

ALTER TABLE platform_worlds
ADD COLUMN IF NOT EXISTS regions JSONB DEFAULT '[]'::jsonb;

-- ============================================================================
-- Step 2: Update dwellers table with new columns
-- ============================================================================

-- Add new columns if they don't exist
DO $$ BEGIN
    -- created_by (who created the persona)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'platform_dwellers' AND column_name = 'created_by') THEN
        ALTER TABLE platform_dwellers ADD COLUMN created_by UUID REFERENCES platform_users(id);
    END IF;

    -- inhabited_by (who's controlling it)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'platform_dwellers' AND column_name = 'inhabited_by') THEN
        ALTER TABLE platform_dwellers ADD COLUMN inhabited_by UUID REFERENCES platform_users(id);
    END IF;

    -- Identity fields
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'platform_dwellers' AND column_name = 'name') THEN
        ALTER TABLE platform_dwellers ADD COLUMN name VARCHAR(100);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'platform_dwellers' AND column_name = 'origin_region') THEN
        ALTER TABLE platform_dwellers ADD COLUMN origin_region VARCHAR(100);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'platform_dwellers' AND column_name = 'generation') THEN
        ALTER TABLE platform_dwellers ADD COLUMN generation VARCHAR(50);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'platform_dwellers' AND column_name = 'name_context') THEN
        ALTER TABLE platform_dwellers ADD COLUMN name_context TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'platform_dwellers' AND column_name = 'cultural_identity') THEN
        ALTER TABLE platform_dwellers ADD COLUMN cultural_identity TEXT;
    END IF;

    -- Character fields
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'platform_dwellers' AND column_name = 'role') THEN
        ALTER TABLE platform_dwellers ADD COLUMN role VARCHAR(255);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'platform_dwellers' AND column_name = 'age') THEN
        ALTER TABLE platform_dwellers ADD COLUMN age INTEGER;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'platform_dwellers' AND column_name = 'personality') THEN
        ALTER TABLE platform_dwellers ADD COLUMN personality TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'platform_dwellers' AND column_name = 'background') THEN
        ALTER TABLE platform_dwellers ADD COLUMN background TEXT;
    END IF;

    -- State fields
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'platform_dwellers' AND column_name = 'current_situation') THEN
        ALTER TABLE platform_dwellers ADD COLUMN current_situation TEXT DEFAULT '';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'platform_dwellers' AND column_name = 'recent_memories') THEN
        ALTER TABLE platform_dwellers ADD COLUMN recent_memories JSONB DEFAULT '[]'::jsonb;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'platform_dwellers' AND column_name = 'relationships') THEN
        ALTER TABLE platform_dwellers ADD COLUMN relationships JSONB DEFAULT '{}'::jsonb;
    END IF;

    -- Meta fields
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'platform_dwellers' AND column_name = 'is_available') THEN
        ALTER TABLE platform_dwellers ADD COLUMN is_available BOOLEAN DEFAULT TRUE;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'platform_dwellers' AND column_name = 'updated_at') THEN
        ALTER TABLE platform_dwellers ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();
    END IF;
END $$;

-- Rename old columns if they exist (graceful migration)
DO $$ BEGIN
    -- If agent_id exists but created_by doesn't have data, copy over
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'platform_dwellers' AND column_name = 'agent_id') THEN
        UPDATE platform_dwellers SET created_by = agent_id WHERE created_by IS NULL AND agent_id IS NOT NULL;
    END IF;

    -- If joined_at exists but created_at doesn't, rename
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'platform_dwellers' AND column_name = 'joined_at')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'platform_dwellers' AND column_name = 'created_at') THEN
        ALTER TABLE platform_dwellers RENAME COLUMN joined_at TO created_at;
    END IF;
END $$;

-- ============================================================================
-- Step 3: Create dweller_actions table
-- ============================================================================

CREATE TABLE IF NOT EXISTS platform_dweller_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dweller_id UUID NOT NULL REFERENCES platform_dwellers(id) ON DELETE CASCADE,
    actor_id UUID NOT NULL REFERENCES platform_users(id),
    action_type VARCHAR(50) NOT NULL,
    target VARCHAR(255),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- Step 4: Add indexes
-- ============================================================================

CREATE INDEX IF NOT EXISTS dweller_created_by_idx ON platform_dwellers(created_by);
CREATE INDEX IF NOT EXISTS dweller_inhabited_by_idx ON platform_dwellers(inhabited_by);
CREATE INDEX IF NOT EXISTS dweller_available_idx ON platform_dwellers(is_available);

CREATE INDEX IF NOT EXISTS action_dweller_idx ON platform_dweller_actions(dweller_id);
CREATE INDEX IF NOT EXISTS action_actor_idx ON platform_dweller_actions(actor_id);
CREATE INDEX IF NOT EXISTS action_created_at_idx ON platform_dweller_actions(created_at);
CREATE INDEX IF NOT EXISTS action_type_idx ON platform_dweller_actions(action_type);

-- ============================================================================
-- Done!
-- ============================================================================
