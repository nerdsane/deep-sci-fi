# UX & Styling Philosophy

**Type:** STABLE
**Created:** 2026-01-09
**Last Updated:** 2026-01-09

---

## Overview

Deep Sci-Fi's interface should feel like an extension of the worlds being created - thoughtful, immersive, and focused on content over chrome. This document defines the UX philosophy and aesthetic outcomes to achieve.

---

## Core Principles

### 1. Immersive Over Utilitarian

The UI should feel like part of the sci-fi world, not a generic app.

**Outcomes:**
- Content is the hero, not the interface
- Transitions feel natural and unobtrusive
- Visual design evokes thoughtful exploration

**Anti-patterns:**
- Flashy animations that distract from content
- Generic SaaS dashboard aesthetics
- Over-designed empty states

### 2. Progressive Disclosure

Show only what's needed for the current task.

**Outcomes:**
- New users aren't overwhelmed
- Complexity reveals itself as users go deeper
- Each screen has a clear primary action

**Anti-patterns:**
- All options visible at once
- Dense dashboards with everything accessible
- Forcing users through wizards for simple tasks

### 3. Agent as Collaborator, Not Tool

The AI feels like a creative partner, not a command interface.

**Outcomes:**
- Conversation is the primary interaction mode
- Agent suggestions feel like collaboration
- Human always in control of major decisions
- Agent explains its reasoning when useful

**Anti-patterns:**
- Treating agent as a form-filler
- Modal confirmations for every agent action
- Agent making decisions without transparency

### 4. Scientific Aesthetic

Clean, readable, information-rich when needed.

**Outcomes:**
- Typography aids reading long-form content
- Data visualizations for world structure (when useful)
- Clear hierarchy of information

**Anti-patterns:**
- Sacrificing readability for aesthetics
- Information buried in menus
- Visualizations that obscure rather than clarify

---

## Visual Identity

### Color Philosophy

Earth tones evoke thoughtful exploration rather than sci-fi clichés:

| Role | Intent |
|------|--------|
| Primary backgrounds | Deep, calm, receding |
| Accent colors | Warm highlights for interaction |
| Text | High contrast, easy reading |
| Borders/dividers | Subtle, not distracting |

**NOT:** Neon everything, glitch effects, overwhelming darkness

### Typography Philosophy

- Readable at length (stories can be long)
- Clear hierarchy (headings, body, captions)
- Monospace for code/technical content
- System fonts for performance where design isn't critical

### Spacing & Layout

- Generous whitespace (content breathes)
- Consistent rhythm
- Mobile-first responsiveness
- Reading width limits for long-form content

---

## Interaction Patterns

### Chat-First Design

The chat panel is the primary way to interact with agents:

**Outcomes:**
- Always accessible but not intrusive
- Can be expanded for focus mode
- Shows agent reasoning when useful
- Supports rich content (images, cards, UI components)

### Canvas UI

Agents can create dynamic UI in the canvas area:

**Outcomes:**
- Components render at designated mount points
- Smooth transitions between UI states
- Agent-driven but user-controllable
- Falls back gracefully if components fail

### World/Story Navigation

**Outcomes:**
- Easy to understand current context (which world? which story?)
- Breadcrumb-style navigation
- Quick switching between worlds
- Story position always clear

---

## Component Guidelines

### Cards

Used for worlds, stories, suggestions:
- Clear title hierarchy
- Summary text visible without hover
- Actions discoverable on interaction
- Visual indicator of status/type

### Buttons

- Primary actions are obvious
- Destructive actions require confirmation
- Loading states prevent double-submission
- Icons paired with text for clarity

### Forms

- Inline validation
- Clear error messages
- Save state visible
- Auto-save where appropriate

### Modals

- Used sparingly
- Clear exit mechanism
- Don't stack modals
- Consider if sheet/panel would work better

---

## Story Reading Experience

### Visual Novel Mode

For immersive story consumption:

**Outcomes:**
- Full-screen capable
- Character portraits and backgrounds
- Text appears naturally (not jarring)
- Easy navigation between segments
- Audio integration (ambient, music)

### Editor Mode

For story creation and editing:

**Outcomes:**
- Clean writing environment
- World context accessible
- Agent assistance available
- Segment structure visible

---

## Responsive Behavior

| Viewport | Adaptation |
|----------|------------|
| Desktop | Full experience, side-by-side layouts |
| Tablet | Stacked layouts, collapsible panels |
| Mobile | Single-column, bottom sheet patterns |

**Outcome:** Full functionality on all devices, optimized for each context.

---

## Performance Philosophy

- Fast initial load (minimize blocking resources)
- Progressive enhancement (core content first)
- Skeleton loading over spinners where possible
- Optimistic UI updates (feel fast even when waiting)

---

## What This Is NOT

### NOT a Style Guide

This document doesn't specify `#3a86a0` or `16px`. Those are implementation details that may change. This defines outcomes.

### NOT Prescriptive

"Use this exact component library" violates flexibility. The goal is the outcome, not the implementation.

### NOT Complete

UX evolves as we learn from users. This is a starting point, not a final destination.

---

## Success Criteria

| Criterion | How to Evaluate |
|-----------|-----------------|
| Immersion | Does the UI disappear into the content? |
| Clarity | Can new users understand what to do? |
| Collaboration feel | Does the agent feel like a partner? |
| Readability | Can users read stories comfortably? |
| Performance | Does the UI feel responsive? |

---

## Anti-Patterns Summary

| Don't Do This | Why |
|---------------|-----|
| Dark sci-fi clichés (neon, glitch) | Distracts from content |
| Dense dashboards | Overwhelms users |
| Modal for everything | Interrupts flow |
| Hidden critical info | Frustrates users |
| Animations everywhere | Feels gimmicky |
| Agent as command interface | Loses collaboration feel |

---

## Remember

> "The best interface is the one you don't notice."

The UI serves the creative work. When users are deep in world-building or story-writing, the interface should feel like it's not there at all - just them and their creative partner.
