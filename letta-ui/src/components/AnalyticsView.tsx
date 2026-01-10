import React, { useEffect, useState, useMemo } from 'react';
import { api } from '../lib/api';
import { UMAP } from 'umap-js';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  ScatterChart,
  Scatter,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { scaleLinear } from 'd3-scale';
import { interpolateRdYlGn } from 'd3-interpolate';
import ReactWordcloud from 'react-wordcloud';

interface TrajectoryWithEmbedding {
  id: string;
  agent_id: string;
  searchable_summary?: string;
  outcome_score?: number;
  tags?: string[];
  task_category?: string;
  complexity_level?: string;
  embedding?: number[];
  created_at: string;
  processing_status: string;
  data: any;
}

interface AnalyticsAggregations {
  total_count: number;
  score_distribution: Record<string, number>;
  turn_distribution: Record<string, number>;
  tool_usage: Record<string, number>;
  tags_frequency: Record<string, number>;
  category_breakdown: Record<string, number>;
  complexity_breakdown: Record<string, number>;
  daily_counts: Array<{ date: string; count: number; avg_score?: number }>;
  agent_stats: Record<string, { count: number; avg_score?: number }>;
}

interface OTSAnalytics {
  decision_success_rate: Record<string, number>;
  action_frequency: Record<string, number>;
  decision_type_breakdown: Record<string, number>;
  turn_distribution: Record<string, number>;
  error_type_frequency: Record<string, number>;
  trajectory_outcomes: Record<string, number>;
  total_trajectories: number;
  total_turns: number;
  total_decisions: number;
  total_messages: number;
  avg_turns_per_trajectory: number;
  avg_decisions_per_turn: number;
  overall_success_rate: number;
}

