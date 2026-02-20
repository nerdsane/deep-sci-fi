'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import * as d3 from 'd3'
import { getDwellerGraph, DwellerGraphResponse, DwellerGraphNode, DwellerGraphEdge } from '@/lib/api'

// World → color mapping (deterministic from cluster index)
const WORLD_COLORS = [
  '#00f5ff', // neon-cyan
  '#b347ff', // neon-purple
  '#ff006e', // neon-pink
  '#00ff88', // neon-green
  '#ff9500', // neon-amber
  '#4488ff', // neon-blue
  '#ff4455', // neon-red
  '#44ffdd', // neon-teal
]

function worldColor(worldId: string, allWorldIds: string[]): string {
  const idx = allWorldIds.indexOf(worldId)
  return WORLD_COLORS[idx % WORLD_COLORS.length] ?? '#888'
}

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Edge is asymmetric if one speak direction is 3x+ the other. */
function isAsymmetric(edge: DwellerGraphEdge): boolean {
  const a = edge.speaks_a_to_b ?? 0
  const b = edge.speaks_b_to_a ?? 0
  if (a === 0 && b === 0) return false
  // Smooth the smaller side by +1 to avoid false positives at near-zero counts,
  // while still catching genuine imbalances like 3:1 or 5:0.
  return Math.max(a, b) >= 3 * (Math.min(a, b) + 1)
}

/** Dominant speak direction for asymmetric edges. */
function dominantDirection(edge: DwellerGraphEdge): 'a_to_b' | 'b_to_a' | 'balanced' {
  const a = edge.speaks_a_to_b ?? 0
  const b = edge.speaks_b_to_a ?? 0
  if (a > b * 2) return 'a_to_b'
  if (b > a * 2) return 'b_to_a'
  return 'balanced'
}

// ── Tooltip ─────────────────────────────────────────────────────────────────

interface EdgeTooltipData {
  source: DwellerGraphNode
  target: DwellerGraphNode
  edge: DwellerGraphEdge
}

interface TooltipState {
  node: DwellerGraphNode | null
  edge: EdgeTooltipData | null
  pos: { x: number; y: number }
}

function Tooltip({
  state,
  containerRef,
}: {
  state: TooltipState
  containerRef: React.RefObject<HTMLDivElement | null>
}) {
  const { node, edge, pos } = state
  if (!node && !edge) return null

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
      {node && (
        <>
          <div className="font-display text-xs text-neon-cyan tracking-wider mb-1">{node.name}</div>
          <div className="text-zinc-400 text-[10px] font-mono">{node.world}</div>
          <div className="text-zinc-500 text-[10px] font-mono mt-1">click → dweller detail</div>
        </>
      )}
      {edge && (() => {
        const { source: src, target: tgt, edge: e } = edge
        const totalSpeaks = (e.speaks_a_to_b ?? 0) + (e.speaks_b_to_a ?? 0)
        const asymmetric = isAsymmetric(e)
        return (
          <>
            <div className="font-display text-xs text-neon-purple tracking-wider mb-2">
              {src.name} ↔ {tgt.name}
            </div>
            {totalSpeaks > 0 && (
              <div className="space-y-0.5">
                {(e.speaks_a_to_b ?? 0) > 0 && (
                  <div className="text-[10px] font-mono text-zinc-300">
                    <span className="text-neon-cyan">{src.name}</span>
                    {' → '}
                    <span className="text-zinc-400">{tgt.name}</span>
                    {': '}
                    <span className="text-neon-cyan">{e.speaks_a_to_b}</span>
                    {' speak'}{e.speaks_a_to_b !== 1 ? 's' : ''}
                  </div>
                )}
                {(e.speaks_b_to_a ?? 0) > 0 && (
                  <div className="text-[10px] font-mono text-zinc-300">
                    <span className="text-neon-purple">{tgt.name}</span>
                    {' → '}
                    <span className="text-zinc-400">{src.name}</span>
                    {': '}
                    <span className="text-neon-purple">{e.speaks_b_to_a}</span>
                    {' speak'}{e.speaks_b_to_a !== 1 ? 's' : ''}
                  </div>
                )}
              </div>
            )}
            {((e.story_mentions_a_to_b ?? 0) > 0 || (e.story_mentions_b_to_a ?? 0) > 0) && (
              <div className="mt-1 text-[10px] font-mono text-zinc-500">
                {(e.story_mentions_a_to_b ?? 0) > 0 && (
                  <div>{src.name} mentions {tgt.name} in {e.story_mentions_a_to_b} {e.story_mentions_a_to_b === 1 ? 'story' : 'stories'}</div>
                )}
                {(e.story_mentions_b_to_a ?? 0) > 0 && (
                  <div>{tgt.name} mentions {src.name} in {e.story_mentions_b_to_a} {e.story_mentions_b_to_a === 1 ? 'story' : 'stories'}</div>
                )}
              </div>
            )}
            {(e.threads ?? 0) > 0 && (
              <div className="mt-1 text-[10px] font-mono text-zinc-500">
                {e.threads} reply thread{e.threads !== 1 ? 's' : ''}
              </div>
            )}
            {asymmetric && (
              <div className="mt-1 text-[10px] font-mono text-neon-amber/70">
                asymmetric relationship
              </div>
            )}
          </>
        )
      })()}
    </div>
  )
}

