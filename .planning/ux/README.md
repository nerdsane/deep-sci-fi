# Dynamic Canvas UX Documentation

All UX-related documentation for the Dynamic Canvas project.

## 📖 Reading Order

### 1. Start Here: Vision & Strategy
- **[Dynamic Canvas UX Vision](./dynamic-canvas-ux-vision.md)** - Complete vision, use cases, architecture, 12-week roadmap
- **[Component Strategy](./component-strategy.md)** - Why Radix UI, how to keep your styling, component architecture

### 2. Architecture Decisions
- **[Canvas Architecture Decision](./canvas-architecture-decision.md)** - Monorepo vs separate projects analysis

### 3. Implementation
- **[Radix Integration Quickstart](./radix-integration-quickstart.md)** - Get first component working in 30 min
- **[Implementation Guide](./implementation-guide.md)** - Complete 2-week Phase 1 build plan

## 📚 Document Overview

### [Dynamic Canvas UX Vision](./dynamic-canvas-ux-vision.md)
**The master plan.**

- Current state analysis (what works, what doesn't)
- Future state vision (agent-controlled dynamic UI)
- Use cases (story presentations, world workshops, multi-modal creation)
- Architecture (Agent Bus, canvas_ui tool, component library)
- 12-week implementation roadmap
- Technical decisions and success metrics

**Read this first** to understand the full vision.

### [Component Strategy](./component-strategy.md)
**How to build agent-composable UI while keeping your neon aesthetic.**

- Why Radix UI Primitives (unstyled, accessible, composable)
- Why NOT shadcn (opinionated styling conflicts)
- Component mapping strategy (JSON → Radix → Your CSS)
- Complete code examples with your styling
- 3-week implementation plan

**Read this** before starting implementation.

### [Canvas Architecture Decision](./canvas-architecture-decision.md)
**Should canvas live in letta-code or be a separate project?**

- Current tight coupling analysis
- Monorepo vs separate repos comparison
- When to separate (and when not to)
- Future-proofing strategies
- **Decision: Keep in letta-code for now** ✅

**Read this** to understand architectural choices.

### [Radix Integration Quickstart](./radix-integration-quickstart.md)
**Hands-on guide: Get your first component working in 30 minutes.**

Step-by-step:
1. Install Radix Dialog package
2. Create styled DSFDialog component
3. Add CSS matching your neon aesthetic
4. Integrate with DynamicRenderer
5. Make agent-controllable
6. Test end-to-end

**Read this** when ready to code!

### [Implementation Guide](./implementation-guide.md)
**Complete 2-week implementation plan for Phase 1 (Foundation).**

**Week 1: Agent Bus & State Management**
- Day 1-2: Agent Bus core (WebSocket server, client library)
- Day 3-4: Canvas State Manager
- Day 5-7: Canvas UI tool

**Week 2: Canvas Client & UI Components**
- Day 8-10: Canvas client integration
- Day 11-12: Component renderers (Radix + your styles)
- Day 13-14: Testing & polish

Includes complete code examples, testing procedures, troubleshooting.

**Read this** for detailed build plan.

## 🎯 Quick Navigation

**Just want to start coding?**
→ [Radix Integration Quickstart](./radix-integration-quickstart.md)

**Want the full context first?**
→ [Dynamic Canvas UX Vision](./dynamic-canvas-ux-vision.md)

**Need to understand component approach?**
→ [Component Strategy](./component-strategy.md)

**Want day-by-day implementation plan?**
→ [Implementation Guide](./implementation-guide.md)

**Questioning the architecture?**
→ [Canvas Architecture Decision](./canvas-architecture-decision.md)

## 🔗 Related Documentation

**Technical Specs** (in `../ technical-specs/`):
- [Agent Bus Technical Spec](../technical-specs/agent-bus.md) - WebSocket protocol, event types, routing
- [Canvas UI Tool Technical Spec](../technical-specs/canvas-ui-tool.md) - Tool API, component definitions

**Main Entry Point**:
- [DYNAMIC-CANVAS-README.md](../DYNAMIC-CANVAS-README.md) - Overview and navigation

## 📊 Implementation Status

- ✅ **Planning Complete** - All UX documents written
- ⏳ **Phase 1 Ready** - Can start building (2 weeks)
- 📅 **Full Vision** - 12 weeks to complete

## 🎨 Design Philosophy

**Core Principles:**
1. **Keep Your Aesthetic** - Neon cyberpunk styling stays 100% intact
2. **Agent-Composable** - Agent specifies UI via JSON data structures
3. **Accessible** - Radix handles keyboard nav, ARIA, focus management
4. **Incremental** - Build component by component, no big bang rewrite
5. **Battle-Tested** - Use proven primitives (Radix powers shadcn/ui)

**The Stack:**
- **Behavior:** Radix UI Primitives (unstyled, accessible components)
- **Styling:** Your existing CSS (neon cyan/purple, pure black, terminal aesthetic)
- **Architecture:** Agent Bus (WebSocket) + canvas_ui tool (JSON → UI)
- **Framework:** React 18.3.1 (already in your project)

## 🚀 Next Steps

1. Read [Dynamic Canvas UX Vision](./dynamic-canvas-ux-vision.md) for full context
2. Read [Component Strategy](./component-strategy.md) to understand approach
3. Follow [Radix Integration Quickstart](./radix-integration-quickstart.md) to build first component
4. Use [Implementation Guide](./implementation-guide.md) for complete Phase 1

**Estimated Time:**
- 📖 Reading: 2-3 hours
- 🛠️ Phase 1 implementation: 2 weeks
- 🚀 Full vision: 12 weeks

---

**Last Updated:** 2026-01-01
**Status:** Ready for Implementation ✅
