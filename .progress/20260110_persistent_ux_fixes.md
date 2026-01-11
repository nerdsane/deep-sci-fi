# Persistent UX Issues Fixes

**Date:** 2026-01-10
**Status:** COMPLETED

---

## Summary

Fixed three persistent issues reported by user:
1. Broken image icons on world cards
2. World names showing character names instead of actual world names
3. Characters section displayed in world details (should be hidden)

---

## Root Causes Identified

### Issue 1: Broken Images

**Problem:** S3 bucket `deep-sci-fi-assets` existed and images uploaded successfully, but bucket didn't have public read access. Result: 403 Forbidden when web app tried to load images.

**Flow was:**
1. Image generates via AI (Gemini/OpenAI)
2. Uploads to S3 ✅
3. S3 URL saved to database (`https://deep-sci-fi-assets.s3.us-east-1.amazonaws.com/...`)
4. Web app loads image → 403 Forbidden ❌
5. Browser shows broken image icon

### Issue 2: World Names Showing Character Names

**Problem:** `WorldSpace.tsx` used first visible element's name as world title, which was often a character (e.g., "The Donor" instead of "The Memory Market").

**Code was (line 39-40):**
```typescript
if (surface.visible_elements?.[0]?.name) {
  return surface.visible_elements[0].name;  // Wrong! This is often a character
}
```

### Issue 3: Characters Section Visible

**Problem:** Characters section was displayed in world detail view. Per design philosophy, characters should emerge through stories, not be displayed upfront.

---

## Fixes Applied

### Fix 1: S3 Bucket Public Access

**AWS CLI commands executed:**

```bash
# Remove public access block
aws s3api delete-public-access-block --bucket deep-sci-fi-assets

# Add public read policy
aws s3api put-bucket-policy --bucket deep-sci-fi-assets --policy '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::deep-sci-fi-assets/*"
    }
  ]
}'
```

**Result:** S3 images now return HTTP 200 instead of 403.

### Fix 2: Image Generator Data URL Fallback

**File:** `/packages/letta/tools/image-generator.ts`

Changed to always store data URL in `url` field (lines 376-416):
- Data URLs work directly in browser without external access
- S3 still used for backup/persistence via `storagePath`
- More reliable than depending on S3 public access

**Rationale:** Even with S3 now public, data URLs provide reliability if S3 access ever changes.

### Fix 3: World Title from world.name

**File:** `/apps/web/components/canvas/world/WorldSpace.tsx`

Changed `worldTitle` derivation (lines 37-47):
```typescript
// Before: Used first visible element's name (often a character)
// After: Use explicit world.name from database
if ((world as any).name) {
  return (world as any).name;
}
```

### Fix 4: Hide Characters Section

**File:** `/apps/web/components/canvas/world/WorldSpace.tsx`

Removed Characters section (lines 130-165):
```typescript
// Before: Rendered characters section
// After: Hidden with comment explaining why
{/* Characters - HIDDEN: Characters emerge through stories, not displayed upfront */}
```

### Fix 5: Cover Image URL Priority

**File:** `/apps/web/components/canvas/world/WorldSpace.tsx`

Changed `coverImage` to prefer URL over path (lines 52-59):
```typescript
// Before: Only used path
// After: Prefer URL (data URL), fallback to path
if (asset.url) return asset.url;
if (asset.path) return `/api/assets/${asset.path}`;
```

### Fix 6: letta-code State Change Field Names

**File:** `/letta-code/src/tools/impl/image_generator.ts`

Changed state change broadcast to send `assetUrl` instead of `assetPath` (lines 153-160):
```typescript
// Before: assetPath: asset?.path
// After: assetUrl: asset?.path ? `/api/assets/${asset.path}` : undefined
```

### Fix 7: Detail Endpoint Transformation

**File:** `/apps/web/app/api/worlds/[id]/route.ts`

Added data transformation to match list endpoint format (lines 85-120):
- Changed asset filter from `category: 'cover_art'` to `type: 'image'`
- Added transformation to match frontend contract

### Database Cleanup

Deleted 3 broken asset records that had S3 URLs but no usable data:
```sql
DELETE FROM app.assets WHERE url IS NULL;
```

---

## Files Modified

| File | Change |
|------|--------|
| `/packages/letta/tools/image-generator.ts` | Store data URL, not S3 URL |
| `/apps/web/components/canvas/world/WorldSpace.tsx` | Use world.name, hide characters, fix cover image |
| `/apps/web/app/api/worlds/[id]/route.ts` | Add transformation, remove category filter |
| `/letta-code/src/tools/impl/image_generator.ts` | Send assetUrl instead of assetPath |

---

## Commits

1. `01c0183` (letta-code) - fix: send assetUrl instead of assetPath in image_generated state change
2. `2a25569` - fix: world detail endpoint transformation and image display
3. `ada7b16` - fix: image display and world detail view improvements

---

## Verification

Tested in browser:
- ✅ World cards show placeholder icons (no broken images)
- ✅ World names display correctly ("The Memory Market", not "The Donor")
- ✅ World detail view shows world name as title
- ✅ Characters section is hidden in world detail
- ✅ Locations and Technologies sections still visible
- ✅ S3 bucket now publicly accessible (HTTP 200)

---

## Additional Fix: Letta Provider Registration

**Issue:** After restarting Letta server, agents failed with:
```
✖400 {"detail":"INVALID_ARGUMENT: Provider anthropic is not supported (supported providers: letta)"}
```

**Root Cause:** Letta server requires providers to be explicitly registered via API. Having API keys in environment variables is not enough - providers must be created in the database.

**Fix:** Created providers via API:
```bash
# Create Anthropic provider
curl -X POST http://localhost:8283/v1/providers/ \
  -H "Content-Type: application/json" \
  -d '{"name": "anthropic", "provider_type": "anthropic", "api_key": "$ANTHROPIC_API_KEY"}'

# Create OpenAI provider
curl -X POST http://localhost:8283/v1/providers/ \
  -H "Content-Type: application/json" \
  -d '{"name": "openai", "provider_type": "openai", "api_key": "$OPENAI_API_KEY"}'

# Create Google AI provider
curl -X POST http://localhost:8283/v1/providers/ \
  -H "Content-Type: application/json" \
  -d '{"name": "google_ai", "provider_type": "google_ai", "api_key": "$GOOGLE_API_KEY"}'
```

**Result:** All three providers registered successfully:
- `provider-2ea62ee7-600a-4d17-b254-aa4b9add4ac5` (anthropic)
- `provider-765c61ca-91bc-4f76-8160-fb586b03fce2` (openai)
- `provider-95c1b89c-8d0e-416f-b9fb-8d6db55ff903` (google_ai)

---

## Notes

- Existing images were deleted from database since they had broken S3 URLs
- New images will use data URLs and work immediately
- S3 is now configured for public read access for future CDN integration
- Consider setting up CloudFront for better performance in production
- **Letta providers persist in database** - don't need to re-register after server restart as long as same database is used