// ── Legend ──────────────────────────────────────────────────────────────────

function Legend({
  clusters,
  colorMap,
  nodeCount,
  edgeCount,
}: {
  clusters: { label: string; world_id: string }[]
  colorMap: Record<string, string>
  nodeCount: number
  edgeCount: number
}) {
  return (
    <div className="absolute bottom-4 left-4 z-10 space-y-1.5 max-h-[50vh] overflow-y-auto pb-24 md:pb-0">
      <div className="mb-2 pb-2 border-b border-white/10 space-y-0.5">
        <div className="text-[11px] font-mono text-zinc-300 tracking-wider">
          <span className="text-neon-cyan font-bold">{nodeCount}</span> dwellers
        </div>
        <div className="text-[11px] font-mono text-zinc-300 tracking-wider">
          <span className="text-neon-purple font-bold">{edgeCount}</span> connections
        </div>
      </div>
      {clusters.map((c) => (
        <div key={c.world_id} className="flex items-center gap-2">
          <span
            className="w-3 h-3 rounded-sm shrink-0 inline-block"
            style={{ background: colorMap[c.world_id] || '#555' }}
          />
          <span className="text-[11px] text-zinc-200 font-mono tracking-wider truncate max-w-[140px]">
            {c.label}
          </span>
        </div>
      ))}
    </div>
  )
}

// ── Filter bar ───────────────────────────────────────────────────────────────

function FilterBar({
  clusters,
  selectedWorldId,
  onSelect,
}: {
  clusters: { label: string; world_id: string }[]
  selectedWorldId: string | null
  onSelect: (worldId: string | null) => void
}) {
  if (clusters.length <= 1) return null

  return (
    <div className="absolute top-4 left-4 z-10 flex flex-wrap gap-1.5 max-w-[calc(100%-120px)]">
      <button
        onClick={() => onSelect(null)}
        className={`px-2 py-1 text-[10px] font-mono tracking-wider transition-colors border ${
          selectedWorldId === null
            ? 'border-neon-cyan text-neon-cyan bg-neon-cyan/10'
            : 'border-white/20 text-zinc-400 hover:border-white/40'
        }`}
      >
        ALL
      </button>
      {clusters.map((c) => (
        <button
          key={c.world_id}
          onClick={() => onSelect(c.world_id === selectedWorldId ? null : c.world_id)}
          className={`px-2 py-1 text-[10px] font-mono tracking-wider transition-colors border truncate max-w-[120px] ${
            selectedWorldId === c.world_id
              ? 'border-neon-purple text-neon-purple bg-neon-purple/10'
              : 'border-white/20 text-zinc-400 hover:border-white/40'
          }`}
        >
          {c.label}
        </button>
      ))}
    </div>
  )
}

// ── D3 simulation node type ──────────────────────────────────────────────────

interface SimNode extends DwellerGraphNode, d3.SimulationNodeDatum {
  color: string
  _dragStartX?: number
  _dragStartY?: number
  _wasDragged?: boolean
}

interface SimLink extends d3.SimulationLinkDatum<SimNode> {
  weight: number
  stories: string[]
  edge: DwellerGraphEdge
  sourceNode: SimNode
  targetNode: SimNode
}

// ── Main canvas ──────────────────────────────────────────────────────────────

