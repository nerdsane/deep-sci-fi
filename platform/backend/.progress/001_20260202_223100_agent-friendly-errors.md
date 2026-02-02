# Agent-Friendly API Error Improvements

## Task
Make all API endpoints agent-friendly with clear, actionable error messages that help agents understand what went wrong and how to fix it.

## Issues Found

### 1. Social Endpoints Missing Target Validation
- `/api/social/react`, `/api/social/follow`, `/api/social/comment` don't check if target exists
- Results in confusing database errors or silent failures

### 2. Error Messages Not Actionable
- Errors should include "how to fix" guidance
- Should include relevant context (available options, correct format, etc.)

### 3. No Global Error Handling
- Database constraint errors return raw SQLAlchemy errors
- Need to catch and translate to agent-friendly messages

## Implementation Plan

### Phase 1: Fix Social Endpoints
- [x] Add target existence validation to react endpoint
- [x] Add target existence validation to follow endpoint
- [x] Add target existence validation to comment endpoint

### Phase 2: Improve Error Messages
- [x] Add actionable suggestions to key errors
- [x] Include context in errors (available values, expected format)

### Phase 3: Global Error Handler
- [x] Add exception handler for database errors
- [x] Add exception handler for validation errors
- [x] Standardize error response format

## Status: Complete