export function AnalyticsView() {
  const [trajectories, setTrajectories] = useState<TrajectoryWithEmbedding[]>([]);
  const [aggregations, setAggregations] = useState<AnalyticsAggregations | null>(null);
  const [otsAnalytics, setOtsAnalytics] = useState<OTSAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTrajectory, setSelectedTrajectory] = useState<string | null>(null);
  const [umapProjection, setUmapProjection] = useState<Array<[number, number]>>([]);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      setLoading(true);
      const [trajsData, aggsData, otsData] = await Promise.all([
        api.getTrajectoriesWithEmbeddings({ limit: 500 }),
        api.getTrajectoryAggregations(),
        api.getOTSAnalytics({ limit: 500 }),
      ]);
      setTrajectories(trajsData);
      setAggregations(aggsData);
      setOtsAnalytics(otsData);

      // Compute UMAP projection if we have embeddings
      if (trajsData.length > 0 && trajsData[0].embedding) {
        computeUMAPProjection(trajsData);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  }

  function computeUMAPProjection(trajs: TrajectoryWithEmbedding[]) {
    const embeddings = trajs
      .filter(t => t.embedding && t.embedding.length > 0)
      .map(t => t.embedding!);

    if (embeddings.length < 3) {
      console.warn('Not enough trajectories with embeddings for UMAP');
      return;
    }

    try {
      const umap = new UMAP({
        nComponents: 2,
        nNeighbors: Math.min(15, embeddings.length - 1),
        minDist: 0.1,
        spread: 1.0,
      });

      const projection = umap.fit(embeddings);
      setUmapProjection(projection);
    } catch (err) {
      console.error('UMAP projection failed:', err);
    }
  }

  // Color scale for outcome scores
  const scoreColorScale = useMemo(() => {
    return scaleLinear<string>()
      .domain([0, 0.5, 1])
      .range(['#ff0055', '#ffff00', '#00ff88']);
  }, []);

  // Prepare data for charts
  const scoreDistData = useMemo(() => {
    if (!aggregations) return [];
    return Object.entries(aggregations.score_distribution)
      .map(([range, count]) => ({ range, count }))
      .sort((a, b) => a.range.localeCompare(b.range));
  }, [aggregations]);

  const turnDistData = useMemo(() => {
    if (!aggregations) return [];
    return Object.entries(aggregations.turn_distribution)
      .map(([turns, count]) => ({ turns: parseInt(turns), count }))
      .sort((a, b) => a.turns - b.turns)
      .slice(0, 15); // Limit to first 15 for readability
  }, [aggregations]);

  const toolUsageData = useMemo(() => {
    if (!aggregations) return [];
    return Object.entries(aggregations.tool_usage)
      .map(([tool, count]) => ({ tool, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10); // Top 10 tools
  }, [aggregations]);

  const categoryData = useMemo(() => {
    if (!aggregations) return [];
    return Object.entries(aggregations.category_breakdown).map(([name, value]) => ({
      name,
      value,
    }));
  }, [aggregations]);

  const complexityData = useMemo(() => {
    if (!aggregations) return [];
    return Object.entries(aggregations.complexity_breakdown).map(([name, value]) => ({
      name,
      value,
    }));
  }, [aggregations]);

  const tagsWordData = useMemo(() => {
    if (!aggregations) return [];
    return Object.entries(aggregations.tags_frequency).map(([text, value]) => ({
      text,
      value,
    }));
  }, [aggregations]);

  // OTS Analytics data
  const otsActionFrequencyData = useMemo(() => {
    if (!otsAnalytics) return [];
    return Object.entries(otsAnalytics.action_frequency)
      .map(([action, count]) => ({ action, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);
  }, [otsAnalytics]);

  const otsSuccessRateData = useMemo(() => {
    if (!otsAnalytics) return [];
    return Object.entries(otsAnalytics.decision_success_rate)
      .map(([action, rate]) => ({
        action,
        rate: Math.round(rate * 100),
        success: Math.round(rate * 100),
        failure: Math.round((1 - rate) * 100),
      }))
      .sort((a, b) => b.rate - a.rate)
      .slice(0, 10);
  }, [otsAnalytics]);

  const otsDecisionTypeData = useMemo(() => {
    if (!otsAnalytics) return [];
    return Object.entries(otsAnalytics.decision_type_breakdown).map(([name, value]) => ({
      name,
      value,
    }));
  }, [otsAnalytics]);

  const otsErrorTypeData = useMemo(() => {
    if (!otsAnalytics) return [];
    return Object.entries(otsAnalytics.error_type_frequency)
      .map(([error, count]) => ({ error, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8);
  }, [otsAnalytics]);

  const otsOutcomeData = useMemo(() => {
    if (!otsAnalytics) return [];
    return Object.entries(otsAnalytics.trajectory_outcomes).map(([name, value]) => ({
      name,
      value,
    }));
  }, [otsAnalytics]);

  const timeSeriesData = useMemo(() => {
    if (!aggregations) return [];
    return aggregations.daily_counts.map(d => ({
      date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      count: d.count,
      score: d.avg_score ? (d.avg_score * 100).toFixed(0) : null,
    }));
  }, [aggregations]);

  // Semantic map data
  const semanticMapData = useMemo(() => {
    if (umapProjection.length === 0 || trajectories.length === 0) return [];

    return trajectories
      .filter(t => t.embedding)
      .map((t, i) => {
        if (i >= umapProjection.length) return null;
        const [x, y] = umapProjection[i];
        const score = t.outcome_score ?? 0.5;
        const turns = t.data?.turns?.length ?? 1;

        return {
          id: t.id,
          x,
          y,
          score,
          size: Math.max(50, turns * 20),
          color: scoreColorScale(score),
          summary: t.searchable_summary?.slice(0, 100) + '...',
          tags: t.tags?.slice(0, 3).join(', '),
          category: t.task_category,
        };
      })
      .filter(Boolean);
  }, [trajectories, umapProjection, scoreColorScale]);

  if (loading) {
    return <div className="loading">Loading analytics...</div>;
  }

  if (error) {
    return (
      <div className="card" style={{ background: 'rgba(255, 0, 255, 0.1)', color: 'var(--magenta)' }}>
        {error}
      </div>
    );
  }

  if (!aggregations || trajectories.length === 0) {
    return (
      <div className="card">
        <h2 className="section-title">No Data Available</h2>
        <p style={{ color: 'var(--text-secondary)' }}>
          Create some trajectories first by running agents. Trajectories will appear here once they've been processed.
        </p>
      </div>
    );
  }

  const COLORS = ['#00ff88', '#00e5ff', '#ff00ff', '#ffff00', '#ff0055'];

  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h2 className="section-title">Trajectory Analytics</h2>
        <p className="section-subtitle">
          Comprehensive analysis of {aggregations.total_count} agent execution traces
        </p>
      </div>

      {/* Overview Stats */}
      <div className="stats-grid" style={{ marginBottom: '2rem' }}>
        <div className="stat-card">
          <div className="stat-value color-teal">{aggregations.total_count}</div>
          <div className="stat-label">Total Trajectories</div>
        </div>
        <div className="stat-card">
          <div className="stat-value color-green">
            {Object.values(aggregations.agent_stats).length}
          </div>
          <div className="stat-label">Active Agents</div>
        </div>
        <div className="stat-card">
          <div className="stat-value color-magenta">
            {Object.keys(aggregations.tool_usage).length}
          </div>
          <div className="stat-label">Tools Used</div>
        </div>
        <div className="stat-card">
          <div className="stat-value color-lemon">
            {Object.keys(aggregations.tags_frequency).length}
          </div>
          <div className="stat-label">Unique Tags</div>
        </div>
      </div>

      {/* Semantic Map */}
      {semanticMapData.length > 0 && (
        <div className="card" style={{ marginBottom: '2rem' }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.5rem' }}>
            🗺️ Semantic Map
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
            Trajectories positioned by semantic similarity (UMAP projection). Color = outcome score,
            Size = interaction depth.
          </p>
          <ResponsiveContainer width="100%" height={500}>
            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis
                type="number"
                dataKey="x"
                name="UMAP-1"
                stroke="var(--text-tertiary)"
                tick={{ fill: 'var(--text-tertiary)', fontSize: 12 }}
              />
              <YAxis
                type="number"
                dataKey="y"
                name="UMAP-2"
                stroke="var(--text-tertiary)"
                tick={{ fill: 'var(--text-tertiary)', fontSize: 12 }}
              />
              <Tooltip
                cursor={{ strokeDasharray: '3 3' }}
                content={({ active, payload }) => {
                  if (active && payload && payload[0]) {
                    const data = payload[0].payload;
                    return (
                      <div
                        style={{
                          background: '#000',
                          border: '1px solid var(--neon-green)',
                          padding: '0.75rem',
                          maxWidth: '300px',
                        }}
                      >
                        <div style={{ color: 'var(--neon-green)', marginBottom: '0.5rem', fontWeight: 600 }}>
                          Score: {data.score.toFixed(2)}
                        </div>
                        {data.category && (
                          <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                            Category: {data.category}
                          </div>
                        )}
                        {data.tags && (
                          <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', marginBottom: '0.5rem' }}>
                            Tags: {data.tags}
                          </div>
                        )}
                        <div style={{ color: 'var(--text-tertiary)', fontSize: '0.75rem' }}>
                          {data.summary}
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Scatter
                data={semanticMapData}
                fill="#8884d8"
                onClick={(data) => setSelectedTrajectory(data.id)}
              >
                {semanticMapData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Time Series */}
      <div className="card" style={{ marginBottom: '2rem' }}>
        <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.5rem' }}>
          📈 Trajectory Activity Over Time
        </h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
          Daily trajectory count and average outcome score (last 30 days)
        </p>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={timeSeriesData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
            <XAxis
              dataKey="date"
              stroke="var(--text-tertiary)"
              tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }}
            />
            <YAxis
              yAxisId="left"
              stroke="var(--neon-teal)"
              tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              stroke="var(--neon-green)"
              tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }}
            />
            <Tooltip
              contentStyle={{
                background: '#000',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-primary)',
              }}
            />
            <Legend />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="count"
              stroke="var(--neon-teal)"
              strokeWidth={2}
              dot={{ fill: 'var(--neon-teal)', r: 4 }}
              name="Count"
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="score"
              stroke="var(--neon-green)"
              strokeWidth={2}
              dot={{ fill: 'var(--neon-green)', r: 4 }}
              name="Avg Score (%)"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Distribution Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
        {/* Score Distribution */}
        <div className="card">
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>
            Score Distribution
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={scoreDistData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis
                dataKey="range"
                stroke="var(--text-tertiary)"
                tick={{ fill: 'var(--text-tertiary)', fontSize: 10 }}
              />
              <YAxis stroke="var(--text-tertiary)" tick={{ fill: 'var(--text-tertiary)', fontSize: 10 }} />
              <Tooltip
                contentStyle={{
                  background: '#000',
                  border: '1px solid var(--border-subtle)',
                }}
              />
              <Bar dataKey="count" fill="var(--neon-green)" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Turn Distribution */}
        <div className="card">
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>
            Interaction Depth (Turns)
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={turnDistData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis
                dataKey="turns"
                stroke="var(--text-tertiary)"
                tick={{ fill: 'var(--text-tertiary)', fontSize: 10 }}
              />
              <YAxis stroke="var(--text-tertiary)" tick={{ fill: 'var(--text-tertiary)', fontSize: 10 }} />
              <Tooltip
                contentStyle={{
                  background: '#000',
                  border: '1px solid var(--border-subtle)',
                }}
              />
              <Bar dataKey="count" fill="var(--neon-teal)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Tool Usage and Categories */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
        {/* Tool Usage */}
        <div className="card">
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>
            🛠️ Tool Usage (Top 10)
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={toolUsageData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis
                type="number"
                stroke="var(--text-tertiary)"
                tick={{ fill: 'var(--text-tertiary)', fontSize: 10 }}
              />
              <YAxis
                type="category"
                dataKey="tool"
                stroke="var(--text-tertiary)"
                tick={{ fill: 'var(--text-tertiary)', fontSize: 10 }}
                width={120}
              />
              <Tooltip
                contentStyle={{
                  background: '#000',
                  border: '1px solid var(--border-subtle)',
                }}
              />
              <Bar dataKey="count" fill="var(--neon-magenta)" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Task Categories */}
        <div className="card">
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>
            📑 Task Categories
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={categoryData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {categoryData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: '#000',
                  border: '1px solid var(--border-subtle)',
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Tags Word Cloud */}
      {tagsWordData.length > 0 && (
        <div className="card" style={{ marginBottom: '2rem' }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '1rem' }}>
            ☁️ Tags Word Cloud
          </h3>
          <div style={{ height: '400px', background: 'rgba(0, 0, 0, 0.3)', padding: '1rem' }}>
            <ReactWordcloud
              words={tagsWordData}
              options={{
                rotations: 2,
                rotationAngles: [0, 90],
                fontSizes: [14, 60],
                fontFamily: 'Berkeley Mono, monospace',
                colors: ['#00ff88', '#00e5ff', '#ff00ff', '#ffff00', '#ff0055'],
                enableTooltip: true,
                deterministic: true,
                padding: 2,
              }}
            />
          </div>
        </div>
      )}

      {/* Complexity Breakdown */}
      {complexityData.length > 0 && (
        <div className="card">
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>
            🎯 Complexity Level Distribution
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={complexityData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis
                dataKey="name"
                stroke="var(--text-tertiary)"
                tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }}
              />
              <YAxis stroke="var(--text-tertiary)" tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  background: '#000',
                  border: '1px solid var(--border-subtle)',
                }}
              />
              <Bar dataKey="value" fill="var(--neon-lemon)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Pure OTS Analytics Section */}
      {otsAnalytics && (
        <>
          <div style={{ marginTop: '3rem', marginBottom: '2rem', borderTop: '1px solid var(--border-subtle)', paddingTop: '2rem' }}>
            <h2 className="section-title">Pure OTS Analytics</h2>
            <p className="section-subtitle">
              Decision-level analytics from raw OTS data (no LLM enrichment required)
            </p>
          </div>

          {/* OTS Overview Stats */}
          <div className="stats-grid" style={{ marginBottom: '2rem' }}>
            <div className="stat-card">
              <div className="stat-value color-teal">{otsAnalytics.total_decisions}</div>
              <div className="stat-label">Total Decisions</div>
            </div>
            <div className="stat-card">
              <div className="stat-value color-green">
                {(otsAnalytics.overall_success_rate * 100).toFixed(1)}%
              </div>
              <div className="stat-label">Success Rate</div>
            </div>
            <div className="stat-card">
              <div className="stat-value color-magenta">
                {otsAnalytics.avg_decisions_per_turn.toFixed(1)}
              </div>
              <div className="stat-label">Avg Decisions/Turn</div>
            </div>
            <div className="stat-card">
              <div className="stat-value color-lemon">
                {otsAnalytics.total_messages}
              </div>
              <div className="stat-label">Total Messages</div>
            </div>
          </div>

          {/* Decision Success Rate and Action Frequency */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
            {/* Decision Success Rate */}
            {otsSuccessRateData.length > 0 && (
              <div className="card">
                <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>
                  ✅ Decision Success Rate by Action
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={otsSuccessRateData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                    <XAxis
                      type="number"
                      domain={[0, 100]}
                      stroke="var(--text-tertiary)"
                      tick={{ fill: 'var(--text-tertiary)', fontSize: 10 }}
                      tickFormatter={(value) => `${value}%`}
                    />
                    <YAxis
                      type="category"
                      dataKey="action"
                      stroke="var(--text-tertiary)"
                      tick={{ fill: 'var(--text-tertiary)', fontSize: 10 }}
                      width={120}
                    />
                    <Tooltip
                      contentStyle={{
                        background: '#000',
                        border: '1px solid var(--border-subtle)',
                      }}
                      formatter={(value: number) => [`${value}%`, 'Success Rate']}
                    />
                    <Bar dataKey="rate" fill="var(--neon-green)" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Action Frequency */}
            {otsActionFrequencyData.length > 0 && (
              <div className="card">
                <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>
                  📊 Action Frequency (Top 10)
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={otsActionFrequencyData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                    <XAxis
                      type="number"
                      stroke="var(--text-tertiary)"
                      tick={{ fill: 'var(--text-tertiary)', fontSize: 10 }}
                    />
                    <YAxis
                      type="category"
                      dataKey="action"
                      stroke="var(--text-tertiary)"
                      tick={{ fill: 'var(--text-tertiary)', fontSize: 10 }}
                      width={120}
                    />
                    <Tooltip
                      contentStyle={{
                        background: '#000',
                        border: '1px solid var(--border-subtle)',
                      }}
                    />
                    <Bar dataKey="count" fill="var(--neon-teal)" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {/* Decision Type and Outcomes */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
            {/* Decision Type Breakdown */}
            {otsDecisionTypeData.length > 0 && (
              <div className="card">
                <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>
                  🔀 Decision Type Breakdown
                </h3>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={otsDecisionTypeData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {otsDecisionTypeData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        background: '#000',
                        border: '1px solid var(--border-subtle)',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Trajectory Outcomes */}
            {otsOutcomeData.length > 0 && (
              <div className="card">
                <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>
                  🎯 Trajectory Outcomes
                </h3>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={otsOutcomeData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {otsOutcomeData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={
                            entry.name === 'success'
                              ? '#00ff88'
                              : entry.name === 'partial_success'
                              ? '#ffff00'
                              : entry.name === 'failure'
                              ? '#ff0055'
                              : COLORS[index % COLORS.length]
                          }
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        background: '#000',
                        border: '1px solid var(--border-subtle)',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {/* Error Type Frequency */}
          {otsErrorTypeData.length > 0 && (
            <div className="card">
              <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>
                ⚠️ Error Type Frequency
              </h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={otsErrorTypeData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis
                    dataKey="error"
                    stroke="var(--text-tertiary)"
                    tick={{ fill: 'var(--text-tertiary)', fontSize: 10 }}
                  />
                  <YAxis stroke="var(--text-tertiary)" tick={{ fill: 'var(--text-tertiary)', fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{
                      background: '#000',
                      border: '1px solid var(--border-subtle)',
                    }}
                  />
                  <Bar dataKey="count" fill="#ff0055" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </div>
  );
}
