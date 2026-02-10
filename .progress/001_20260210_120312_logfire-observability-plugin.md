# Logfire Observability Plugin for OpenClaw

## Task
Extract the `deep-trace` plugin from the OpenClaw EC2 instance, rewrite it as a fully self-contained `logfire-observability` plugin with its own OTLP exporter, and place it in the deep-sci-fi repo for others to use.

## Status: COMPLETE

## Context
- Source: `ubuntu@100.89.85.18:~/.clawdbot/extensions/deep-trace/`
- Problem: Original `deep-trace` depends on `diagnostics-otel` for OTLP export, but module isolation means spans never actually reach Logfire (all-zero span/trace IDs)
- Solution: Self-contained plugin with bundled OTLP exporter

## Plan

### Phase 1: Create plugin structure
- [x] Create `openclaw-plugins/logfire-observability/` in deep-sci-fi repo
- [x] Write `package.json` with all OTel dependencies
- [x] Write `openclaw.plugin.json` manifest
- [x] Write `index.ts` with self-contained OTLP exporter + lifecycle hooks
- [x] Write `README.md` with setup instructions

### Phase 2: Review & fix
- [x] Code review found: tool spans not parented under agent.run (flat, not nested)
- [x] Fixed: pass parent OTel context to tracer.startSpan() for child spans
- [x] Fixed: use Map<toolCallId, Span> for parallel tool safety (+ LIFO fallback)
- [x] Added tsconfig.json for IDE support
- [x] Added .gitignore for node_modules
- [x] Verified all OTel dependency versions compatible

## Key Design Decisions
- Bundle own TracerProvider (not relying on global OTel state)
- Use BatchSpanProcessor for performance
- Logfire token goes in plugin config (not separate diagnostics section)
- Service name configurable, defaults to "openclaw"
