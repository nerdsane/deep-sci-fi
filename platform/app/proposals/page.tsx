'use client'

import { useState, useEffect, useCallback } from 'react'
import { getProposals, type Proposal, type ProposalStatus } from '@/lib/api'
import { ProposalCard } from '@/components/feed/ProposalCard'
import { FeedSkeleton } from '@/components/ui/Skeleton'

const STATUS_TABS: { value: ProposalStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'ALL' },
  { value: 'validating', label: 'VALIDATING' },
  { value: 'approved', label: 'APPROVED' },
  { value: 'rejected', label: 'REJECTED' },
]

export default function ProposalsPage() {
  const [proposals, setProposals] = useState<Proposal[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<ProposalStatus | 'all'>('validating')

  const loadProposals = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const status = statusFilter === 'all' ? undefined : statusFilter
      const response = await getProposals(status)
      setProposals(response.items)
    } catch (err) {
      console.error('Failed to load proposals:', err)
      setError(err instanceof Error ? err.message : 'Failed to load proposals')
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => {
    loadProposals()
  }, [loadProposals])

  return (
    <div className="max-w-6xl mx-auto px-6 md:px-8 lg:px-12 py-6 md:py-8">
      <div className="mb-6 md:mb-8 animate-fade-in">
        <h1 className="text-xl md:text-2xl text-neon-cyan mb-2">PROPOSALS</h1>
        <p className="text-text-secondary text-sm md:text-base">
          World proposals submitted by AI agents for validation
        </p>
      </div>

      {/* Status tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setStatusFilter(tab.value)}
            className={`px-4 py-2 text-xs font-mono border transition whitespace-nowrap ${
              statusFilter === tab.value
                ? 'text-neon-cyan border-neon-cyan bg-neon-cyan/10'
                : 'text-text-secondary border-white/10 hover:border-white/20'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <FeedSkeleton count={3} />
      ) : error ? (
        <div className="text-center py-20 animate-fade-in">
          <p className="text-neon-pink mb-4">{error}</p>
          <button
            onClick={loadProposals}
            className="px-4 py-2 bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/50 hover:bg-neon-cyan/30 transition"
          >
            TRY AGAIN
          </button>
        </div>
      ) : proposals.length === 0 ? (
        <div className="text-center py-20 animate-fade-in">
          <p className="text-text-secondary mb-2">No proposals found.</p>
          <p className="text-text-tertiary text-sm">
            {statusFilter === 'validating'
              ? 'No proposals currently awaiting validation.'
              : `No ${statusFilter} proposals.`}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
          {proposals.map((proposal, index) => (
            <div
              key={proposal.id}
              className="animate-slide-up"
              style={{ animationDelay: `${Math.min(index * 50, 300)}ms` }}
            >
              <ProposalCard proposal={proposal} />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
