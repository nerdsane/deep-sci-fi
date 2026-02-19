'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import * as d3 from 'd3'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

interface WorldNode {
  id: string
  name: string
  premise_short: string
  year_setting: number
  cover_image_url: string | null
  dweller_count: number
  follower_count: number
  x: number
  y: number
  cluster: number
  cluster_label: string
  cluster_color: string
  has_embedding: boolean
}

interface MapData {
  worlds: WorldNode[]
  cluster_labels: string[]
  total: number
}

// ── Tooltip component ──────────────────────────────────────────────────────────

function Tooltip({
  node,
  pos,
  containerRef,
}: {
  node: WorldNode | null
  pos: { x: number; y: number }
  containerRef: React.RefObject<HTMLDivElement | null>
}) {
  if (!node) return null

  const containerWidth = containerRef.current?.clientWidth ?? 600
  const flipX = pos.x > containerWidth * 0.65

  return (
    <div
      className="pointer-events-none absolute z-20 glass-purple border border-neon-purple/30 p-3 max-w-[220px]"
      style={{
        left: flipX ? pos.x - 14 : pos.x + 14,
        top: pos.y - 8,
        transform: flipX ? 'translateX(-100%)' : undefined,
      }}
    >
      <div className="font-display text-xs text-neon-purple tracking-wider mb-1">
        {node.name}
      </div>
      <div className="text-zinc-300 text-[10px] font-mono mb-2 leading-relaxed">
        {node.premise_short}
      </div>
      <div className="flex items-center gap-2 flex-wrap text-[10px] text-zinc-400 font-mono">
        <span className="text-neon-cyan">{node.year_setting}</span>
        <span>
          <span className="text-neon-cyan">{node.dweller_count}</span> dwellers
        </span>
        <span
          className="px-1.5 py-0.5"
          style={{
            color: node.cluster_color,
            border: `1px solid ${node.cluster_color}44`,
          }}
        >
          {node.cluster_label}
        </span>
      </div>
    </div>
  )
}

// ── Legend ─────────────────────────────────────────────────────────────────────

function Legend({ labels, colorMap, total }: { labels: string[]; colorMap: Record<string, string>; total: number }) {
  if (labels.length === 0) return null
  return (
    <div className="absolute bottom-4 left-4 z-10 space-y-1.5 max-h-[50vh] overflow-y-auto pb-24 md:pb-0">
      {/* World count — sits above legend items so there's no collision */}
      <div className="mb-2 pb-2 border-b border-white/10">
        <span className="text-[11px] font-mono text-zinc-300 tracking-wider">
          <span className="text-neon-purple font-bold">{total}</span>
          {' '}worlds mapped
        </span>
      </div>
      {labels.map((lbl) => (
        <div key={lbl} className="flex items-center gap-2">
          <span
            className="w-3.5 h-3.5 rounded-sm shrink-0 inline-block"
            style={{ background: colorMap[lbl] || '#555' }}
          />
          <span className="text-[11px] text-zinc-200 font-mono tracking-wider">
            {lbl}
          </span>
        </div>
      ))}
    </div>
  )
}

// ── Label collision avoidance ───────────────────────────────────────────────────

function avoidLabelCollisions(
  labels: Array<{ x: number; y: number; text: string }>,
  charWidth: number,
  lineHeight: number
): Array<{ x: number; y: number; text: string }> {
  const result = labels.map((l) => ({ ...l }))
  const iterations = 30
  const padding = 3

  for (let iter = 0; iter < iterations; iter++) {
    for (let i = 0; i < result.length; i++) {
      for (let j = i + 1; j < result.length; j++) {
        const a = result[i]
        const b = result[j]
        const aw = (a.text.length * charWidth) / 2
        const bw = (b.text.length * charWidth) / 2

        const overlapX = aw + bw + padding - Math.abs(a.x - b.x)
        const overlapY = lineHeight + padding - Math.abs(a.y - b.y)

        if (overlapX > 0 && overlapY > 0) {
          // Push apart on Y axis only — labels are centered on node X, so X is fixed.
          // Overlap check requires both axes to confirm true collision.
          const push = overlapY / 2 + 1
          if (a.y <= b.y) {
            result[i].y -= push
            result[j].y += push
          } else {
            result[i].y += push
            result[j].y -= push
          }
        }
      }
    }
  }

  return result
}

// ── Main canvas ────────────────────────────────────────────────────────────────

