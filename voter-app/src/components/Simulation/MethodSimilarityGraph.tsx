/**
 * MethodSimilarityGraph — D3 force-directed graph of voting-method similarity.
 *
 * Nodes = voting methods, coloured by family.
 * Edges  = inter-method agreement above the threshold slider.
 * Physics: forceLink (strength ∝ agreement) + forceManyBody + forceCenter + forceCollide.
 * D3 runs the simulation; React renders every tick via setState.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
  SimulationNodeDatum,
  SimulationLinkDatum,
} from 'd3';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { Range } from '@/components/ui/form-controls';

// ── Method family classification ──────────────────────────────────────────────

const FAMILY: Record<string, 'ranked' | 'score' | 'special'> = {
  plurality: 'ranked',
  two_round: 'ranked',
  borda: 'ranked',
  irv: 'ranked',
  coombs: 'ranked',
  bucklin: 'ranked',
  minimax: 'ranked',
  schulze: 'ranked',
  kemeny_young: 'ranked',
  positional_score: 'ranked',
  simple_score: 'score',
  star_voting: 'score',
  median_voting: 'score',
  mean_median_hybrid: 'score',
  variance_based: 'score',
  approval: 'special',
  quadratic: 'special',
};

const FAMILY_COLOR: Record<string, string> = {
  ranked: '#005CAB',
  score: '#C8590A',
  special: '#007A33',
};

const NODE_R = 18;
const W = 500;
const H = 400;

// Family centres for the "group by family" force
const FAMILY_CENTERS: Record<string, { x: number; y: number }> = {
  ranked: { x: W * 0.25, y: H / 2 },
  score: { x: W * 0.65, y: H * 0.3 },
  special: { x: W * 0.65, y: H * 0.7 },
};

// ── Types ─────────────────────────────────────────────────────────────────────

interface NodeDatum extends SimulationNodeDatum {
  id: string;
  family: 'ranked' | 'score' | 'special';
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Convert flat "A|B" → value map to a symmetric nested matrix. */
export function flatToMatrix(flat: Record<string, number>): Record<string, Record<string, number>> {
  const matrix: Record<string, Record<string, number>> = {};
  for (const [key, val] of Object.entries(flat)) {
    const idx = key.indexOf('|');
    if (idx < 0) continue;
    const a = key.slice(0, idx);
    const b = key.slice(idx + 1);
    if (!matrix[a]) matrix[a] = {};
    if (!matrix[b]) matrix[b] = {};
    matrix[a][b] = val;
    matrix[b][a] = val;
  }
  return matrix;
}

/** Derive a pairwise agreement matrix from streaming winner distributions. */
export function partialResultsToMatrix(
  pr: Record<string, { winner_distribution: Record<string, number> }>
): Record<string, Record<string, number>> {
  const methods = Object.keys(pr);
  const matrix: Record<string, Record<string, number>> = {};
  for (const a of methods) {
    matrix[a] = {};
    for (const b of methods) {
      if (a === b) {
        matrix[a][b] = 1.0;
        continue;
      }
      const da = pr[a].winner_distribution;
      const db = pr[b].winner_distribution;
      const cands = new Set([...Object.keys(da), ...Object.keys(db)]);
      let agreement = 0;
      for (const c of cands) agreement += Math.min(da[c] ?? 0, db[c] ?? 0);
      matrix[a][b] = Math.round(agreement * 100) / 100;
    }
  }
  return matrix;
}

// ── Main component ────────────────────────────────────────────────────────────

export interface MethodSimilarityGraphProps {
  agreementMatrix: Record<string, Record<string, number>>;
  height?: number;
}

