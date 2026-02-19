# PROP-017: Render Dweller Portrait Images

## Problem
Dweller portraits were backfilled (50/50 dwellers have `portrait_url` in DB, API returns valid R2 URLs), but the frontend renders letter-initial avatars everywhere except the feed. Two pages need fixes.

## What to Fix

### 1. Dweller Detail Page (`platform/app/dweller/[id]/page.tsx`)
- The `DwellerData` interface (line ~8) does NOT include `portrait_url`
- Add `portrait_url?: string | null` to the dweller interface
- Line ~92: Replace the letter-initial div with an image when `portrait_url` exists:
  - If `portrait_url`: render `<img>` with the URL, same dimensions (w-14 h-14), rounded or matching current style, with `onError` fallback to the letter initial
  - If no `portrait_url`: keep current letter-initial fallback

### 2. World Page Dweller List (`platform/app/world/[id]/page.tsx`)
- The dweller type at line ~149 does NOT include `portrait_url`
- Add `portrait_url?: string | null` to the array type
- Find where dwellers are rendered in the DWELLERS tab — add portrait image with same pattern (image with fallback to letter initial)

### Reference Implementation
The feed already does this correctly in `platform/components/feed/FeedContainer.tsx` lines 215-250 — `DwellerAvatar` component with `portrait_url`, `imgError` state, and fallback. You can extract this into a shared component or duplicate the pattern.

## Requirements
- Use Next.js `<Image>` or plain `<img>` — either is fine, but handle loading errors gracefully
- Keep the existing letter-initial as fallback (not all dwellers may have portraits)
- Match the existing visual style (border, size, colors)
- Portrait images should be square, matching the current avatar dimensions on each page

## Verification
- Run `npx tsc --noEmit` — must pass
- Run Rodney screenshots:
  - `rodney start && rodney open "https://deep-sci-fi.world/dweller/40644a4c-12d5-4084-86ad-1c7cd39a1642" && sleep 3 && rodney screenshot dweller-detail.png`
  - `rodney open "https://deep-sci-fi.world/world/8a506aa1-fc8e-48a8-8ce9-9a79caeafd1b" && sleep 3 && rodney screenshot world-dwellers.png`
- Confirm portrait images are visible, not letter initials

## Showboat
Use showboat to document the work:
- `showboat init reports/PROP-017-complete.md "PROP-017: Dweller Portrait Rendering"`
- `showboat note reports/PROP-017-complete.md "What changed"`
- `showboat image reports/PROP-017-complete.md '![screenshot](path)'` for Rodney screenshots
