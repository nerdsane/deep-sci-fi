import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ReactionButtons } from '../ReactionButtons'
import type { ReactionCounts } from '@/types'

describe('ReactionButtons', () => {
  const defaultCounts: ReactionCounts = {
    fire: 10,
    mind: 5,
    heart: 20,
    thinking: 3,
  }

  const defaultProps = {
    counts: defaultCounts,
    targetType: 'story' as const,
    targetId: 'test-story-123',
  }

  it('renders all 4 reaction buttons', () => {
    render(<ReactionButtons {...defaultProps} />)

    // Check emojis are present
    expect(screen.getByText('🔥')).toBeInTheDocument()
    expect(screen.getByText('🧠')).toBeInTheDocument()
    expect(screen.getByText('❤️')).toBeInTheDocument()
    expect(screen.getByText('🤔')).toBeInTheDocument()
  })

  it('displays correct initial counts', () => {
    render(<ReactionButtons {...defaultProps} />)

    expect(screen.getByText('10')).toBeInTheDocument() // fire
    expect(screen.getByText('5')).toBeInTheDocument()  // mind
    expect(screen.getByText('20')).toBeInTheDocument() // heart
    expect(screen.getByText('3')).toBeInTheDocument()  // thinking
  })

  it('increments count on click (optimistic update)', async () => {
    const user = userEvent.setup()
    render(<ReactionButtons {...defaultProps} />)

    // Find the fire button (contains 🔥)
    const fireButton = screen.getByText('🔥').closest('button')!

    // Initial count is 10
    expect(screen.getByText('10')).toBeInTheDocument()

    // Click the fire button
    await user.click(fireButton)

    // Count should increment to 11
    expect(screen.getByText('11')).toBeInTheDocument()
  })

  it('toggles count down when clicking same button again', async () => {
    const user = userEvent.setup()
    render(<ReactionButtons {...defaultProps} />)

    const fireButton = screen.getByText('🔥').closest('button')!

    // First click: 10 -> 11
    await user.click(fireButton)
    expect(screen.getByText('11')).toBeInTheDocument()

    // Second click: 11 -> 10 (toggle off)
    await user.click(fireButton)
    expect(screen.getByText('10')).toBeInTheDocument()
  })

  it('allows clicking multiple different reactions', async () => {
    const user = userEvent.setup()
    render(<ReactionButtons {...defaultProps} />)

    const fireButton = screen.getByText('🔥').closest('button')!
    const heartButton = screen.getByText('❤️').closest('button')!

    // Click fire
    await user.click(fireButton)
    expect(screen.getByText('11')).toBeInTheDocument() // fire: 10 -> 11

    // Click heart
    await user.click(heartButton)
    expect(screen.getByText('21')).toBeInTheDocument() // heart: 20 -> 21

    // Both should remain incremented
    expect(screen.getByText('11')).toBeInTheDocument()
    expect(screen.getByText('21')).toBeInTheDocument()
  })

  it('applies active style when reaction is selected', async () => {
    const user = userEvent.setup()
    render(<ReactionButtons {...defaultProps} />)

    const fireButton = screen.getByText('🔥').closest('button')!

    // Initially not active (no cyan border class)
    expect(fireButton).not.toHaveClass('border-neon-cyan/50')

    // Click to activate
    await user.click(fireButton)

    // Now should have active styling
    expect(fireButton).toHaveClass('border-neon-cyan/50')
  })

  it('removes active style when toggling off', async () => {
    const user = userEvent.setup()
    render(<ReactionButtons {...defaultProps} />)

    const fireButton = screen.getByText('🔥').closest('button')!

    // Click to activate
    await user.click(fireButton)
    expect(fireButton).toHaveClass('border-neon-cyan/50')

    // Click again to deactivate
    await user.click(fireButton)
    expect(fireButton).not.toHaveClass('border-neon-cyan/50')
  })

  it('handles zero counts correctly', () => {
    const zeroCounts: ReactionCounts = {
      fire: 0,
      mind: 0,
      heart: 0,
      thinking: 0,
    }

    render(
      <ReactionButtons
        counts={zeroCounts}
        targetType="world"
        targetId="test-world-456"
      />
    )

    // All should show 0
    const zeros = screen.getAllByText('0')
    expect(zeros).toHaveLength(4)
  })
})
