/**
 * GerrymanderMap — interactive district-boundary editor + election simulator.
 *
 * The user paints a 10×10 grid of cells assigning each to a numbered
 * district. The backend then runs FPTP per district and compares the result
 * with D'Hondt proportional.
 */
import React, { useCallback, useRef, useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import { useElection } from '../../stores/useElectionStore';
import { $api } from '../../api/hooks';

// ── Grid constants ────────────────────────────────────────────────────────────

const GRID = 10; // 10×10 cells
const SVG_W = 400;
const SVG_H = 400;
const CELL_W = SVG_W / GRID;
const CELL_H = SVG_H / GRID;

// ── Types ─────────────────────────────────────────────────────────────────────

interface DistrictBounds {
  x_min: number;
  x_max: number;
  y_min: number;
  y_max: number;
}
interface DistrictDef {
  id: number;
  bounds: DistrictBounds;
}

interface DistrictResult {
  id: number;
  num_voters: number;
  winner: string | null;
  vote_shares: Record<string, number>;
}

interface VoterSnap {
  id: number;
  x: number;
  y: number;
  preferred: string;
}

interface GerryData {
  districts: DistrictResult[];
  voters: VoterSnap[];
  parliament_gerrymander: Record<string, number>;
  parliament_proportional: Record<string, number>;
  national_vote_share: Record<string, number>;
  distortion: number;
  gerrymander_index: number;
  winner: string;
  candidates: string[];
  num_seats: number;
}

// ── Palette ───────────────────────────────────────────────────────────────────

// District colours (up to 10 districts)
const DIST_COLORS = [
  '#005CAB44',
  '#C8590A44',
  '#007A3344',
  '#6c757d44',
  '#9b59b644',
  '#e67e2244',
  '#2A9D8F44',
  '#E76F5144',
  '#f0c04044',
  '#b71c1c44',
];
const DIST_STROKE = [
  '#005CAB',
  '#C8590A',
  '#007A33',
  '#6c757d',
  '#9b59b6',
  '#e67e22',
  '#2A9D8F',
  '#E76F51',
  '#f0c040',
  '#b71c1c',
];

const CAND_COLORS = ['#005CAB', '#C8590A', '#007A33', '#6c757d', '#9b59b6', '#e67e22'];
function candColor(name: string, names: string[]) {
  return CAND_COLORS[names.indexOf(name) % CAND_COLORS.length] ?? '#888';
}

// ── Grid cell → domain bounds ──────────────────────────────────────────────

function cellToBounds(col: number, row: number): DistrictBounds {
  // row 0 = top of SVG = y=+1 domain; row GRID-1 = y=-1 domain
  const x_min = -1 + col * (2 / GRID);
  const x_max = x_min + 2 / GRID;
  const y_max = 1 - row * (2 / GRID);
  const y_min = y_max - 2 / GRID;
  return { x_min, x_max, y_min, y_max };
}

// ── Build district defs from grid ─────────────────────────────────────────

function gridToDistricts(grid: number[][]): DistrictDef[] {
  // Merge contiguous cells of the same district ID into one bounding box
  const distMap = new Map<number, DistrictBounds>();
  for (let row = 0; row < GRID; row++) {
    for (let col = 0; col < GRID; col++) {
      const id = grid[row][col];
      if (id < 0) continue;
      const cb = cellToBounds(col, row);
      const existing = distMap.get(id);
      if (!existing) {
        distMap.set(id, { ...cb });
      } else {
        existing.x_min = Math.min(existing.x_min, cb.x_min);
        existing.x_max = Math.max(existing.x_max, cb.x_max);
        existing.y_min = Math.min(existing.y_min, cb.y_min);
        existing.y_max = Math.max(existing.y_max, cb.y_max);
      }
    }
  }
  return Array.from(distMap.entries()).map(([id, bounds]) => ({ id, bounds }));
}

// ── SVG coordinate helpers ─────────────────────────────────────────────────

function domainToSvgX(x: number) {
  return ((x + 1) / 2) * SVG_W;
}
function domainToSvgY(y: number) {
  return ((1 - y) / 2) * SVG_H;
} // flip y

// ── Hémicycle ─────────────────────────────────────────────────────────────────

const Hémicycle: React.FC<{
  seats: Record<string, number>;
  names: string[];
  total: number;
  label: string;
}> = ({ seats, names, total, label }) => {
  const W = 200;
  const H = 120;
  const cx = W / 2;
  const cy = H - 8;
  const rI = 35;
  const rO = 90;
  const parties = names.filter((n) => (seats[n] ?? 0) > 0);
  let cum = Math.PI;
  const segs = parties.map((n) => {
    const span = ((seats[n] ?? 0) / total) * Math.PI;
    const s = { name: n, a1: cum, a2: cum + span };
    cum += span;
    return s;
  });
  function arc(r: number, a: number): [number, number] {
    return [cx + r * Math.cos(a), cy - r * Math.sin(a)];
  }
  function path(r1: number, r2: number, a1: number, a2: number) {
    const [x1, y1] = arc(r1, a1);
    const [x2, y2] = arc(r2, a1);
    const [x3, y3] = arc(r2, a2);
    const [x4, y4] = arc(r1, a2);
    const la = a2 - a1 > Math.PI ? 1 : 0;
    return `M${x1} ${y1} L${x2} ${y2} A${r2} ${r2} 0 ${la} 0 ${x3} ${y3} L${x4} ${y4} A${r1} ${r1} 0 ${la} 1 ${x1} ${y1} Z`;
  }
  return (
    <div className="text-center">
      <div style={{ fontSize: '0.78rem', fontWeight: 600, marginBottom: 2 }}>{label}</div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ maxWidth: 220 }}>
        {segs.map((s) => (
          <path
            key={s.name}
            d={path(rI, rO, s.a1, s.a2)}
            fill={candColor(s.name, names)}
            stroke="#fff"
            strokeWidth={1}
          >
            <title>
              {s.name}: {seats[s.name]} siège(s)
            </title>
          </path>
        ))}
      </svg>
      <div className="flex flex-wrap gap-1 justify-center">
        {parties.map((n) => (
          <span key={n} style={{ fontSize: '0.68rem' }}>
            <span
              style={{
                display: 'inline-block',
                width: 8,
                height: 8,
                borderRadius: 1,
                background: candColor(n, names),
                marginRight: 2,
              }}
            />
            {n} ({seats[n]})
          </span>
        ))}
      </div>
    </div>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

const NUM_DISTRICTS = 5;

function makeDefaultGrid(): number[][] {
  // 5 horizontal stripes
  return Array.from({ length: GRID }, (_, row) =>
    Array.from({ length: GRID }, () => Math.floor(row / (GRID / NUM_DISTRICTS)))
  );
}

const GerrymanderMap: React.FC = () => {
  const { t } = useTranslation();
  const { config } = useElection();

  const [grid, setGrid] = useState<number[][]>(makeDefaultGrid);
  const [numDist, setNumDist] = useState(NUM_DISTRICTS);
  const [painting, setPainting] = useState<number | null>(null);
  const sim = $api.useMutation('post', '/api/v2/election/gerrymander');
  const data: GerryData | null = (sim.data as GerryData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('gerrymander.error') : null;

  const svgRef = useRef<SVGSVGElement>(null);

  const candidateNames = config.candidates.map((c) => c.name);

  // Paint a cell to a district id
  const paintCell = useCallback((col: number, row: number, distId: number) => {
    setGrid((prev) => {
      const next = prev.map((r) => [...r]);
      next[row][col] = distId;
      return next;
    });
  }, []);

  const handleCellClick = (col: number, row: number) => {
    const cur = grid[row][col];
    paintCell(col, row, (cur + 1) % numDist);
  };

  const handleCellPointerDown = (col: number, row: number) => {
    const newId = (grid[row][col] + 1) % numDist;
    setPainting(newId);
    paintCell(col, row, newId);
  };

  const handleCellPointerEnter = (col: number, row: number) => {
    if (painting !== null) paintCell(col, row, painting);
  };

  const handlePointerUp = () => setPainting(null);

  // Auto-redistrict: divide into horizontal stripes
  const autoRedistribute = () => {
    setGrid(
      Array.from({ length: GRID }, (_, row) =>
        Array.from({ length: GRID }, () => Math.floor(row / (GRID / numDist)))
      )
    );
  };

  // Greedy gerrymander: pack opponent into top district, spread own voters
  const gerrymanderOptimal = () => {
    // Simple heuristic: top rows → district 0, rest split evenly
    const newGrid = Array.from({ length: GRID }, (_, row) => {
      const distId = row < 2 ? 0 : Math.floor((row - 2) / Math.max(1, (GRID - 2) / (numDist - 1)));
      return Array.from({ length: GRID }, () => Math.min(distId, numDist - 1));
    });
    setGrid(newGrid);
  };

  function run() {
    const districts = gridToDistricts(grid);
    sim.mutate({
      body: {
        candidates: config.candidates,
        num_voters: config.num_voters,
        ideology: config.ideology,
        seed: config.seed,
        districts,
      },
    });
  }

  const winnerPct = data
    ? Math.round(((data.parliament_gerrymander[data.winner] ?? 0) / data.num_seats) * 100)
    : 0;
  const winnerVote = data ? Math.round((data.national_vote_share[data.winner] ?? 0) * 100) : 0;
  const isGerry = data && data.gerrymander_index > 0.2;

  return (
    <div>
      {/* Controls row */}
      <Row className="g-2 mb-3 items-end">
        <Col xs={12} sm={3}>
          <div className="text-sm mb-1">
            {t('gerrymander.numDistricts')}: <strong>{numDist}</strong>
          </div>
          <input
            type="range"
            className="form-range"
            min={2}
            max={10}
            step={1}
            value={numDist}
            onChange={(e) => {
              const n = Number(e.target.value);
              setNumDist(n);
              setGrid(
                Array.from({ length: GRID }, (_, row) =>
                  Array.from({ length: GRID }, () => Math.floor(row / (GRID / n)))
                )
              );
            }}
          />
        </Col>
        <Col xs={12} sm={3} className="flex gap-1 flex-wrap">
          <Button size="sm" variant="outline-secondary" onClick={autoRedistribute}>
            ⊞ {t('gerrymander.autoRedraw')}
          </Button>
          <Button size="sm" variant="outline-danger" onClick={gerrymanderOptimal}>
            ⚠ {t('gerrymander.gerryOptimal')}
          </Button>
        </Col>
        <Col xs={12} sm={3}>
          <Button variant="primary" className="w-full" onClick={run} disabled={loading}>
            {loading ? <Spinner size="sm" /> : `🗺 ${t('gerrymander.run')}`}
          </Button>
        </Col>
      </Row>

      {error && <Alert variant="danger">{error}</Alert>}
      {!data && !loading && <Alert variant="info">{t('gerrymander.prompt')}</Alert>}

      <Row className="g-3">
        {/* Left: grid editor + voter overlay */}
        <Col xs={12} lg={6}>
          <div className="text-sm text-muted-foreground mb-1">{t('gerrymander.gridHint')}</div>
          <svg
            ref={svgRef}
            data-testid="gerrymander-grid"
            viewBox={`0 0 ${SVG_W} ${SVG_H}`}
            width="100%"
            style={{ display: 'block', cursor: 'crosshair', userSelect: 'none', maxHeight: 400 }}
            onPointerUp={handlePointerUp}
            onPointerLeave={handlePointerUp}
          >
            {/* Grid cells */}
            {Array.from({ length: GRID }, (_, row) =>
              Array.from({ length: GRID }, (_, col) => {
                const distId = grid[row][col];
                return (
                  <rect
                    key={`${row}-${col}`}
                    x={col * CELL_W}
                    y={row * CELL_H}
                    width={CELL_W}
                    height={CELL_H}
                    fill={DIST_COLORS[distId % DIST_COLORS.length]}
                    stroke={DIST_STROKE[distId % DIST_STROKE.length]}
                    strokeWidth={0.5}
                    onClick={() => handleCellClick(col, row)}
                    onPointerDown={() => handleCellPointerDown(col, row)}
                    onPointerEnter={() => handleCellPointerEnter(col, row)}
                    data-testid="grid-cell"
                    data-district={distId}
                    style={{ cursor: 'crosshair' }}
                  />
                );
              })
            )}

            {/* Voter dots */}
            {data?.voters.map((v) => (
              <circle
                key={v.id}
                cx={domainToSvgX(v.x)}
                cy={domainToSvgY(v.y)}
                r={2.5}
                fill={candColor(v.preferred, data.candidates)}
                fillOpacity={0.5}
                style={{ pointerEvents: 'none' }}
                data-testid="voter-dot"
              />
            ))}

            {/* District labels */}
            {Array.from({ length: numDist }, (_, distId) => {
              const distResult = data?.districts.find((d) => d.id === distId);
              const cellsOfDist = [];
              for (let r = 0; r < GRID; r++)
                for (let c = 0; c < GRID; c++)
                  if (grid[r][c] === distId) cellsOfDist.push({ r, c });
              if (!cellsOfDist.length) return null;
              const meanC = cellsOfDist.reduce((a, b) => a + b.c, 0) / cellsOfDist.length;
              const meanR = cellsOfDist.reduce((a, b) => a + b.r, 0) / cellsOfDist.length;
              return (
                <text
                  key={distId}
                  x={meanC * CELL_W + CELL_W / 2}
                  y={meanR * CELL_H + CELL_H / 2}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={10}
                  fontWeight={700}
                  fill={DIST_STROKE[distId % DIST_STROKE.length]}
                  style={{ pointerEvents: 'none' }}
                >
                  {distId + 1}
                  {distResult?.winner ? ` (${distResult.winner[0]})` : ''}
                </text>
              );
            })}
          </svg>

          {/* District colour legend */}
          <div className="flex flex-wrap gap-2 mt-1" style={{ fontSize: '0.7rem' }}>
            {Array.from({ length: numDist }, (_, i) => (
              <span key={i} className="flex items-center gap-1">
                <span
                  style={{
                    width: 12,
                    height: 12,
                    background: DIST_COLORS[i],
                    border: `2px solid ${DIST_STROKE[i]}`,
                    display: 'inline-block',
                    borderRadius: 2,
                  }}
                />
                {t('gerrymander.district')} {i + 1}
              </span>
            ))}
          </div>
        </Col>

        {/* Right: results */}
        {data && (
          <Col xs={12} lg={6}>
            {/* Pedagogical message */}
            <Alert
              variant={isGerry ? 'warning' : 'success'}
              className="py-2 mb-3"
              style={{ fontSize: '0.82rem' }}
              data-testid="gerrymander-alert"
            >
              {isGerry
                ? t('gerrymander.pedagogicalGerry', {
                    winner: data.winner,
                    seatPct: winnerPct,
                    votePct: winnerVote,
                    index: Math.round(data.gerrymander_index * 100),
                  })
                : t('gerrymander.pedagogicalFair', { winner: data.winner })}
            </Alert>

            {/* Gerrymander index gauge */}
            <div className="mb-3">
              <div className="flex justify-between mb-1" style={{ fontSize: '0.75rem' }}>
                <span>{t('gerrymander.neutral')}</span>
                <strong>
                  {t('gerrymander.index')}: {Math.round(data.gerrymander_index * 100)}%
                </strong>
                <span>{t('gerrymander.perfect')}</span>
              </div>
              <div
                style={{ height: 12, background: '#e9ecef', borderRadius: 6, overflow: 'hidden' }}
              >
                <div
                  style={{
                    width: `${data.gerrymander_index * 100}%`,
                    height: '100%',
                    background:
                      data.gerrymander_index > 0.5
                        ? '#dc3545'
                        : data.gerrymander_index > 0.2
                          ? '#f0c040'
                          : '#007A33',
                    borderRadius: 6,
                    transition: 'width 0.5s ease',
                  }}
                  data-testid="gerry-index-bar"
                />
              </div>
            </div>

            {/* Dual hémicycles */}
            <Row className="g-2 mb-3">
              <Col xs={6}>
                <Hémicycle
                  seats={data.parliament_gerrymander}
                  names={data.candidates}
                  total={data.num_seats}
                  label={t('gerrymander.labelGerry')}
                />
              </Col>
              <Col xs={6}>
                <Hémicycle
                  seats={data.parliament_proportional}
                  names={data.candidates}
                  total={data.num_seats}
                  label={t('gerrymander.labelProp')}
                />
              </Col>
            </Row>

            {/* Distortion badges */}
            <div className="flex flex-wrap gap-2">
              <Badge
                variant={data.distortion > 0.1 ? 'warning' : 'success'}
                data-testid="distortion-badge"
              >
                {t('gerrymander.distortion')}: {Math.round(data.distortion * 100)}pp
              </Badge>
              {data.candidates.map((n) => {
                const seatsG = data.parliament_gerrymander[n] ?? 0;
                const seatsP = data.parliament_proportional[n] ?? 0;
                const diff = seatsG - seatsP;
                return (
                  <Badge
                    key={n}
                    style={{ background: candColor(n, data.candidates), fontSize: '0.7rem' }}
                  >
                    {n}: {seatsG}{' '}
                    {diff !== 0 && (
                      <span>
                        ({diff > 0 ? '+' : ''}
                        {diff})
                      </span>
                    )}
                  </Badge>
                );
              })}
            </div>
          </Col>
        )}
      </Row>
    </div>
  );
};

export default GerrymanderMap;
