/**
 * LiquidDemocracyPanel — simulates transitive vote delegation.
 * Voters either vote directly or delegate to a representative (who may
 * further delegate). Super-voters accumulate weight; cycles vote directly.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { useTranslation } from 'react-i18next';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Control, Range, Select } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
} from 'recharts';
import { useElection } from '../../stores/useElectionStore';
import { $api } from '../../api/hooks';
const DEBOUNCE_MS = 400;

// ── Types ─────────────────────────────────────────────────────────────────────

interface SuperVoter {
  id: number;
  weight: number;
  x: number;
  y: number;
  choice: string;
}

interface LiquidData {
  weighted_results: Record<string, number>;
  direct_voters: number;
  delegators: number;
  super_voters: SuperVoter[];
  delegation_graph: { from: number; to: number }[];
  cycles_detected: number;
  cycle_voter_ids: number[];
  chain_stats: { mean: number; max: number };
  gini_curve: { probability: number; gini: number }[];
  comparison: {
    liquid_winner: string;
    direct_winner: string;
    winner_changed: boolean;
  };
  gini_voting_weight: number;
  pedagogical_note: string;
}

// ── Palette ───────────────────────────────────────────────────────────────────

const CAND_COLORS = ['#005CAB', '#C8590A', '#007A33', '#6c757d', '#9b59b6', '#e67e22'];
function candColor(name: string, names: string[]): string {
  return CAND_COLORS[names.indexOf(name) % CAND_COLORS.length] ?? '#888';
}

// ── D3 Delegation Graph ───────────────────────────────────────────────────────

interface GraphNode extends d3.SimulationNodeDatum {
  id: number;
  weight: number;
  choice: string;
  isSuper: boolean;
  isCycle: boolean;
}

interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  source: number | GraphNode;
  target: number | GraphNode;
}

interface DelegationGraphProps {
  data: LiquidData;
  candidateNames: string[];
}

const DelegationGraph: React.FC<DelegationGraphProps> = ({ data, candidateNames }) => {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    if (!data.delegation_graph.length) return;

    const W = 560,
      H = 320;
    svg.attr('viewBox', `0 0 ${W} ${H}`);

    // Build node set (cap at 150 for performance)
    const superMap = new Map(data.super_voters.map((sv) => [sv.id, sv]));
    const cycleSet = new Set(data.cycle_voter_ids);
    const allNodeIds = new Set<number>();
    data.delegation_graph.forEach((e) => {
      allNodeIds.add(e.from);
      allNodeIds.add(e.to);
    });

    const nodes: GraphNode[] = Array.from(allNodeIds)
      .sort((a, b) => (superMap.get(b)?.weight ?? 1) - (superMap.get(a)?.weight ?? 1))
      .slice(0, 150)
      .map((id) => ({
        id,
        weight: superMap.get(id)?.weight ?? 1,
        choice: superMap.get(id)?.choice ?? '',
        isSuper: (superMap.get(id)?.weight ?? 0) > 10,
        isCycle: cycleSet.has(id),
      }));

    const nodeIds = new Set(nodes.map((n) => n.id));
    const links: GraphLink[] = data.delegation_graph
      .filter((e) => nodeIds.has(e.from) && nodeIds.has(e.to))
      .map((e) => ({ source: e.from, target: e.to }));

    // Arrow marker
    svg
      .append('defs')
      .append('marker')
      .attr('id', 'arrow')
      .attr('viewBox', '0 -3 6 6')
      .attr('refX', 10)
      .attr('refY', 0)
      .attr('markerWidth', 4)
      .attr('markerHeight', 4)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-3L6,0L0,3')
      .attr('fill', '#adb5bd');

    const sim = d3
      .forceSimulation<GraphNode>(nodes)
      .force(
        'link',
        d3
          .forceLink<GraphNode, GraphLink>(links)
          .id((d) => d.id)
          .distance(30)
      )
      .force('charge', d3.forceManyBody<GraphNode>().strength(-40))
      .force('center', d3.forceCenter(W / 2, H / 2))
      .force('collision', d3.forceCollide(10));

    const linkSel = svg
      .append('g')
      .selectAll<SVGLineElement, GraphLink>('line')
      .data(links)
      .join('line')
      .attr('stroke', '#ced4da')
      .attr('stroke-width', 0.8)
      .attr('marker-end', 'url(#arrow)');

    const nodeSel = svg.append('g').selectAll<SVGGElement, GraphNode>('g').data(nodes).join('g');

    // Super-voter crown ring
    nodeSel
      .filter((d) => d.isSuper)
      .append('circle')
      .attr('r', (d) => Math.sqrt(d.weight) * 3.5 + 3)
      .attr('fill', 'none')
      .attr('stroke', '#ffc107')
      .attr('stroke-width', 1.5)
      .attr('data-testid', 'super-voter-crown');

    // Cycle voter ring
    nodeSel
      .filter((d) => d.isCycle && !d.isSuper)
      .append('circle')
      .attr('r', 6)
      .attr('fill', 'none')
      .attr('stroke', '#dc3545')
      .attr('stroke-width', 1.5)
      .attr('data-testid', 'cycle-voter-ring');

    // Main dot
    nodeSel
      .append('circle')
      .attr('r', (d) => Math.max(3, Math.sqrt(d.weight) * 3))
      .attr('fill', (d) => candColor(d.choice, candidateNames))
      .attr('opacity', 0.85);

    sim.on('tick', () => {
      linkSel
        .attr('x1', (d) => (d.source as GraphNode).x ?? 0)
        .attr('y1', (d) => (d.source as GraphNode).y ?? 0)
        .attr('x2', (d) => (d.target as GraphNode).x ?? 0)
        .attr('y2', (d) => (d.target as GraphNode).y ?? 0);
      nodeSel.attr('transform', (d) => `translate(${d.x ?? 0},${d.y ?? 0})`);
    });

    return () => {
      sim.stop();
    };
  }, [data, candidateNames]);

  return (
    <svg
      ref={svgRef}
      data-testid="delegation-graph-svg"
      width="100%"
      height={320}
      style={{ display: 'block' }}
    />
  );
};

// ── Main panel ────────────────────────────────────────────────────────────────

const LiquidDemocracyPanel: React.FC = () => {
  const { t } = useTranslation();
  const { config } = useElection();

  const candidateNames = config.candidates.map((c) => c.name);

  const [delegProb, setDelegProb] = useState(0.5);
  const [strategy, setStrategy] = useState('nearest');
  const [maxChain, setMaxChain] = useState(5);
  const sim = $api.useMutation('post', '/api/v2/election/liquid-democracy');
  const data: LiquidData | null = (sim.data as LiquidData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('liquid.error') : null;
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const runSimulation = useCallback(
    (prob: number, strat: string, chain: number) => {
      sim.mutate({
        body: {
          candidates: config.candidates.map((c) => ({ name: c.name, x: c.x, y: c.y })),
          num_voters: config.num_voters,
          ideology: config.ideology,
          seed: config.seed,
          delegation_probability: prob,
          delegation_strategy: strat,
          max_chain_length: chain,
        },
      });
      // eslint-disable-next-line react-hooks/exhaustive-deps
    },
    [config, t, sim]
  );

  const handleSimulate = () => runSimulation(delegProb, strategy, maxChain);

  const handleProbChange = (v: number) => {
    setDelegProb(v);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runSimulation(v, strategy, maxChain), DEBOUNCE_MS);
  };

  const { comparison } = data ?? {};

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 items-end">
        <Col xs={12} md={4}>
          <label className="mb-1 inline-block text-sm mb-0">
            {t('liquid.probSlider')}: <strong>{Math.round(delegProb * 100)}%</strong>
          </label>
          <Range
            data-testid="delegation-prob-slider"
            min={0}
            max={1}
            step={0.05}
            value={delegProb}
            onChange={(e) => handleProbChange(Number(e.target.value))}
          />
        </Col>
        <Col xs={12} md={3}>
          <label className="mb-1 inline-block text-sm mb-0">{t('liquid.strategy')}</label>
          <Select
            size="sm"
            value={strategy}
            data-testid="strategy-select"
            onChange={(e) => setStrategy(e.target.value)}
          >
            <option value="nearest">{t('liquid.strategyNearest')}</option>
            <option value="most_competent">{t('liquid.strategyCompetent')}</option>
            <option value="random">{t('liquid.strategyRandom')}</option>
          </Select>
        </Col>
        <Col xs={6} md={2}>
          <label className="mb-1 inline-block text-sm mb-0">{t('liquid.maxChain')}</label>
          <Control
            type="number"
            size="sm"
            min={1}
            max={20}
            value={maxChain}
            onChange={(e) => setMaxChain(Math.max(1, Math.min(20, Number(e.target.value))))}
          />
        </Col>
        <Col xs="auto">
          <Button variant="primary" onClick={handleSimulate} disabled={loading}>
            {loading ? <Spinner size="sm" /> : t('liquid.run')}
          </Button>
        </Col>
      </Row>

      {!data && !loading && !error && (
        <Alert variant="info" role="alert">
          {t('liquid.prompt')}
        </Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}

      {data && comparison && (
        <>
          {/* Winner comparison */}
          <div
            className={`d-flex align-items-center justify-content-around p-3 rounded mb-3 ${
              comparison.winner_changed
                ? 'border border-border border-danger'
                : 'border border-border border-success'
            }`}
            data-testid="comparison-banner"
          >
            <div className="text-center">
              <div className="text-muted-foreground" style={{ fontSize: '0.72rem' }}>
                {t('liquid.directWinner')}
              </div>
              <Badge
                style={{
                  background: candColor(comparison.direct_winner, candidateNames),
                  fontSize: '0.85rem',
                  padding: '6px 12px',
                }}
                data-testid="direct-winner-badge"
              >
                {comparison.direct_winner}
              </Badge>
            </div>
            <span
              style={{
                fontSize: '1.4rem',
                color: comparison.winner_changed ? '#dc3545' : '#198754',
              }}
            >
              {comparison.winner_changed ? '⇒' : '='}
            </span>
            <div className="text-center">
              <div className="text-muted-foreground" style={{ fontSize: '0.72rem' }}>
                {t('liquid.liquidWinner')}
              </div>
              <Badge
                style={{
                  background: candColor(comparison.liquid_winner, candidateNames),
                  fontSize: '0.85rem',
                  padding: '6px 12px',
                }}
                data-testid="liquid-winner-badge"
              >
                {comparison.liquid_winner}
              </Badge>
            </div>
          </div>

          {/* Stats row */}
          <div className="flex flex-wrap gap-2 mb-3">
            <Badge variant="secondary" data-testid="gini-badge">
              Gini {data.gini_voting_weight.toFixed(3)}
            </Badge>
            <Badge variant="primary">
              {data.direct_voters} {t('liquid.directVoters')}
            </Badge>
            <Badge variant="info">
              {data.delegators} {t('liquid.delegators')}
            </Badge>
            {data.cycles_detected > 0 && (
              <Badge variant="danger" data-testid="cycles-badge">
                {data.cycles_detected} {t('liquid.cycles')}
              </Badge>
            )}
            {data.super_voters.length > 0 && (
              <Badge variant="warning" data-testid="super-voters-badge">
                {data.super_voters.length} {t('liquid.superVoters')} (max{' '}
                {data.super_voters[0]?.weight})
              </Badge>
            )}
            <Badge variant="light">
              {t('liquid.chainMax')} {data.chain_stats.max}
            </Badge>
          </div>

          {/* Delegation graph */}
          <div className="mb-3">
            <div className="font-semibold mb-1" style={{ fontSize: '0.85rem' }}>
              {t('liquid.graphTitle')}
            </div>
            <div
              className="border border-border rounded"
              style={{ background: '#f8f9fa', overflow: 'hidden' }}
            >
              <DelegationGraph data={data} candidateNames={candidateNames} />
            </div>
            <div className="flex gap-3 mt-1" style={{ fontSize: '0.72rem', color: '#6c757d' }}>
              <span>● {t('liquid.legendNode')}</span>
              <span style={{ color: '#ffc107' }}>◎ {t('liquid.legendSuper')}</span>
              <span style={{ color: '#dc3545' }}>◌ {t('liquid.legendCycle')}</span>
            </div>
          </div>

          {/* Gini curve */}
          <div data-testid="gini-curve-chart" className="mb-3">
            <div className="font-semibold mb-1" style={{ fontSize: '0.85rem' }}>
              {t('liquid.giniCurveTitle')}
            </div>
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={data.gini_curve} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="probability"
                  tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
                />
                <YAxis domain={[0, 1]} tickFormatter={(v: number) => v.toFixed(1)} />
                <Tooltip formatter={(v: number) => v.toFixed(3)} />
                <Line
                  type="monotone"
                  dataKey="gini"
                  name="Gini"
                  stroke="#6610f2"
                  dot={false}
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Pedagogical note */}
          <Alert variant="secondary" style={{ fontSize: '0.8rem' }}>
            <strong>{t('liquid.noteTitle')}</strong> {data.pedagogical_note}
          </Alert>
        </>
      )}
    </div>
  );
};

export default LiquidDemocracyPanel;
