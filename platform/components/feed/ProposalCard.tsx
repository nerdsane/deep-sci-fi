'use client'

import { formatDistanceToNow } from 'date-fns'
import Link from 'next/link'
import type { Proposal } from '@/lib/api'
import { Card, CardContent } from '@/components/ui/Card'
import { IconArrowRight } from '@/components/ui/PixelIcon'

interface ProposalCardProps {
  proposal: Proposal
}

const statusColors: Record<string, string> = {
  draft: 'text-text-tertiary bg-white/5 border-white/10',
  validating: 'text-neon-cyan bg-neon-cyan/10 border-neon-cyan/30',
  approved: 'text-neon-green bg-neon-green/10 border-neon-green/30',
  rejected: 'text-neon-pink bg-neon-pink/10 border-neon-pink/30',
}

const statusLabels: Record<string, string> = {
  draft: 'DRAFT',
  validating: 'PENDING',
  approved: 'APPROVED',
  rejected: 'REJECTED',
}

export function ProposalCard({ proposal }: ProposalCardProps) {
  const createdAt = new Date(proposal.created_at)

  return (
    <Link href={`/proposal/${proposal.id}`} className="block">
      <Card className="hover:border-neon-cyan/30 transition-colors cursor-pointer">
        <CardContent>
        {/* Status badge */}
        <div className="flex items-center gap-2 mb-3">
          <span
            className={`text-xs font-mono px-2 py-0.5 border ${statusColors[proposal.status]}`}
          >
            {statusLabels[proposal.status]}
          </span>
          <span className="text-xs text-text-tertiary">
            {formatDistanceToNow(createdAt, { addSuffix: true })}
          </span>
          {proposal.status === 'validating' && (
            <span className="text-xs font-mono text-text-tertiary ml-auto">
              {proposal.approve_count}/{proposal.validation_count} APPROVALS
            </span>
          )}
        </div>

        {/* World info */}
        <h3 className="text-sm text-neon-cyan mb-2">
          {proposal.name || `World ${proposal.year_setting}`}
        </h3>
        <p className="text-text-secondary text-xs mb-4 line-clamp-3">{proposal.premise}</p>

        {/* Causal chain preview */}
        {proposal.causal_chain.length > 0 && (
          <div className="border border-neon-cyan/10 bg-neon-cyan/5 p-4 mb-4">
            <div className="text-[10px] font-display text-neon-cyan tracking-wider mb-3">
              CAUSAL CHAIN TO {proposal.year_setting}
            </div>
            <div className="space-y-2">
              {proposal.causal_chain.slice(0, 3).map((step, index) => (
                <div key={index} className="flex items-start gap-3">
                  <div className="text-xs font-mono text-neon-cyan shrink-0 mt-0.5 drop-shadow-[0_0_4px_var(--neon-cyan)]">
                    {step.year}
                  </div>
                  <div className="flex-1">
                    <div className="text-xs text-text-primary line-clamp-2">
                      {step.event}
                    </div>
                    <div className="text-xs text-text-tertiary mt-0.5 line-clamp-1 flex items-center gap-1">
                      <IconArrowRight size={12} /> {step.reasoning}
                    </div>
                  </div>
                </div>
              ))}
              {proposal.causal_chain.length > 3 && (
                <div className="text-xs text-neon-cyan/60 font-mono">
                  + {proposal.causal_chain.length - 3} more steps
                </div>
              )}
            </div>
          </div>
        )}

        {/* Scientific basis preview */}
        <div className="text-xs text-text-tertiary font-mono mb-2">
          SCIENTIFIC BASIS
        </div>
        <p className="text-xs text-text-secondary line-clamp-2 mb-4">
          {proposal.scientific_basis}
        </p>
      </CardContent>

      </Card>
    </Link>
  )
}
