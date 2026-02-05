# Design Tokens

**Type:** STABLE
**Created:** 2026-02-03
**Last Updated:** 2026-02-03

---

## Spacing (8px base)

| Token | Value | Use |
|-------|-------|-----|
| xs | 4px | Tight spacing, icon gaps |
| sm | 8px | Default small spacing |
| md | 16px | Standard spacing |
| lg | 24px | Section spacing |
| xl | 32px | Large gaps |
| 2xl | 48px | Major sections |
| 3xl | 64px | Page-level spacing |

---

## Border Radius

| Token | Value | Notes |
|-------|-------|-------|
| none | 0px | **Default** - sharp corners |
| sm | 2px | **Maximum allowed** |

*Never use larger radius values. We are sharp, not soft.*

---

## Motion

| Token | Value | Use |
|-------|-------|-----|
| fast | 100ms | Micro-interactions |
| normal | 150ms | Standard transitions |
| slow | 200ms | **Maximum** - larger animations |
| easing | ease-out | Default easing |

*Motion should have purpose. No decorative animations.*

---

## Colors

Reference the existing Tailwind config - terminal aesthetic.

See `.vision/UX_STYLING.md` for the full color palette:

```css
/* Backgrounds */
--bg-primary: #000000;
--bg-secondary: #0a0a0a;
--bg-tertiary: #0f0f0f;

/* Neon Accents */
--neon-cyan: #00ffcc;
--neon-cyan-bright: #00ffff;
--neon-purple: #aa00ff;

/* Text */
--text-primary: #c8c8c8;
--text-secondary: #8a8a8a;
--text-tertiary: #5a5a5a;
```

---

## Typography

```css
--font-mono: 'Berkeley Mono', 'SF Mono', 'JetBrains Mono', monospace;
--font-sans: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
```

- **Mono** for headers, labels, UI chrome
- **Sans** for body text, story content, long-form reading
- All caps + letter-spacing for labels and badges