const MethodSimilarityGraph: React.FC<MethodSimilarityGraphProps> = ({
  agreementMatrix,
  height = H,
}) => {
  const { t } = useTranslation();

  const [threshold, setThreshold] = useState(0.6);
  const [groupByFamily, setGroupByFamily] = useState(false);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [positions, setPositions] = useState<Map<string, { x: number; y: number }>>(new Map());

  const simRef = useRef<any>(null);
  const dragRef = useRef<{ id: string | null; ox: number; oy: number }>({ id: null, ox: 0, oy: 0 });
  const svgRef = useRef<SVGSVGElement>(null);
  const rafRef = useRef<number | null>(null);

  const methodNames = useMemo(() => Object.keys(agreementMatrix), [agreementMatrix]);

  // Build node and link arrays
  const { nodes, links } = useMemo(() => {
    const nodes: NodeDatum[] = methodNames.map((id) => ({
      id,
      family: FAMILY[id] ?? 'ranked',
    }));
    const links: { source: string; target: string; value: number }[] = [];
    for (let i = 0; i < methodNames.length; i++) {
      for (let j = i + 1; j < methodNames.length; j++) {
        const a = methodNames[i];
        const b = methodNames[j];
        const v = agreementMatrix[a]?.[b] ?? agreementMatrix[b]?.[a];
        if (v != null && v >= threshold) {
          links.push({ source: a, target: b, value: v });
        }
      }
    }
    return { nodes, links };
  }, [agreementMatrix, methodNames, threshold]);

  // Rebuild D3 simulation when nodes/links/groupByFamily change
  useEffect(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    if (simRef.current) simRef.current.stop();

    if (nodes.length === 0) return;

    // Preserve existing positions
    const existingPos = positions;
    const initialised = nodes.map((n) => {
      const p = existingPos.get(n.id);
      return {
        ...n,
        x: p?.x ?? W / 2 + (Math.random() - 0.5) * 200,
        y: p?.y ?? H / 2 + (Math.random() - 0.5) * 160,
      };
    });

    const sim = forceSimulation<NodeDatum>(initialised)
      .force(
        'link',
        forceLink<NodeDatum, SimulationLinkDatum<NodeDatum>>(links as any)
          .id((d) => d.id)
          .strength((d: any) => d.value * 0.4)
          .distance((d: any) => 120 - d.value * 60)
      )
      .force('charge', forceManyBody().strength(-90))
      .force('center', forceCenter(W / 2, H / 2))
      .force('collide', forceCollide(NODE_R + 6))
      .alphaDecay(0.03);

    if (groupByFamily) {
      sim
        .force('fx', forceX<NodeDatum>((d) => FAMILY_CENTERS[d.family]?.x ?? W / 2).strength(0.35))
        .force('fy', forceY<NodeDatum>((d) => FAMILY_CENTERS[d.family]?.y ?? H / 2).strength(0.35));
    } else {
      sim.force('fx', null).force('fy', null);
    }

    simRef.current = sim;

    function tick() {
      const map = new Map<string, { x: number; y: number }>();
      (sim.nodes() as NodeDatum[]).forEach((n) => {
        map.set(n.id, {
          x: Math.max(NODE_R, Math.min(W - NODE_R, n.x ?? W / 2)),
          y: Math.max(NODE_R, Math.min(H - NODE_R, n.y ?? H / 2)),
        });
      });
      setPositions(map);
      if (sim.alpha() > sim.alphaMin()) {
        rafRef.current = requestAnimationFrame(tick);
      }
    }
    rafRef.current = requestAnimationFrame(tick);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      sim.stop();
    };
  }, [nodes.length, methodNames.join(','), threshold, groupByFamily]);

  // ── Drag handlers ──────────────────────────────────────────────────────────

  const handleNodeMouseDown = useCallback(
    (e: React.MouseEvent<SVGCircleElement>, id: string) => {
      e.preventDefault();
      const svg = svgRef.current;
      if (!svg) return;
      const rect = svg.getBoundingClientRect();
      const scaleX = W / rect.width;
      const scaleY = H / rect.height;
      const p = positions.get(id);
      dragRef.current = {
        id,
        ox: e.clientX * scaleX - (p?.x ?? 0),
        oy: e.clientY * scaleY - (p?.y ?? 0),
      };
      // Fix node in simulation
      const node = (simRef.current?.nodes() as NodeDatum[] | undefined)?.find((n) => n.id === id);
      if (node) {
        (node as any).fx = p?.x ?? 0;
        (node as any).fy = p?.y ?? 0;
      }
      simRef.current?.alphaTarget(0.3).restart();
    },
    [positions]
  );

  const handleSvgMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    const { id, ox, oy } = dragRef.current;
    if (!id || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const scaleX = W / rect.width;
    const scaleY = H / rect.height;
    const nx = e.clientX * scaleX - ox;
    const ny = e.clientY * scaleY - oy;
    const node = (simRef.current?.nodes() as NodeDatum[] | undefined)?.find((n) => n.id === id);
    if (node) {
      (node as any).fx = nx;
      (node as any).fy = ny;
    }
  }, []);

  const handleSvgMouseUp = useCallback(() => {
    const { id } = dragRef.current;
    if (id) {
      const node = (simRef.current?.nodes() as NodeDatum[] | undefined)?.find((n) => n.id === id);
      if (node) {
        (node as any).fx = undefined;
        (node as any).fy = undefined;
      }
      simRef.current?.alphaTarget(0);
    }
    dragRef.current = { id: null, ox: 0, oy: 0 };
  }, []);

  // ── Derived ────────────────────────────────────────────────────────────────

  // Links with resolved positions
  const resolvedLinks = useMemo(() => {
    return links.map((l) => {
      const src = typeof l.source === 'string' ? l.source : (l.source as any).id;
      const tgt = typeof l.target === 'string' ? l.target : (l.target as any).id;
      return { src, tgt, value: l.value };
    });
  }, [links, nodes]);

  // Hover tooltip lines
  const hoverLines = useMemo(() => {
    if (!hoveredNode) return [];
    return resolvedLinks
      .filter((l) => l.src === hoveredNode || l.tgt === hoveredNode)
      .map((l) => ({ peer: l.src === hoveredNode ? l.tgt : l.src, value: l.value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 6);
  }, [hoveredNode, resolvedLinks]);

  const edgeCount = resolvedLinks.length;
  const maxAgreement =
    methodNames.length > 1 ? Math.max(0, ...resolvedLinks.map((l) => l.value)) : 0;

  return (
    <div>
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 mb-2">
        <div style={{ flex: '1 1 200px', minWidth: 160 }}>
          <label className="mb-1 inline-block text-sm mb-0">
            {t('graph.threshold')}: <strong>{Math.round(threshold * 100)}%</strong>
            <span className="text-muted-foreground ms-2" style={{ fontSize: '0.7rem' }}>
              ({edgeCount} {t('graph.edges')})
            </span>
          </label>
          <Range
            min={0}
            max={1}
            step={0.05}
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
            data-testid="threshold-slider"
          />
        </div>
        <Button
          size="sm"
          variant={groupByFamily ? 'secondary' : 'outline-secondary'}
          onClick={() => setGroupByFamily(!groupByFamily)}
          data-testid="group-by-family-btn"
        >
          {t('graph.groupByFamily')}
        </Button>
        {/* Family legend */}
        <div className="flex gap-2">
          {(['ranked', 'score', 'special'] as const).map((f) => (
            <span key={f} className="flex items-center gap-1" style={{ fontSize: '0.72rem' }}>
              <span
                style={{
                  display: 'inline-block',
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  background: FAMILY_COLOR[f],
                }}
              />
              {t(`graph.family_${f}`)}
            </span>
          ))}
        </div>
      </div>

      {/* SVG graph */}
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${height}`}
        width="100%"
        style={{
          display: 'block',
          cursor: dragRef.current.id ? 'grabbing' : 'default',
          userSelect: 'none',
        }}
        onPointerMove={handleSvgMouseMove as unknown as React.PointerEventHandler<SVGSVGElement>}
        onPointerUp={handleSvgMouseUp}
        onPointerLeave={handleSvgMouseUp}
        aria-label={t('graph.ariaLabel')}
        data-testid="similarity-graph"
      >
        {/* Edges */}
        <g data-testid="graph-edges">
          {resolvedLinks.map(({ src, tgt, value }) => {
            const sp = positions.get(src) ?? { x: W / 2, y: H / 2 };
            const tp = positions.get(tgt) ?? { x: W / 2, y: H / 2 };
            const isHighlighted = hoveredNode === src || hoveredNode === tgt;
            const opacity = hoveredNode ? (isHighlighted ? 0.9 : 0.1) : 0.35 + value * 0.45;
            return (
              <line
                key={`${src}|${tgt}`}
                x1={sp.x}
                y1={sp.y}
                x2={tp.x}
                y2={tp.y}
                stroke={isHighlighted ? '#212529' : '#adb5bd'}
                strokeWidth={Math.max(1, value * 5)}
                opacity={opacity}
                style={{ transition: 'opacity 0.4s' }}
                data-testid="graph-edge"
              />
            );
          })}
        </g>

        {/* Nodes */}
        <g data-testid="graph-nodes">
          {nodes.map((n) => {
            const p = positions.get(n.id) ?? { x: W / 2, y: H / 2 };
            const color = FAMILY_COLOR[n.family];
            const isHovered = hoveredNode === n.id;
            return (
              <g key={n.id} data-testid="graph-node" data-method={n.id}>
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={isHovered ? NODE_R + 3 : NODE_R}
                  fill={color}
                  stroke={isHovered ? '#212529' : '#fff'}
                  strokeWidth={isHovered ? 2.5 : 1.5}
                  opacity={hoveredNode && !isHovered ? 0.5 : 1}
                  style={{
                    cursor: 'grab',
                    transition: 'opacity 0.3s, r 0.2s',
                    touchAction: 'none',
                  }}
                  onPointerDown={(e) => {
                    (e.target as Element).setPointerCapture(e.pointerId);
                    handleNodeMouseDown(e as unknown as React.MouseEvent<SVGCircleElement>, n.id);
                  }}
                  onPointerEnter={() => setHoveredNode(n.id)}
                  onPointerLeave={() => setHoveredNode(null)}
                />
                <text
                  x={p.x}
                  y={p.y + 1}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={9}
                  fill="#fff"
                  fontWeight={600}
                  style={{ pointerEvents: 'none' }}
                >
                  {n.id
                    .split('_')
                    .map((w) => w[0]?.toUpperCase())
                    .join('')}
                </text>
                <text
                  x={p.x}
                  y={p.y + NODE_R + 11}
                  textAnchor="middle"
                  fontSize={8.5}
                  fill="#495057"
                  style={{ pointerEvents: 'none' }}
                >
                  {n.id.replace(/_/g, ' ')}
                </text>
              </g>
            );
          })}
        </g>

        {/* Hover tooltip */}
        {hoveredNode &&
          hoverLines.length > 0 &&
          (() => {
            const p = positions.get(hoveredNode) ?? { x: W / 2, y: H / 2 };
            const tx = p.x > W * 0.6 ? p.x - 10 : p.x + 10;
            const anchor = p.x > W * 0.6 ? 'end' : 'start';
            const ty = Math.min(p.y, H - hoverLines.length * 14 - 20);
            return (
              <g data-testid="hover-tooltip">
                <rect
                  x={anchor === 'end' ? tx - 160 : tx - 4}
                  y={ty - 14}
                  width={164}
                  height={hoverLines.length * 14 + 10}
                  rx={4}
                  fill="rgba(255,255,255,0.92)"
                  stroke="#dee2e6"
                />
                {hoverLines.map((l, i) => (
                  <text
                    key={l.peer}
                    x={tx}
                    y={ty + i * 14}
                    textAnchor={anchor}
                    fontSize={9}
                    fill="#212529"
                  >
                    {l.peer}: <tspan fontWeight={600}>{Math.round(l.value * 100)}%</tspan>
                  </text>
                ))}
              </g>
            );
          })()}
      </svg>

      {/* Stats bar */}
      <div className="flex flex-wrap gap-3 mt-1" style={{ fontSize: '0.75rem', color: '#6c757d' }}>
        <span>
          {methodNames.length} {t('graph.methods')} · {edgeCount} {t('graph.edges')}
        </span>
        {maxAgreement > 0 && (
          <span>
            {t('graph.maxAgreement')}: <strong>{Math.round(maxAgreement * 100)}%</strong>
          </span>
        )}
        <span className="text-muted-foreground">{t('graph.dragHint')}</span>
      </div>

      {methodNames.length === 0 && (
        <div className="text-center text-muted-foreground py-4" style={{ fontSize: '0.85rem' }}>
          {t('graph.noData')}
        </div>
      )}
    </div>
  );
};

export default MethodSimilarityGraph;
