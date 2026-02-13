# 050 - ClawHub Submission Research

**Created**: 2026-02-10
**Status**: Complete
**Type**: Research

## Goal

Research how to submit/publish a plugin to ClawHub (clawhub.ai), the OpenClaw community registry.

## Key Findings

### 1. ClawHub is for SKILLS, not plugins

ClawHub is exclusively a **skill registry**. Skills are text-based instruction bundles (SKILL.md + supporting files) that teach agents how to use tools. Plugins are code modules distributed via **npm**.

### 2. Two separate distribution channels exist

- **Skills** -> ClawHub (clawhub.ai) via `clawhub publish`
- **Plugins** -> npm registry via `npm publish`, installed via `openclaw plugins install`

### 3. Your logfire-observability is a PLUGIN, not a skill

It has `openclaw.plugin.json`, exports a `register()` function, uses TypeScript. This is a plugin distributed via npm, not a ClawHub skill.

### 4. However, plugins CAN bundle skills

A plugin can ship a SKILL.md in a `skills/` directory. The skill would appear on ClawHub while the plugin code lives on npm.

### 5. To publish the plugin to npm

- Publish under `@openclaw/*` namespace or your own scope
- Ensure `package.json` has `openclaw.extensions` field
- Users install via `openclaw plugins install <npm-spec>`

### 6. To additionally list on ClawHub

- Create a companion SKILL.md with metadata pointing to the npm plugin
- Use `clawhub publish` to register the skill entry
- The SKILL.md metadata can reference the nix/npm plugin

## Sources

- https://docs.openclaw.ai/tools/clawhub
- https://docs.openclaw.ai/tools/plugin
- https://docs.openclaw.ai/tools/skills
- https://github.com/openclaw/clawhub
- https://deepwiki.com/openclaw/openclaw/10.3-creating-custom-plugins
- https://github.com/henrikrexed/openclaw-observability-plugin
