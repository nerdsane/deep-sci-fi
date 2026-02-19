# Dweller image_prompt field (PROP-010 follow-up)

*2026-02-17T23:45:19Z by Showboat 0.6.0*
<!-- showboat-id: 8d225817-8e1d-47ed-9ab4-3950d080b434 -->

Implementing image_prompt support for dwellers. Pattern: 4 changes needed:
1. Migration 0021_add_image_prompt_to_dwellers.py
2. models.py: add image_prompt field to Dweller
3. dwellers.py: add image_prompt to DwellerCreateRequest + pass through background task
4. art_generation.py: accept optional image_prompt param, skip Anthropic call if provided

Implementation complete. All 4 files changed:
- 0021_add_image_prompt_to_dwellers.py: idempotent migration adding nullable Text column
- models.py: image_prompt field added to Dweller after portrait_url
- dwellers.py: DwellerCreateRequest.image_prompt field + propagated through _generate_portrait_background
- art_generation.py: if image_prompt provided, use directly; else fall back to Anthropic Claude Haiku
