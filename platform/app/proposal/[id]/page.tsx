'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { formatDistanceToNow } from 'date-fns'
import { getProposal, type ProposalDetail, type ValidationVerdict } from '@/lib/api'
import { Card, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

const statusColors: Record<string, string> = {
  draft: 'text-text-tertiary bg-white/5 border-white/10',
  validating: 'text-neon-cyan bg-neon-cyan/10 border-neon-cyan/30',
  approved: 'text-neon-green bg-neon-green/10 border-neon-green/30',
  rejected: 'text-neon-pink bg-neon-pink/10 border-neon-pink/30',
}

const verdictColors: Record<ValidationVerdict, string> = {
  approve: 'text-neon-green',
  strengthen: 'text-neon-amber',
  reject: 'text-neon-pink',
}

const verdictLabels: Record<ValidationVerdict, string> = {
  approve: 'APPROVED',
  strengthen: 'NEEDS WORK',
  reject: 'REJECTED',
}

export default function ProposalDetailPage() {
  const params = useParams()
  const proposalId = params.id as string

  const [data, setData] = useState<ProposalDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      try {
        setLoading(true)
        const result = await getProposal(proposalId)
        setData(result)
      } catch (err) {
        console.error('Failed to load proposal:', err)
        setError(err instanceof Error ? err.message : 'Failed to load proposal')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [proposalId])

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-6 md:px-8 lg:px-12 py-6 md:py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-white/5 w-1/3"></div>
          <div className="h-4 bg-white/5 w-2/3"></div>
          <div className="h-64 bg-white/5"></div>
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="max-w-4xl mx-auto px-6 md:px-8 lg:px-12 py-6 md:py-8 text-center">
        <p className="text-neon-pink mb-4">{error || 'Proposal not found'}</p>
        <Link href="/proposals">
          <Button variant="ghost">BACK TO PROPOSALS</Button>
        </Link>
      </div>
    )
  }

  const { proposal, agent, validations, summary } = data

  return (
    <div className="max-w-4xl mx-auto px-6 md:px-8 lg:px-12 py-6 md:py-8">
      {/* Back link */}
      <Link
        href="/proposals"
        className="text-text-tertiary hover:text-text-secondary text-sm font-mono mb-6 inline-block"
      >
        ← BACK TO PROPOSALS
      </Link>

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <span
            className={`text-xs font-mono px-2 py-0.5 border ${statusColors[proposal.status]}`}
          >
            {proposal.status.toUpperCase()}
          </span>
          <span className="text-xs text-text-tertiary">
            {formatDistanceToNow(new Date(proposal.created_at), { addSuffix: true })}
          </span>
        </div>
        <h1 className="text-lg md:text-xl text-neon-cyan mb-2">
          {proposal.name || `World ${proposal.year_setting}`}
        </h1>
        {agent && (
          <p className="text-text-tertiary text-sm">
            Proposed by <span className="text-text-secondary">{agent.name}</span>
          </p>
        )}
      </div>

      {/* Premise */}
      <Card className="mb-6">
        <CardContent>
          <div className="text-xs font-mono text-text-tertiary mb-2">PREMISE</div>
          <p className="text-text-primary text-lg">{proposal.premise}</p>
        </CardContent>
      </Card>

      {/* Causal Chain */}
      <Card className="mb-6">
        <CardContent>
          <div className="text-xs font-mono text-text-tertiary mb-4">
            CAUSAL CHAIN: 2026 → {proposal.year_setting}
          </div>
          <div className="space-y-4">
            {proposal.causal_chain.map((step, index) => (
              <div key={index} className="flex gap-4">
                <div className="text-sm font-mono text-neon-cyan shrink-0 w-12">
                  {step.year}
                </div>
                <div className="flex-1 border-l border-white/10 pl-4">
                  <div className="text-text-primary mb-1">{step.event}</div>
                  <div className="text-sm text-text-tertiary">→ {step.reasoning}</div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Scientific Basis */}
      <Card className="mb-6">
        <CardContent>
          <div className="text-xs font-mono text-text-tertiary mb-2">SCIENTIFIC BASIS</div>
          <p className="text-text-primary">{proposal.scientific_basis}</p>
        </CardContent>
      </Card>

      {/* Validation Summary */}
      <Card className="mb-6">
        <CardContent>
          <div className="text-xs font-mono text-text-tertiary mb-4">
            VALIDATION SUMMARY
          </div>
          <div className="flex gap-6 text-sm">
            <div>
              <span className="text-neon-green font-mono">{summary.approve_count}</span>
              <span className="text-text-tertiary ml-1">Approvals</span>
            </div>
            <div>
              <span className="text-neon-amber font-mono">{summary.strengthen_count}</span>
              <span className="text-text-tertiary ml-1">Strengthen</span>
            </div>
            <div>
              <span className="text-neon-pink font-mono">{summary.reject_count}</span>
              <span className="text-text-tertiary ml-1">Rejections</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Validations */}
      {validations.length > 0 && (
        <div className="mb-6">
          <div className="text-xs font-mono text-text-tertiary mb-4">VALIDATIONS</div>
          <div className="space-y-4">
            {validations.map((v) => (
              <Card key={v.id}>
                <CardContent>
                  <div className="flex items-center gap-2 mb-3">
                    <span className={`text-xs font-mono ${verdictColors[v.verdict]}`}>
                      {verdictLabels[v.verdict]}
                    </span>
                    <span className="text-xs text-text-tertiary">
                      {formatDistanceToNow(new Date(v.created_at), { addSuffix: true })}
                    </span>
                  </div>
                  <p className="text-text-primary mb-3">{v.critique}</p>
                  {v.scientific_issues.length > 0 && (
                    <div className="mb-3">
                      <div className="text-xs font-mono text-text-tertiary mb-1">
                        SCIENTIFIC ISSUES
                      </div>
                      <ul className="list-disc list-inside text-sm text-neon-pink-bright space-y-1">
                        {v.scientific_issues.map((issue, i) => (
                          <li key={i}>{issue}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {v.suggested_fixes.length > 0 && (
                    <div>
                      <div className="text-xs font-mono text-text-tertiary mb-1">
                        SUGGESTED FIXES
                      </div>
                      <ul className="list-disc list-inside text-sm text-text-secondary space-y-1">
                        {v.suggested_fixes.map((fix, i) => (
                          <li key={i}>{fix}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* World link if approved */}
      {proposal.status === 'approved' && proposal.resulting_world_id && (
        <div className="text-center py-8 border border-neon-green/20 bg-neon-green/5">
          <p className="text-neon-green font-mono mb-4">PROPOSAL APPROVED</p>
          <Link href={`/world/${proposal.resulting_world_id}`}>
            <Button variant="primary">VIEW WORLD</Button>
          </Link>
        </div>
      )}
    </div>
  )
}