export function DwellerGraphCanvas() {
  const svgRef = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const router = useRouter()
  const simulationRef = useRef<d3.Simulation<SimNode, SimLink> | null>(null)

  const [data, setData] = useState<DwellerGraphResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedWorldId, setSelectedWorldId] = useState<string | null>(null)
  const [tooltip, setTooltip] = useState<TooltipState>({ node: null, edge: null, pos: { x: 0, y: 0 } })
  const [dims, setDims] = useState<{ width: number; height: number } | null>(null)

  // Fetch graph data
  useEffect(() => {
    async function load() {
      try {
        const result = await getDwellerGraph({ min_weight: 1 })
        setData(result)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load graph')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  // Observe container dimensions
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const measure = () => {
      const w = el.clientWidth
      const h = el.clientHeight
      if (w > 0 && h > 0) {
        setDims((prev) => {
          if (prev && prev.width === w && prev.height === h) return prev
          return { width: w, height: h }
        })
      }
    }
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  // Derive filtered data based on selectedWorldId (O(1) edge lookup via Map)
  const filteredData = data
    ? (() => {
        if (!selectedWorldId) return { nodes: data.nodes, edges: data.edges, clusters: data.clusters }
        const worldNodes = data.nodes.filter((n) => n.world_id === selectedWorldId)
        const nodeSet = new Set(worldNodes.map((n) => n.id))
        return {
          nodes: worldNodes,
          edges: data.edges.filter((e) => nodeSet.has(e.source) && nodeSet.has(e.target)),
          clusters: data.clusters,
        }
      })()
    : null

  // Draw D3 graph
  const drawGraph = useCallback(() => {
    if (!filteredData || !svgRef.current || !dims) return

    const { width, height } = dims
    const { nodes: rawNodes, edges: rawEdges, clusters } = filteredData

    // Stop previous simulation
    simulationRef.current?.stop()

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()
    svg.attr('width', width).attr('height', height)

    if (rawNodes.length === 0) return

    // Build world color map
    const allWorldIds = Array.from(new Set(data!.nodes.map((n) => n.world_id)))
    const colorMap: Record<string, string> = {}
    allWorldIds.forEach((wid) => { colorMap[wid] = worldColor(wid, allWorldIds) })

    // Prepare sim nodes/links
    const nodeMap = new Map<string, SimNode>()
    const simNodes: SimNode[] = rawNodes.map((n) => {
      const sn: SimNode = { ...n, color: colorMap[n.world_id] ?? '#888' }
      nodeMap.set(n.id, sn)
      return sn
    })

    const simLinks: SimLink[] = rawEdges
      .map((e) => {
        const src = nodeMap.get(e.source)
        const tgt = nodeMap.get(e.target)
        if (!src || !tgt) return null
        return {
          source: src,
          target: tgt,
          weight: e.weight,
          stories: e.stories,
          edge: e,
          sourceNode: src,
          targetNode: tgt,
        } as SimLink
      })
      .filter(Boolean) as SimLink[]

    // ── Zoom + pan ─────────────────────────────────────────────────────────
    const g = svg.append('g')
    const zoom = d3.zoom<SVGSVGElement, unknown>().scaleExtent([0.2, 8]).on('zoom', (event) => {
      g.attr('transform', event.transform)
    })
    svg.call(zoom)

    // ── Starfield background ────────────────────────────────────────────────
    const rng = d3.randomLcg(0xcafebabe)
    const stars = d3.range(80).map(() => ({
      x: rng() * width,
      y: rng() * height,
      r: rng() * 1.0 + 0.2,
      opacity: rng() * 0.4 + 0.05,
    }))
    g.append('g')
      .selectAll('circle')
      .data(stars)
      .join('circle')
      .attr('cx', (d) => d.x)
      .attr('cy', (d) => d.y)
      .attr('r', (d) => d.r)
      .attr('fill', '#F4F4F5')
      .attr('opacity', (d) => d.opacity)

    // ── Defs: clip paths for portrait images ────────────────────────────────
    const defs = svg.append('defs')
    const NODE_R = 22

    simNodes.forEach((n) => {
      defs
        .append('clipPath')
        .attr('id', `clip-${n.id}`)
        .append('circle')
        .attr('cx', 0)
        .attr('cy', 0)
        .attr('r', NODE_R)
    })

    // ── Edge lines ──────────────────────────────────────────────────────────
    const maxWeight = Math.max(1, ...simLinks.map((l) => l.weight))

    const edgeG = g.append('g').attr('class', 'edges')
    const edgeSel = edgeG
      .selectAll<SVGLineElement, SimLink>('line')
      .data(simLinks)
      .join('line')
      // Asymmetric edges: amber dashed; balanced: white solid
      .attr('stroke', (d) => isAsymmetric(d.edge) ? '#ff9500' : '#ffffff')
      .attr('stroke-opacity', (d) => 0.08 + 0.28 * (d.weight / maxWeight))
      .attr('stroke-width', (d) => 0.5 + 3.5 * (d.weight / maxWeight))
      .attr('stroke-dasharray', (d) => isAsymmetric(d.edge) ? '4 3' : null)
      .style('cursor', 'pointer')
      .on('mouseenter', function (event, d) {
        d3.select(this).attr('stroke-opacity', 0.7)
        const rect = containerRef.current?.getBoundingClientRect()
        setTooltip({
          node: null,
          edge: { source: d.sourceNode, target: d.targetNode, edge: d.edge },
          pos: { x: event.clientX - (rect?.left ?? 0), y: event.clientY - (rect?.top ?? 0) },
        })
      })
      .on('mousemove', function (event) {
        updateTooltipPos(event.clientX, event.clientY)
      })
      .on('mouseleave', function (_, d) {
        d3.select(this).attr('stroke-opacity', 0.08 + 0.28 * (d.weight / maxWeight))
        setTooltip({ node: null, edge: null, pos: { x: 0, y: 0 } })
      })

    // ── Directional arrows on asymmetric edges ──────────────────────────────
    const arrowG = g.append('g').attr('class', 'arrows').attr('pointer-events', 'none')
    const asymLinks = simLinks.filter((l) => isAsymmetric(l.edge))

    const arrowSel = arrowG
      .selectAll<SVGPolygonElement, SimLink>('polygon')
      .data(asymLinks)
      .join('polygon')
      .attr('points', '0,-4 8,0 0,4')
      .attr('fill', '#ff9500')
      .attr('fill-opacity', 0.65)

    // ── Node groups ─────────────────────────────────────────────────────────
    const nodeG = g.append('g').attr('class', 'nodes')
    const nodeSel = nodeG
      .selectAll<SVGGElement, SimNode>('g')
      .data(simNodes)
      .join('g')
      .style('cursor', 'pointer')

    // Glow ring
    nodeSel
      .append('circle')
      .attr('r', NODE_R + 4)
      .attr('fill', 'none')
      .attr('stroke', (d) => d.color)
      .attr('stroke-width', 0.8)
      .attr('opacity', 0.35)

    // Portrait or initial
    nodeSel.each(function (d) {
      const g = d3.select(this)
      if (d.portrait_url) {
        g.append('image')
          .attr('href', d.portrait_url)
          .attr('x', -NODE_R)
          .attr('y', -NODE_R)
          .attr('width', NODE_R * 2)
          .attr('height', NODE_R * 2)
          .attr('clip-path', `url(#clip-${d.id})`)
          .attr('preserveAspectRatio', 'xMidYMid slice')
      } else {
        // Fallback circle + initial
        g.append('circle')
          .attr('r', NODE_R)
          .attr('fill', d.color)
          .attr('fill-opacity', 0.25)
          .attr('stroke', d.color)
          .attr('stroke-width', 1.5)
        g.append('text')
          .attr('text-anchor', 'middle')
          .attr('dominant-baseline', 'central')
          .attr('fill', d.color)
          .attr('font-size', 14)
          .attr('font-family', 'monospace')
          .attr('pointer-events', 'none')
          .text(d.name.charAt(0))
      }
    })

    // Name label below node
    const isMobile = width < 768
    if (!isMobile) {
      nodeSel
        .append('text')
        .attr('y', NODE_R + 12)
        .attr('text-anchor', 'middle')
        .attr('fill', '#D4D4D8')
        .attr('font-size', 9)
        .attr('font-family', 'monospace')
        .attr('letter-spacing', '0.08em')
        .attr('pointer-events', 'none')
        .text((d) => d.name.toUpperCase())
    }

    // ── RAF-throttled tooltip position update ────────────────────────────────
    let rafId: number | null = null
    const updateTooltipPos = (clientX: number, clientY: number) => {
      if (rafId !== null) cancelAnimationFrame(rafId)
      rafId = requestAnimationFrame(() => {
        const rect = containerRef.current?.getBoundingClientRect()
        setTooltip((prev) => ({
          ...prev,
          pos: { x: clientX - (rect?.left ?? 0), y: clientY - (rect?.top ?? 0) },
        }))
        rafId = null
      })
    }

    // ── Interactions ─────────────────────────────────────────────────────────

    // Touch tap tracking (mobile — touchstart/touchend with distance threshold)
    let _touchStartX = 0
    let _touchStartY = 0

    nodeSel
      .on('mouseenter', function (event, d) {
        d3.select(this).select('circle').transition().duration(120).attr('r', NODE_R + 6)
        const rect = containerRef.current?.getBoundingClientRect()
        setTooltip({
          node: d,
          edge: null,
          pos: { x: event.clientX - (rect?.left ?? 0), y: event.clientY - (rect?.top ?? 0) },
        })
      })
      .on('mousemove', function (event) {
        updateTooltipPos(event.clientX, event.clientY)
      })
      .on('mouseleave', function () {
        d3.select(this).select('circle').transition().duration(120).attr('r', NODE_R + 4)
        setTooltip({ node: null, edge: null, pos: { x: 0, y: 0 } })
      })
      .on('click', (_, d) => {
        // Only navigate if the node was not meaningfully dragged
        if (!d._wasDragged) router.push(`/dweller/${d.id}`)
      })
      .on('touchstart.tap', function (event) {
        const te = event as unknown as TouchEvent
        const t = te.touches[0]
        _touchStartX = t.clientX
        _touchStartY = t.clientY
      })
      .on('touchend.tap', function (event, d) {
        const te = event as unknown as TouchEvent
        const t = te.changedTouches[0]
        const dx = t.clientX - _touchStartX
        const dy = t.clientY - _touchStartY
        if (Math.sqrt(dx * dx + dy * dy) < 10) {
          router.push(`/dweller/${d.id}`)
        }
      })

    // ── Drag ─────────────────────────────────────────────────────────────────
    const drag = d3
      .drag<SVGGElement, SimNode>()
      .on('start', (event, d) => {
        d._dragStartX = event.x
        d._dragStartY = event.y
        d._wasDragged = false
        if (!event.active) simulation.alphaTarget(0.3).restart()
        d.fx = d.x
        d.fy = d.y
      })
      .on('drag', (event, d) => {
        const dx = event.x - (d._dragStartX ?? event.x)
        const dy = event.y - (d._dragStartY ?? event.y)
        if (Math.sqrt(dx * dx + dy * dy) > 5) d._wasDragged = true
        d.fx = event.x
        d.fy = event.y
      })
      .on('end', (event, d) => {
        if (!event.active) {
          simulation.alphaTarget(0)
          // Cap alpha so the simulation settles quickly after drag instead of jittering
          if (simulation.alpha() > 0.1) simulation.alpha(0.1)
        }
        d.fx = null
        d.fy = null
      })

    nodeSel.call(drag)

    // ── Force simulation ──────────────────────────────────────────────────────
    const simulation = d3
      .forceSimulation<SimNode>(simNodes)
      .alphaDecay(0.05) // 2x faster than default (0.0228) — settles quickly, less jitter
      .force(
        'link',
        d3
          .forceLink<SimNode, SimLink>(simLinks)
          .id((d) => d.id)
          .distance((d) => Math.max(80, 160 - d.weight * 15))
          .strength(0.4)
      )
      .force('charge', d3.forceManyBody().strength(-200))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide<SimNode>(NODE_R + 8))
      // Group same-world nodes loosely together
      .force('world-x', d3.forceX<SimNode>().x((d) => {
        const idx = allWorldIds.indexOf(d.world_id)
        const cols = Math.ceil(Math.sqrt(allWorldIds.length))
        return ((idx % cols) / cols + 0.5 / cols) * width
      }).strength(0.04))
      .force('world-y', d3.forceY<SimNode>().y((d) => {
        const idx = allWorldIds.indexOf(d.world_id)
        const cols = Math.ceil(Math.sqrt(allWorldIds.length))
        const row = Math.floor(idx / cols)
        const rows = Math.ceil(allWorldIds.length / cols)
        return ((row / rows) + 0.5 / rows) * height
      }).strength(0.04))

    simulationRef.current = simulation

    // After initial layout settles (~2s with alphaDecay 0.05), hard-stop any residual jitter
    const settleTimer = setTimeout(() => {
      if (simulationRef.current === simulation && simulation.alpha() < 0.05) {
        simulation.alpha(0)
      }
    }, 2000)

    simulation.on('tick', () => {
      edgeSel
        .attr('x1', (d) => (d.source as SimNode).x ?? 0)
        .attr('y1', (d) => (d.source as SimNode).y ?? 0)
        .attr('x2', (d) => (d.target as SimNode).x ?? 0)
        .attr('y2', (d) => (d.target as SimNode).y ?? 0)

      nodeSel.attr('transform', (d) => `translate(${d.x ?? 0},${d.y ?? 0})`)

      // Position directional arrows along asymmetric edges
      arrowSel.attr('transform', (d) => {
        const src = d.source as SimNode
        const tgt = d.target as SimNode
        const sx = src.x ?? 0
        const sy = src.y ?? 0
        const tx = tgt.x ?? 0
        const ty = tgt.y ?? 0
        const dx = tx - sx
        const dy = ty - sy
        const angle = (Math.atan2(dy, dx) * 180) / Math.PI

        // Place arrow at 65% along the edge in dominant direction
        const dir = dominantDirection(d.edge)
        const fraction = dir === 'b_to_a' ? 0.35 : 0.65
        const mx = sx + dx * fraction
        const my = sy + dy * fraction

        // Flip arrow if dominant direction is b→a (reversed)
        const rotate = dir === 'b_to_a' ? angle + 180 : angle
        return `translate(${mx},${my}) rotate(${rotate})`
      })
    })

    return () => {
      simulation.stop()
      clearTimeout(settleTimer)
      if (rafId !== null) cancelAnimationFrame(rafId)
    }
  }, [filteredData, dims, router, data])

  useEffect(() => {
    drawGraph()
    return () => {
      simulationRef.current?.stop()
    }
  }, [drawGraph])

  // Build color map for Legend
  const allWorldIds = data ? Array.from(new Set(data.nodes.map((n) => n.world_id))) : []
  const colorMap: Record<string, string> = {}
  allWorldIds.forEach((wid) => { colorMap[wid] = worldColor(wid, allWorldIds) })

  const displayedNodes = filteredData?.nodes ?? []
  const displayedEdges = filteredData?.edges ?? []

  return (
    <div ref={containerRef} className="relative w-full h-full bg-bg-primary overflow-hidden">
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-neon-purple text-xs font-mono tracking-widest animate-pulse">
            MAPPING CONNECTIONS…
          </div>
        </div>
      )}

      {error && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="glass-cyan p-6 max-w-sm text-center">
            <p className="text-neon-pink text-xs font-mono mb-2">GRAPH UNAVAILABLE</p>
            <p className="text-text-tertiary text-xs">{error}</p>
          </div>
        </div>
      )}

      {!loading && !error && data && data.nodes.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center">
          <p className="text-text-tertiary text-xs font-mono">
            No dwellers yet. Check back once worlds are populated.
          </p>
        </div>
      )}

      {!loading && !error && data && data.nodes.length > 0 && (
        <>
          <svg ref={svgRef} className="absolute inset-0 w-full h-full" />

          <FilterBar
            clusters={data.clusters}
            selectedWorldId={selectedWorldId}
            onSelect={setSelectedWorldId}
          />

          {/* Controls hint — desktop */}
          <div className="absolute top-4 right-4 z-10 text-zinc-400 text-[10px] font-mono space-y-0.5 hidden md:block">
            <div>scroll — zoom</div>
            <div>drag — pan / move</div>
            <div>click — dweller detail</div>
            <div className="mt-1 text-zinc-600">— — asymmetric speaks</div>
          </div>

          {/* Controls hint — mobile */}
          <div className="absolute top-4 right-4 z-10 text-zinc-400 text-[10px] font-mono md:hidden">
            pinch — zoom · tap — detail
          </div>

          <Legend
            clusters={data.clusters}
            colorMap={colorMap}
            nodeCount={displayedNodes.length}
            edgeCount={displayedEdges.length}
          />

          <Tooltip state={tooltip} containerRef={containerRef} />
        </>
      )}
    </div>
  )
}
