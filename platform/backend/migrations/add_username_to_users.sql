-- Migration: Add username column to platform_users
-- Run this before deploying the new code

-- Step 1: Add username column (nullable initially)
ALTER TABLE platform_users
ADD COLUMN IF NOT EXISTS username VARCHAR(50);

-- Step 2: Generate usernames for existing users (based on name + random digits)
UPDATE platform_users
SET username = LOWER(
    REGEXP_REPLACE(
        REGEXP_REPLACE(name, '[^a-zA-Z0-9\s-]', '', 'g'),
        '\s+', '-', 'g'
    )
) || '-' || FLOOR(RANDOM() * 9000 + 1000)::TEXT
WHERE username IS NULL;

-- Step 3: Make username non-nullable and unique
ALTER TABLE platform_users
ALTER COLUMN username SET NOT NULL;

-- Step 4: Add unique index
CREATE UNIQUE INDEX IF NOT EXISTS user_username_idx ON platform_users(username);
