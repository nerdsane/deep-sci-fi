// Shared framer-motion animation presets
import type { Variants, Transition } from 'framer-motion'

// ── Transitions ──────────────────────────────────────────────
export const springSnappy: Transition = {
  type: 'spring',
  stiffness: 400,
  damping: 25,
}

export const springGentle: Transition = {
  type: 'spring',
  stiffness: 200,
  damping: 20,
}

// ── Entrance Variants ────────────────────────────────────────
export const fadeInUp: Variants = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: 'easeOut' } },
}

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.5, ease: 'easeOut' } },
}

// ── Stagger Containers ───────────────────────────────────────
export const staggerContainer: Variants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.08,
      delayChildren: 0.1,
    },
  },
}

export const staggerContainerSlow: Variants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.12,
      delayChildren: 0.15,
    },
  },
}

// ── Hover presets (for whileHover) ───────────────────────────
// Lift + subtle scale — avoids clipping by parent overflow
export const springHover = {
  y: -4,
  scale: 1.01,
  transition: springSnappy,
}

export const springHoverSubtle = {
  y: -2,
  scale: 1.005,
  transition: springSnappy,
}

// ── Tap preset ───────────────────────────────────────────────
export const springTap = {
  scale: 0.97,
}
