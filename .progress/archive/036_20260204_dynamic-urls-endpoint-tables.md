# 036 - Dynamic URLs + Auto-Generated Endpoint Tables

**Created:** 2026-02-04
**Status:** COMPLETE

## Summary

Replaced hardcoded production URLs throughout the platform with environment-aware
template tokens, and added auto-generation infrastructure for endpoint tables in skill.md.

## What Changed

### Part A: Dynamic Environment-Aware URLs

- Added `NEXT_PUBLIC_SITE_URL` env var to .env.example, .env.vercel.prod, .env.vercel.preview
- Replaced 6 hardcoded URLs in skill.md with `{{SITE_URL}}`, `{{API_URL}}`, `{{API_BASE}}` tokens
- Replaced 3 hardcoded URLs in heartbeat.md with tokens
- Created `platform/lib/template.ts` — shared URL template rendering utility
- Created `platform/app/skill.md/route.ts` — Next.js route handler that renders templates
- Created `platform/app/heartbeat.md/route.ts` — Next.js route handler that renders templates
- Added `render_doc_template()` to FastAPI backend main.py
- Updated `/skill.md`, `/api/skill/version`, `/heartbeat.md` FastAPI endpoints to render templates
- Replaced 5 hardcoded URLs in landing page (page.tsx) with env var constants
- Fixed hardcoded `deepsci.fi` URL in OpenAPI heartbeat tag description

### Part B: Auto-Generate Endpoint Tables

- Added AUTO markers around 10 endpoint table sections in skill.md
- Created `platform/backend/scripts/sync_skill_endpoints.py` script
- Fixed 3 dead doc links (`/api/docs/proposals` → `/docs#/proposals` etc.)

## Verification

- All 7 verification checks passed
- TypeScript type check passes
- No remaining hardcoded production URLs in documentation files

## User Action Required

- Set `NEXT_PUBLIC_SITE_URL` in Vercel dashboard (Production: `https://deep-sci-fi.world`, Preview: `https://staging.deep-sci-fi.world`)
- Set `NEXT_PUBLIC_SITE_URL` and `NEXT_PUBLIC_API_URL` in Railway for both environments
