'use client'

import { useRef } from 'react'
import { motion, useInView, type Variants } from 'framer-motion'
import { fadeInUp, staggerContainer } from '@/lib/motion'

interface ScrollRevealProps {
  children: React.ReactNode
  className?: string
  variants?: Variants
  /** viewport intersection threshold – fraction visible before triggering */
  amount?: number
  /** trigger only once */
  once?: boolean
}

export function ScrollReveal({
  children,
  className,
  variants = fadeInUp,
  amount = 0.15,
  once = true,
}: ScrollRevealProps) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once, amount })

  return (
    <motion.div
      ref={ref}
      variants={variants}
      initial="hidden"
      animate={inView ? 'visible' : 'hidden'}
      className={className}
    >
      {children}
    </motion.div>
  )
}

/** Wrap children so each direct child staggers in on scroll */
interface StaggerRevealProps {
  children: React.ReactNode
  className?: string
  childVariants?: Variants
  amount?: number
  once?: boolean
}

export function StaggerReveal({
  children,
  className,
  childVariants = fadeInUp,
  amount = 0.1,
  once = true,
}: StaggerRevealProps) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once, amount })

  return (
    <motion.div
      ref={ref}
      variants={staggerContainer}
      initial="hidden"
      animate={inView ? 'visible' : 'hidden'}
      className={className}
    >
      {/* Each child must be wrapped in motion.div with childVariants */}
      {children}
    </motion.div>
  )
}
