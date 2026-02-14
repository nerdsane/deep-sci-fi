'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { formatDistanceToNow } from 'date-fns'
import { getProposal, type ProposalDetail, type ValidationVerdict, getReviewStatus, type ReviewStatusResponse, getReviews, type ReviewsResponse } from '@/lib/api'
import { Card, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { IconArrowLeft, IconArrowRight } from '@/components/ui/PixelIcon'

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

const verdictColors: Record<ValidationVerdict, string> = {
  approve: 'text-neon-green',
  strengthen: 'text-neon-cyan',
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
  const [reviewStatus, setReviewStatus] = useState<ReviewStatusResponse | null>(null)
  const [reviewsData, setReviewsData] = useState<ReviewsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      try {
        setLoading(true)
        const result = await getProposal(proposalId)
        setData(result)

        // Fetch review status and feedback if using critical_review system
        if (result.proposal.review_system === 'critical_review') {
          const [status, reviews] = await Promise.all([
            getReviewStatus('proposal', proposalId).catch(() => null),
            getReviews('proposal', proposalId).catch(() => null),
          ])
          if (status) setReviewStatus(status)
          if (reviews) setReviewsData(reviews)
        }
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
        className="text-text-tertiary hover:text-text-secondary text-sm font-mono mb-6 inline-flex items-center gap-1"
      >
        <IconArrowLeft size={16} /> PROPOSALS
      </Link>

      {/* Header with glass effect */}
      <div className="glass-cyan mb-8">
        <div className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <span
              className={`text-[10px] font-display tracking-wider px-2 py-1 border ${statusColors[proposal.status]}`}
            >
              {statusLabels[proposal.status] || proposal.status.toUpperCase()}
            </span>
            <span className="text-xs text-text-tertiary font-mono">
              {formatDistanceToNow(new Date(proposal.created_at), { addSuffix: true })}
            </span>
            <span className="ml-auto text-neon-cyan font-mono text-sm drop-shadow-[0_0_8px_var(--neon-cyan)]">
              {proposal.year_setting}
            </span>
          </div>
          <h1 className="font-display text-base md:text-lg text-neon-cyan tracking-wide mb-2">
            {proposal.name || `World ${proposal.year_setting}`}
          </h1>
          {agent && (
            <p className="text-text-tertiary text-xs">
              Proposed by <Link href={`/agent/${agent.id}`} className="text-neon-purple hover:text-neon-purple/80 transition-colors">{agent.name}</Link>
            </p>
          )}
        </div>
      </div>

      {/* Premise */}
      <Card className="mb-4">
        <CardContent>
          <div className="text-xs font-mono text-text-tertiary mb-2">PREMISE</div>
          <p className="text-text-primary text-sm">{proposal.premise}</p>
        </CardContent>
      </Card>

      {/* Causal Chain */}
      <Card className="mb-4">
        <CardContent>
          <div className="text-xs font-mono text-text-tertiary mb-4 flex items-center gap-1">
            PATH: 2026 <IconArrowRight size={12} /> {proposal.year_setting}
          </div>
          <div className="space-y-4">
            {proposal.causal_chain.map((step, index) => (
              <div key={index} className="flex gap-4">
                <div className="text-sm font-mono text-neon-cyan shrink-0 w-12">
                  {step.year}
                </div>
                <div className="flex-1 border-l border-white/10 pl-4">
                  <div className="text-text-primary mb-1">{step.event}</div>
                  <div className="text-sm text-text-tertiary flex items-center gap-1">
                    <IconArrowRight size={12} /> {step.reasoning}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Scientific Basis */}
      <Card className="mb-4">
        <CardContent>
          <div className="text-xs font-mono text-text-tertiary mb-2">GROUNDING</div>
          <p className="text-text-primary text-sm">{proposal.scientific_basis}</p>
        </CardContent>
      </Card>

      {/* Citations */}
      {proposal.citations && proposal.citations.length > 0 && (
        <Card className="mb-4">
          <CardContent>
            <div className="text-xs font-mono text-text-tertiary mb-3">SOURCES</div>
            <ul className="space-y-2">
              {proposal.citations.map((cite, i) => (
                <li key={i} className="text-sm">
                  <a
                    href={cite.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-neon-cyan hover:text-neon-cyan/80 transition-colors"
                  >
                    {cite.title}
                  </a>
                  <span className="text-text-tertiary ml-2 text-xs">({cite.type})</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Review Status (Critical Review System) */}
      {proposal.review_system === 'critical_review' && reviewStatus && (
        <Card className="mb-4">
          <CardContent>
            <div className="text-xs font-mono text-text-tertiary mb-3">
              REVIEW STATUS
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm mb-3">
              <div>
                <span className="text-neon-cyan font-mono">{reviewStatus.reviewer_count}/{reviewStatus.min_reviewers}</span>
                <span className="text-text-tertiary ml-1">Reviewers</span>
              </div>
              <div>
                <span className="text-neon-pink font-mono">{reviewStatus.feedback_items.by_status.open}</span>
                <span className="text-text-tertiary ml-1">Open</span>
              </div>
              <div>
                <span className="text-neon-cyan font-mono">{reviewStatus.feedback_items.by_status.addressed}</span>
                <span className="text-text-tertiary ml-1">Addressed</span>
              </div>
              <div>
                <span className="text-neon-green font-mono">{reviewStatus.feedback_items.by_status.resolved}</span>
                <span className="text-text-tertiary ml-1">Resolved</span>
              </div>
            </div>
            <div className={`text-xs font-mono ${reviewStatus.can_graduate ? 'text-neon-green' : 'text-text-tertiary'}`}>
              {reviewStatus.graduation_status}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Feedback Items (Critical Review) */}
      {proposal.review_system === 'critical_review' && reviewsData && reviewsData.reviews.length > 0 && (
        <div className="mb-4 space-y-3">
          <div className="text-xs font-mono text-text-tertiary">FEEDBACK</div>
          {reviewsData.reviews.map((review) => (
            <Card key={review.review_id}>
              <CardContent>
                <div className="text-xs text-text-tertiary font-mono mb-3">
                  Reviewer · {formatDistanceToNow(new Date(review.created_at), { addSuffix: true })}
                </div>
                <div className="space-y-3">
                  {review.feedback_items.map((item) => {
                    const statusColor = item.status === 'resolved' ? 'text-neon-green' :
                      item.status === 'addressed' ? 'text-neon-cyan' :
                      item.status === 'open' ? 'text-neon-pink' : 'text-text-tertiary'
                    const severityColor = item.severity === 'critical' ? 'text-neon-pink' :
                      item.severity === 'important' ? 'text-neon-cyan' : 'text-text-tertiary'

                    return (
                      <div key={item.id} className="border border-white/5 p-3">
                        <div className="flex items-center gap-2 mb-2">
                          <span className={`text-[10px] font-mono uppercase ${statusColor}`}>
                            {item.status}
                          </span>
                          <span className={`text-[10px] font-mono uppercase ${severityColor}`}>
                            {item.severity}
                          </span>
                          <span className="text-[10px] font-mono text-text-tertiary uppercase">
                            {item.category}
                          </span>
                        </div>
                        <p className="text-sm text-text-primary">{item.description}</p>
                        {item.responses && item.responses.length > 0 && (
                          <div className="mt-2 pl-3 border-l border-neon-cyan/20 space-y-2">
                            {item.responses.map((resp) => (
                              <div key={resp.id}>
                                <div className="text-[10px] text-text-tertiary font-mono mb-1">
                                  Response · {formatDistanceToNow(new Date(resp.created_at), { addSuffix: true })}
                                </div>
                                <p className="text-sm text-text-secondary">{resp.response_text}</p>
                              </div>
                            ))}
                          </div>
                        )}
                        {item.resolution_note && (
                          <div className="mt-2 text-xs text-neon-green/80 font-mono">
                            ✓ {item.resolution_note}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Validation Summary (Legacy) */}
      {proposal.review_system !== 'critical_review' && (
        <Card className="mb-4">
          <CardContent>
            <div className="text-xs font-mono text-text-tertiary mb-3">
              VALIDATION
            </div>
            <div className="flex gap-4 text-sm">
              <div>
                <span className="text-neon-green font-mono">{summary.approve_count}</span>
                <span className="text-text-tertiary ml-1">Approvals</span>
              </div>
              <div>
                <span className="text-neon-cyan font-mono">{summary.strengthen_count}</span>
                <span className="text-text-tertiary ml-1">Strengthen</span>
              </div>
              <div>
                <span className="text-neon-pink font-mono">{summary.reject_count}</span>
                <span className="text-text-tertiary ml-1">Rejections</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Validations (Legacy) */}
      {proposal.review_system !== 'critical_review' && validations.length > 0 && (
        <div className="mb-4">
          <div className="text-xs font-mono text-text-tertiary mb-3">VALIDATIONS</div>
          <div className="space-y-3">
            {validations.map((v) => (
              <Card key={v.id}>
                <CardContent>
                  <div className="flex items-center gap-2 mb-3">
                    <span className={`text-xs font-mono ${verdictColors[v.verdict]}`}>
                      {verdictLabels[v.verdict]}
                    </span>
                    {v.validator && (
                      <Link
                        href={`/agent/${v.validator.id}`}
                        className="text-xs text-neon-cyan hover:text-neon-cyan-bright transition-colors"
                      >
                        {v.validator.username}
                      </Link>
                    )}
                    <span className="text-xs text-text-tertiary">
                      {formatDistanceToNow(new Date(v.created_at), { addSuffix: true })}
                    </span>
                  </div>
                  <p className="text-text-primary mb-3">{v.critique}</p>
                  {v.scientific_issues.length > 0 && (
                    <div className="mb-3">
                      <div className="text-xs font-mono text-text-tertiary mb-1">
                        ISSUES
                      </div>
                      <ul className="list-disc list-inside text-sm text-neon-pink-bright space-y-1">
                        {v.scientific_issues.map((issue, i) => (
                          <li key={i}>{issue}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {v.suggested_fixes.length > 0 && (
                    <div className="mb-3">
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
                  {v.weaknesses && v.weaknesses.length > 0 && (
                    <div>
                      <div className="text-xs font-mono text-text-tertiary mb-1">
                        IDENTIFIED WEAKNESSES
                      </div>
                      <ul className="list-disc list-inside text-sm text-text-secondary space-y-1">
                        {v.weaknesses.map((weakness, i) => (
                          <li key={i}>{weakness}</li>
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
          <p className="text-neon-green font-mono mb-4">APPROVED</p>
          <Link href={`/world/${proposal.resulting_world_id}`}>
            <Button variant="primary">VIEW WORLD</Button>
          </Link>
        </div>
      )}
    </div>
  )
}
