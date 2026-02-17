'use client'

import { useEffect, useRef, useState } from 'react'
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
}: {
  node: WorldNode | null
  pos: { x: number; y: number }
}) {
  if (!node) return null
  return (
    <div
      className="pointer-events-none absolute z-20 glass-purple border border-neon-purple/30 p-3 max-w-xs"
      style={{
        left: pos.x + 14,
        top: pos.y - 8,
        transform: pos.x > window.innerWidth * 0.65 ? 'translateX(-110%)' : undefined,
      }}
    >
      <div className="font-display text-xs text-neon-purple tracking-wider mb-1">
        {node.name}
      </div>
      <div className="text-text-tertiary text-[10px] font-mono mb-2 leading-relaxed">
        {node.premise_short}
      </div>
      <div className="flex items-center gap-3 text-[10px] text-text-muted font-mono">
        <span>
          <span className="text-neon-cyan">{node.year_setting}</span>
        </span>
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

function Legend({ labels, colorMap }: { labels: string[]; colorMap: Record<string, string> }) {
  if (labels.length === 0) return null
  return (
    <div className="absolute bottom-4 left-4 z-10 space-y-1">
      {labels.map((lbl) => (
        <div key={lbl} className="flex items-center gap-2">
          <span
            className="w-2 h-2 shrink-0"
            style={{ background: colorMap[lbl] || '#555' }}
          />
          <span className="text-[10px] text-text-tertiary font-mono tracking-wider">
            {lbl}
          </span>
        </div>
      ))}
    </div>
  )
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

  // Render D3 graph
  useEffect(() => {
    if (!data || !svgRef.current || !containerRef.current) return

    const container = containerRef.current
    const width = container.clientWidth
    const height = container.clientHeight
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
    const padding = 80
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
    const stars = d3.range(starCount).map(() => ({
      x: Math.random() * width,
      y: Math.random() * height,
      r: Math.random() * 1.2 + 0.2,
      opacity: Math.random() * 0.5 + 0.1,
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
    // Group nodes by cluster, draw a soft blur circle at centroid
    const clusterGroups = d3.group(nodes, (d) => d.cluster)

    clusterGroups.forEach((members, cid) => {
      if (cid === -1) return // skip uncharted
      const cx = d3.mean(members, (d) => d.px) ?? 0
      const cy = d3.mean(members, (d) => d.py) ?? 0
      const color = members[0].cluster_color

      // Soft radial gradient halo
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

      // Cluster label in background
      g.append('text')
        .attr('x', cx)
        .attr('y', cy + 112)
        .attr('text-anchor', 'middle')
        .attr('fill', color)
        .attr('opacity', 0.25)
        .attr('font-size', 9)
        .attr('font-family', 'monospace')
        .attr('letter-spacing', '0.15em')
        .text(members[0].cluster_label.toUpperCase())
    })

    // ── Nearest-neighbor connecting lines ─────────────────────────────────────
    // For each node, draw a faint line to its 2 nearest cluster-mates
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
      .attr('fill-opacity', d => d.has_embedding ? 0.85 : 0.35)
      .attr('stroke', (d) => d.cluster_color)
      .attr('stroke-width', 1)
      .attr('filter', (d) =>
        d.has_embedding ? `drop-shadow(0 0 4px ${d.cluster_color}88)` : null
      )

    // World name label
    nodeG
      .append('text')
      .attr('y', (d) => -(NODE_BASE_R + Math.sqrt(d.dweller_count) * 1.2) - 4)
      .attr('text-anchor', 'middle')
      .attr('fill', '#D4D4D8')
      .attr('font-size', 9)
      .attr('font-family', 'monospace')
      .attr('letter-spacing', '0.1em')
      .text((d) => d.name.toUpperCase())

    // ── Interaction ───────────────────────────────────────────────────────────
    nodeG
      .on('mouseenter', function (event, d) {
        d3.select(this).select('circle:nth-child(2)').transition().duration(150).attr('r', (NODE_BASE_R + Math.sqrt(d.dweller_count) * 1.2) * 1.4)
        setTooltip({ node: d, pos: { x: event.clientX, y: event.clientY } })
      })
      .on('mousemove', function (event) {
        setTooltip((prev) => ({ ...prev, pos: { x: event.clientX, y: event.clientY } }))
      })
      .on('mouseleave', function (_, d) {
        d3.select(this).select('circle:nth-child(2)').transition().duration(150).attr('r', NODE_BASE_R + Math.sqrt(d.dweller_count) * 1.2)
        setTooltip({ node: null, pos: { x: 0, y: 0 } })
      })
      .on('click', (_, d) => {
        router.push(`/world/${d.id}`)
      })

    // ── Initial zoom-to-fit ───────────────────────────────────────────────────
    svg.call(
      zoom.transform,
      d3.zoomIdentity
        .translate(width / 2, height / 2)
        .scale(0.85)
        .translate(-width / 2, -height / 2)
    )
  }, [data, router])

  return (
    <div ref={containerRef} className="relative w-full h-full bg-bg-primary overflow-hidden">
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

      {!loading && !error && data && data.worlds.length > 0 && (
        <>
          <svg ref={svgRef} className="w-full h-full" />

          {/* Controls hint */}
          <div className="absolute top-4 right-4 z-10 text-text-muted text-[10px] font-mono space-y-0.5">
            <div>scroll — zoom</div>
            <div>drag — pan</div>
            <div>click — explore world</div>
          </div>

          {/* World count */}
          <div className="absolute top-4 left-4 z-10">
            <span className="text-[10px] font-mono text-text-muted tracking-wider">
              <span className="text-neon-purple">{data.total}</span> worlds mapped
            </span>
          </div>

          <Legend labels={data.cluster_labels} colorMap={colorMap} />

          <Tooltip node={tooltip.node} pos={tooltip.pos} />
        </>
      )}
    </div>
  )
}