export function WorldMapCanvas() {
  const svgRef = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const router = useRouter()

  const [data, setData] = useState<MapData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tooltip, setTooltip] = useState<{ node: WorldNode | null; pos: { x: number; y: number } }>({
    node: null,
    pos: { x: 0, y: 0 },
  })
  const [colorMap, setColorMap] = useState<Record<string, string>>({})
  const [dims, setDims] = useState<{ width: number; height: number } | null>(null)

  // Fetch map data
  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_BASE}/worlds/map`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const json: MapData = await res.json()
        setData(json)

        // Build label→color map
        const cm: Record<string, string> = {}
        json.worlds.forEach((w) => {
          if (w.cluster_label && w.cluster_label !== 'uncharted') {
            cm[w.cluster_label] = w.cluster_color
          }
        })
        setColorMap(cm)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load map')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  // Observe container dimensions — fixes the h-full=0 problem on mobile
  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const measure = () => {
      const w = el.clientWidth
      const h = el.clientHeight
      if (w > 0 && h > 0) {
        setDims({ width: w, height: h })
      }
    }

    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  // Draw D3 graph — runs when data OR dims change
  const drawGraph = useCallback(() => {
    if (!data || !svgRef.current || !dims) return

    const { width, height } = dims
    const worlds = data.worlds

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()
    svg.attr('width', width).attr('height', height)

    // ── Zoom + pan ────────────────────────────────────────────────────────────
    const g = svg.append('g')

    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.3, 6])
      .on('zoom', (event) => {
        g.attr('transform', event.transform)
      })

    svg.call(zoom)

    // ── Project semantic coords → pixel coords ────────────────────────────────
    const padding = Math.min(80, width * 0.12)
    const xScale = d3.scaleLinear().domain([-1, 1]).range([padding, width - padding])
    const yScale = d3.scaleLinear().domain([-1, 1]).range([padding, height - padding])

    // Compute pixel positions
    const nodes = worlds.map((w) => ({
      ...w,
      px: xScale(w.x),
      py: yScale(w.y),
    }))

    // ── Starfield background ──────────────────────────────────────────────────
    const starCount = 120
    const rng = d3.randomLcg(0xdeadbeef) // deterministic
    const stars = d3.range(starCount).map(() => ({
      x: rng() * width,
      y: rng() * height,
      r: rng() * 1.2 + 0.2,
      opacity: rng() * 0.5 + 0.1,
    }))

    g.append('g')
      .attr('class', 'stars')
      .selectAll('circle')
      .data(stars)
      .join('circle')
      .attr('cx', (d) => d.x)
      .attr('cy', (d) => d.y)
      .attr('r', (d) => d.r)
      .attr('fill', '#F4F4F5')
      .attr('opacity', (d) => d.opacity)

    // ── Cluster nebula halos ──────────────────────────────────────────────────
    const clusterGroups = d3.group(nodes, (d) => d.cluster)

    clusterGroups.forEach((members, cid) => {
      if (cid === -1) return // skip uncharted
      const cx = d3.mean(members, (d) => d.px) ?? 0
      const cy = d3.mean(members, (d) => d.py) ?? 0
      const color = members[0].cluster_color

      const gradId = `halo-${cid}`
      const defs = svg.select('defs').empty() ? svg.append('defs') : svg.select('defs')

      const radGrad = defs
        .append('radialGradient')
        .attr('id', gradId)
        .attr('cx', '50%')
        .attr('cy', '50%')
        .attr('r', '50%')

      radGrad.append('stop').attr('offset', '0%').attr('stop-color', color).attr('stop-opacity', 0.08)
      radGrad.append('stop').attr('offset', '100%').attr('stop-color', color).attr('stop-opacity', 0)

      g.append('ellipse')
        .attr('cx', cx)
        .attr('cy', cy)
        .attr('rx', 140)
        .attr('ry', 100)
        .attr('fill', `url(#${gradId})`)

    })

    // ── Nearest-neighbor connecting lines ─────────────────────────────────────
    nodes.forEach((node) => {
      if (node.cluster === -1) return

      const sameCluster = nodes.filter((n) => n.cluster === node.cluster && n.id !== node.id)
      const nearest = sameCluster
        .map((n) => ({
          n,
          dist: Math.hypot(n.px - node.px, n.py - node.py),
        }))
        .sort((a, b) => a.dist - b.dist)
        .slice(0, 2)

      nearest.forEach(({ n, dist }) => {
        const opacity = Math.max(0.03, 0.15 - dist / 1200)
        g.append('line')
          .attr('x1', node.px)
          .attr('y1', node.py)
          .attr('x2', n.px)
          .attr('y2', n.py)
          .attr('stroke', node.cluster_color)
          .attr('stroke-width', 0.5)
          .attr('opacity', opacity)
      })
    })

    // ── World nodes ───────────────────────────────────────────────────────────
    const NODE_BASE_R = 6
    const nodeG = g
      .append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .attr('transform', (d) => `translate(${d.px},${d.py})`)
      .style('cursor', 'pointer')

    // Glow ring
    nodeG
      .append('circle')
      .attr('r', (d) => NODE_BASE_R + 2 + Math.sqrt(d.dweller_count) * 1.5)
      .attr('fill', 'none')
      .attr('stroke', (d) => d.cluster_color)
      .attr('stroke-width', 0.5)
      .attr('opacity', 0.3)

    // Core circle
    nodeG
      .append('circle')
      .attr('r', (d) => NODE_BASE_R + Math.sqrt(d.dweller_count) * 1.2)
      .attr('fill', (d) => d.cluster_color)
      .attr('fill-opacity', (d) => (d.has_embedding ? 0.85 : 0.35))
      .attr('stroke', (d) => d.cluster_color)
      .attr('stroke-width', 1)
      .attr('filter', (d) =>
        d.has_embedding ? `drop-shadow(0 0 4px ${d.cluster_color}88)` : null
      )

    // ── Label collision avoidance ─────────────────────────────────────────────
    const CHAR_W = 5.5 // approx monospace char width at font-size 9
    const LINE_H = 12

    const rawLabels = nodes.map((d) => ({
      x: d.px,
      y: d.py - (NODE_BASE_R + Math.sqrt(d.dweller_count) * 1.2) - 4,
      text: d.name.toUpperCase(),
    }))

    const adjustedLabels = avoidLabelCollisions(rawLabels, CHAR_W, LINE_H)

    // World name labels — hidden on mobile (too cramped); visible on wider viewports
    // 768px matches Tailwind's md breakpoint used by hint divs and legend padding
    const isMobile = width < 768
    if (!isMobile) {
      nodes.forEach((d, i) => {
        const adj = adjustedLabels[i]
        g.append('text')
          .attr('x', d.px)
          .attr('y', adj.y)
          .attr('text-anchor', 'middle')
          .attr('fill', '#D4D4D8')
          .attr('font-size', 9)
          .attr('font-family', 'monospace')
          .attr('letter-spacing', '0.1em')
          .attr('pointer-events', 'none')
          .text(d.name.toUpperCase())
      })
    }

    // ── Interaction ───────────────────────────────────────────────────────────
    nodeG
      .on('mouseenter', function (event, d) {
        d3.select(this).select('circle:nth-child(2)').transition().duration(150).attr('r', (NODE_BASE_R + Math.sqrt(d.dweller_count) * 1.2) * 1.4)
        const rect = containerRef.current?.getBoundingClientRect()
        const x = event.clientX - (rect?.left ?? 0)
        const y = event.clientY - (rect?.top ?? 0)
        setTooltip({ node: d, pos: { x, y } })
      })
      .on('mousemove', function (event) {
        const rect = containerRef.current?.getBoundingClientRect()
        const x = event.clientX - (rect?.left ?? 0)
        const y = event.clientY - (rect?.top ?? 0)
        setTooltip((prev) => ({ ...prev, pos: { x, y } }))
      })
      .on('mouseleave', function (_, d) {
        d3.select(this).select('circle:nth-child(2)').transition().duration(150).attr('r', NODE_BASE_R + Math.sqrt(d.dweller_count) * 1.2)
        setTooltip({ node: null, pos: { x: 0, y: 0 } })
      })
      .on('click', (_, d) => {
        router.push(`/world/${d.id}`)
      })

    // ── Zoom to fit all nodes ─────────────────────────────────────────────────
    if (nodes.length > 0) {
      const xs = nodes.map((n) => n.px)
      const ys = nodes.map((n) => n.py)
      const minX = Math.min(...xs)
      const maxX = Math.max(...xs)
      const minY = Math.min(...ys)
      const maxY = Math.max(...ys)

      const contentW = maxX - minX || 1
      const contentH = maxY - minY || 1
      const scale = Math.min(
        (width - padding * 2) / contentW,
        (height - padding * 2) / contentH,
        1.5
      ) * 0.85

      const midX = (minX + maxX) / 2
      const midY = (minY + maxY) / 2

      svg.call(
        zoom.transform,
        d3.zoomIdentity
          .translate(width / 2, height / 2)
          .scale(scale)
          .translate(-midX, -midY)
      )
    }
  }, [data, dims, router])

  useEffect(() => {
    drawGraph()
  }, [drawGraph])

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full bg-bg-primary overflow-hidden"
    >
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-neon-purple text-xs font-mono tracking-widest animate-pulse">
            MAPPING WORLDS…
          </div>
        </div>
      )}

      {error && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="glass-cyan p-6 max-w-sm text-center">
            <p className="text-neon-pink text-xs font-mono mb-2">MAP UNAVAILABLE</p>
            <p className="text-text-tertiary text-xs">{error}</p>
          </div>
        </div>
      )}

      {!loading && !error && data && data.worlds.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center">
          <p className="text-text-tertiary text-xs font-mono">No worlds to map yet.</p>
        </div>
      )}

      {!loading && !error && data && data.worlds.length > 0 && dims && (
        <>
          <svg ref={svgRef} className="absolute inset-0 w-full h-full" />

          {/* Controls hint — desktop */}
          <div className="absolute top-4 right-4 z-10 text-zinc-400 text-[10px] font-mono space-y-0.5 hidden md:block">
            <div>scroll — zoom</div>
            <div>drag — pan</div>
            <div>click — explore world</div>
          </div>

          {/* Controls hint — mobile */}
          <div className="absolute top-4 right-4 z-10 text-zinc-400 text-[10px] font-mono md:hidden">
            pinch — zoom · tap — explore
          </div>

          {/* Legend with world count embedded — bottom left */}
          <Legend labels={data.cluster_labels} colorMap={colorMap} total={data.total} />

          <Tooltip node={tooltip.node} pos={tooltip.pos} containerRef={containerRef} />
        </>
      )}
    </div>
  )
}
