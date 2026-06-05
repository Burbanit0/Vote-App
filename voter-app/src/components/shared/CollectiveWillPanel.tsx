/**
 * CollectiveWillPanel — does collective will exist, or is it procedural artefact?
 * Rousseau (1762) vs Arrow (1951) vs Schumpeter (1942) vs Sen (1999) vs Rawls (1971).
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Control, Select } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import { $api } from '../../api/hooks';

// ── Types ─────────────────────────────────────────────────────────────────────

interface CollectiveWillData {
  unique_winners: string[];
  unique_winner_count: number;
  winner_by_method: Record<string, string>;
  winner_by_agenda: Record<string, string>;
  rousseau_score: number;
  most_frequent_winner: string;
  most_frequent_pct: number;
  condorcet_exists: boolean;
  condorcet_winner: string | null;
  philosophical_conclusion: string;
  pedagogical_note: string;
}

// ── Candidate colour palette ──────────────────────────────────────────────────

const CAND_COLORS: Record<string, string> = {
  Alice: '#0d6efd',
  Bob: '#dc3545',
  Carol: '#198754',
  David: '#fd7e14',
  Eva: '#6f42c1',
};

function candColor(name: string, idx = 0): string {
  return CAND_COLORS[name] ?? ['#0d6efd', '#dc3545', '#198754', '#fd7e14', '#6f42c1'][idx % 5];
}

// ── Will-o-meter SVG ──────────────────────────────────────────────────────────

const WillOMeter: React.FC<{ score: number; uniqueCount: number }> = ({ score, uniqueCount }) => {
  const size = 200;
  const cx = size / 2;
  const cy = size / 2 + 20;
  const R = 75;

  // Semi-circle arc from π to 0 (left to right)
  const deg = (1 - score) * 180; // 0=right(Rousseau), 180=left(Schumpeter)
  const rad = (deg * Math.PI) / 180;
  const nx = cx + R * Math.cos(Math.PI - rad);
  const ny = cy - R * Math.sin(Math.PI - rad);

  // Arc background segments (red→yellow→green)
  const arcPath = (startDeg: number, endDeg: number, color: string) => {
    const s = (startDeg * Math.PI) / 180;
    const e = (endDeg * Math.PI) / 180;
    const x1 = cx + R * Math.cos(s);
    const y1 = cy - R * Math.sin(s);
    const x2 = cx + R * Math.cos(e);
    const y2 = cy - R * Math.sin(e);
    return (
      <path
        d={`M ${x1} ${y1} A ${R} ${R} 0 0 0 ${x2} ${y2}`}
        fill="none"
        stroke={color}
        strokeWidth={14}
        strokeLinecap="round"
      />
    );
  };

  const gaugeColor = score > 0.7 ? '#198754' : score > 0.4 ? '#ffc107' : '#dc3545';

  return (
    <svg
      data-testid="will-o-meter"
      width={size}
      height={size * 0.72}
      style={{ display: 'block', margin: '0 auto' }}
    >
      {/* Background arc segments */}
      {arcPath(180, 120, '#dc3545')}
      {arcPath(120, 60, '#fd7e14')}
      {arcPath(60, 0, '#198754')}
      {/* Needle */}
      <line
        x1={cx}
        y1={cy}
        x2={nx}
        y2={ny}
        stroke={gaugeColor}
        strokeWidth={3}
        strokeLinecap="round"
      />
      <circle cx={cx} cy={cy} r={6} fill={gaugeColor} />
      {/* Labels */}
      <text x={8} y={cy + 8} style={{ fontSize: 9, fill: '#dc3545' }}>
        Schumpeter
      </text>
      <text x={size - 10} y={cy + 8} textAnchor="end" style={{ fontSize: 9, fill: '#198754' }}>
        Rousseau
      </text>
      {/* Score */}
      <text
        x={cx}
        y={cy - R - 12}
        textAnchor="middle"
        style={{ fontSize: 20, fontWeight: 700, fill: gaugeColor }}
      >
        {Math.round(score * 100)}%
      </text>
      <text x={cx} y={cy - R + 4} textAnchor="middle" style={{ fontSize: 9, fill: '#6c757d' }}>
        {uniqueCount} vainqueur{uniqueCount > 1 ? 's' : ''} possible{uniqueCount > 1 ? 's' : ''}
      </text>
    </svg>
  );
};

// ── Result grid (method × agenda) ─────────────────────────────────────────────

const ResultGrid: React.FC<{
  byMethod: Record<string, string>;
  byAgenda: Record<string, string>;
  t: (k: string) => string;
}> = ({ byMethod, byAgenda, t }) => {
  const allWinners = new Set([...Object.values(byMethod), ...Object.values(byAgenda)]);
  const winnerList = [...allWinners];

  return (
    <div data-testid="result-grid" style={{ overflowX: 'auto' }}>
      <div className="font-semibold mb-2" style={{ fontSize: '0.82rem' }}>
        {t('will.gridTitle')}
      </div>
      <table className="table table-sm table-bordered" style={{ fontSize: '0.72rem' }}>
        <thead className="table-light">
          <tr>
            <th>{t('will.procedure')}</th>
            <th>{t('will.winner')}</th>
            <th>{t('will.type')}</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(byMethod).map(([method, winner]) => (
            <tr key={`m-${method}`} data-testid={`grid-method-${method}`}>
              <td>{method}</td>
              <td>
                <span
                  className="badge"
                  style={{
                    background: candColor(winner, winnerList.indexOf(winner)),
                    fontSize: '0.65rem',
                  }}
                >
                  {winner}
                </span>
              </td>
              <td className="text-muted-foreground">{t('will.typeMethod')}</td>
            </tr>
          ))}
          {Object.entries(byAgenda).map(([agenda, winner]) => (
            <tr key={`a-${agenda}`} data-testid={`grid-agenda-${agenda.slice(0, 10)}`}>
              <td
                style={{
                  fontSize: '0.65rem',
                  maxWidth: 120,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {agenda}
              </td>
              <td>
                <span
                  className="badge"
                  style={{
                    background: candColor(winner, winnerList.indexOf(winner)),
                    fontSize: '0.65rem',
                  }}
                >
                  {winner}
                </span>
              </td>
              <td className="text-muted-foreground">{t('will.typeAgenda')}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {/* Color legend */}
      <div className="flex gap-2 flex-wrap" style={{ fontSize: '0.65rem' }}>
        {winnerList.map((w, i) => (
          <span key={w}>
            <span
              style={{
                display: 'inline-block',
                width: 10,
                height: 10,
                borderRadius: '50%',
                background: candColor(w, i),
                marginRight: 3,
              }}
            />
            {w}
          </span>
        ))}
      </div>
    </div>
  );
};

// ── Philosophers section ──────────────────────────────────────────────────────

const PHILOSOPHERS = [
  { key: 'rousseau', icon: '📜', year: '1762', color: '#198754' },
  { key: 'arrow', icon: '🔢', year: '1951', color: '#dc3545' },
  { key: 'schumpeter', icon: '🏭', year: '1942', color: '#fd7e14' },
  { key: 'sen', icon: '⚖️', year: '1999', color: '#0d6efd' },
  { key: 'rawls', icon: '🎭', year: '1971', color: '#6f42c1' },
];

const PhilosophersSection: React.FC<{ score: number; t: (k: string) => string }> = ({
  score,
  t,
}) => {
  const [activePhilo, setActivePhilo] = useState<string | null>(null);

  // Which philosopher is "most right" given the score?
  const mostRight =
    score > 0.8 ? 'rousseau' : score < 0.3 ? 'schumpeter' : score < 0.5 ? 'arrow' : 'rawls';

  return (
    <div data-testid="philosophers-section">
      <div className="font-semibold mb-2" style={{ fontSize: '0.82rem' }}>
        {t('will.philosTitle')}
        <Badge variant="secondary" className="ms-2" style={{ fontSize: '0.6rem' }}>
          {t('will.mostRight')}: {t(`will.philo_${mostRight}`)}
        </Badge>
      </div>
      <Row className="g-2">
        {PHILOSOPHERS.map(({ key, icon, year, color }) => (
          <Col key={key} xs={12} md={6}>
            <div
              role="button"
              className="border border-border rounded p-2"
              style={{
                background: activePhilo === key ? '#f8f9fa' : '#fff',
                borderColor: activePhilo === key ? color : undefined,
                cursor: 'pointer',
                fontSize: '0.74rem',
              }}
              onClick={() => setActivePhilo(activePhilo === key ? null : key)}
              data-testid={`philo-card-${key}`}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontSize: '1rem' }}>{icon}</span>
                <strong style={{ color }}>{t(`will.philo_${key}`)}</strong>
                <span className="text-muted-foreground ml-auto" style={{ fontSize: '0.65rem' }}>
                  {year}
                </span>
              </div>
              <div className="text-muted-foreground" style={{ fontSize: '0.7rem', marginTop: 3 }}>
                {t(`will.philo_short_${key}`)}
              </div>
              {activePhilo === key && (
                <div
                  className="mt-2 p-2 rounded"
                  style={{ background: color + '18', fontSize: '0.72rem', lineHeight: 1.5 }}
                >
                  {t(`will.philo_detail_${key}`)}
                </div>
              )}
            </div>
          </Col>
        ))}
      </Row>
    </div>
  );
};

// ── Lab-mode props ────────────────────────────────────────────────────────────

export interface CollectiveWillLabProps {
  labMode?: boolean;
  labCandidates?: Array<{ name: string; x: number; y: number }>;
  labNumVoters?: number;
  labSeed?: number;
  labIdeology?: string;
}

// ── Main panel ────────────────────────────────────────────────────────────────

const CollectiveWillPanel: React.FC<CollectiveWillLabProps> = ({
  labMode = false,
  labCandidates,
  labNumVoters,
  labSeed,
  labIdeology,
}) => {
  const { t } = useTranslation();

  const sim = $api.useMutation('post', '/api/v2/theory/collective-will');
  const data: CollectiveWillData | null = (sim.data as CollectiveWillData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('will.error') : null;
  const [numVoters, setNumVoters] = useState(100);
  const [seed, setSeed] = useState(42);
  const [numMethods, setNumMethods] = useState(5);
  const [numAgendas, setNumAgendas] = useState(4);
  const [ideology, setIdeology] = useState('random');

  const DEFAULT_CANDS = [
    { name: 'Alice', x: -0.5, y: 0.0 },
    { name: 'Bob', x: 0.0, y: 0.0 },
    { name: 'Carol', x: 0.5, y: 0.0 },
  ];

  const handleRun = (
    overrideCands?: typeof DEFAULT_CANDS,
    overrideVoters?: number,
    overrideSeed?: number,
    overrideIdeology?: string
  ) => {
    sim.mutate({
      body: {
        candidates: overrideCands ?? DEFAULT_CANDS,
        num_voters: overrideVoters ?? numVoters,
        ideology: overrideIdeology ?? ideology,
        seed: overrideSeed ?? seed,
        num_methods: numMethods,
        num_agendas: numAgendas,
        num_simulations: 1,
      },
    });
  };

  // Auto-run when lab context changes
  useEffect(() => {
    if (labMode && labCandidates?.length) {
      handleRun(labCandidates, labNumVoters, labSeed, labIdeology);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [labMode, labCandidates, labNumVoters, labSeed, labIdeology]);

  const score = data?.rousseau_score ?? 0;

  return (
    <div>
      {/* ── Lab mode badge ── */}
      {labMode && (
        <div className="mb-2">
          <Badge variant="dark" style={{ fontSize: '0.68rem' }}>
            🔬 {t('lab.fromElectionLab')}
          </Badge>
        </div>
      )}
      {/* ── Controls (hidden in lab mode) ── */}
      {!labMode && (
        <Row className="g-2 mb-3 items-end">
          <Col xs={6} md={2}>
            <label className="mb-1 inline-block text-sm mb-0">{t('will.voters')}</label>
            <Control
              type="number"
              size="sm"
              min={10}
              max={500}
              value={numVoters}
              data-testid="voters-input"
              onChange={(e) => setNumVoters(Number(e.target.value))}
            />
          </Col>
          <Col xs={6} md={2}>
            <label className="mb-1 inline-block text-sm mb-0">{t('will.methods')}</label>
            <Control
              type="number"
              size="sm"
              min={2}
              max={10}
              value={numMethods}
              data-testid="methods-input"
              onChange={(e) => setNumMethods(Number(e.target.value))}
            />
          </Col>
          <Col xs={6} md={2}>
            <label className="mb-1 inline-block text-sm mb-0">{t('will.agendas')}</label>
            <Control
              type="number"
              size="sm"
              min={2}
              max={6}
              value={numAgendas}
              data-testid="agendas-input"
              onChange={(e) => setNumAgendas(Number(e.target.value))}
            />
          </Col>
          <Col xs={6} md={2}>
            <label className="mb-1 inline-block text-sm mb-0">{t('will.ideology')}</label>
            <Select
              size="sm"
              value={ideology}
              data-testid="ideology-select"
              onChange={(e) => setIdeology(e.target.value)}
            >
              <option value="random">{t('will.ideologyRandom')}</option>
              <option value="polarized">{t('will.ideologyPolarized')}</option>
            </Select>
          </Col>
          <Col xs={6} md={1}>
            <label className="mb-1 inline-block text-sm mb-0">{t('will.seed')}</label>
            <Control
              type="number"
              size="sm"
              value={seed}
              data-testid="seed-input"
              onChange={(e) => setSeed(Number(e.target.value))}
            />
          </Col>
          <Col xs="auto">
            <Button
              variant="dark"
              size="sm"
              onClick={() => handleRun()}
              disabled={loading}
              data-testid="run-btn"
            >
              {loading ? <Spinner size="sm" /> : t('will.run')}
            </Button>
          </Col>
        </Row>
      )}

      {!data && !loading && !error && !labMode && (
        <Alert variant="secondary" data-testid="prompt-alert">
          {t('will.prompt')}
        </Alert>
      )}
      {error && (
        <Alert variant="danger" data-testid="error-alert">
          {error}
        </Alert>
      )}

      {data && (
        <>
          {/* ── Will-o-meter ── */}
          <div className="mb-3 text-center" data-testid="willometer-section">
            <div className="font-semibold mb-1" style={{ fontSize: '0.82rem' }}>
              {t('will.meterTitle')}
            </div>
            <WillOMeter score={score} uniqueCount={data.unique_winner_count} />
            <div className="flex gap-2 justify-center flex-wrap mt-2">
              <Badge
                variant={data.condorcet_exists ? 'success' : 'danger'}
                data-testid="condorcet-badge"
              >
                {data.condorcet_exists
                  ? `✓ ${t('will.condorcetExists')}: ${data.condorcet_winner}`
                  : `✗ ${t('will.noCW')}`}
              </Badge>
              <Badge variant="secondary" data-testid="rousseau-badge">
                Rousseau score: {Math.round(score * 100)}%
              </Badge>
              <Badge
                variant={score > 0.7 ? 'success' : score > 0.4 ? 'warning' : 'danger'}
                data-testid="verdict-badge"
              >
                {score > 0.7
                  ? t('will.verdictRousseau')
                  : score > 0.4
                    ? t('will.verdictMixed')
                    : t('will.verdictSchumpeter')}
              </Badge>
            </div>
          </div>

          {/* ── Unique winners ── */}
          <div className="mb-3" data-testid="unique-winners">
            <span className="font-semibold" style={{ fontSize: '0.82rem' }}>
              {t('will.uniqueWinnersTitle')} ({data.unique_winner_count}) :
            </span>{' '}
            {data.unique_winners.map((w, i) => (
              <Badge
                key={w}
                className="me-1"
                style={{ background: candColor(w, i), fontSize: '0.72rem' }}
              >
                {w}
                {w === data.most_frequent_winner && (
                  <span className="ms-1">({Math.round(data.most_frequent_pct * 100)}%)</span>
                )}
              </Badge>
            ))}
          </div>

          {/* ── Result grid ── */}
          <div className="mb-3">
            <ResultGrid byMethod={data.winner_by_method} byAgenda={data.winner_by_agenda} t={t} />
          </div>

          {/* ── Philosophers ── */}
          <div className="mb-3">
            <PhilosophersSection score={score} t={t} />
          </div>

          {/* ── Philosophical conclusion ── */}
          <Alert
            variant={score > 0.7 ? 'success' : score > 0.4 ? 'warning' : 'danger'}
            className="mb-3"
            data-testid="philo-conclusion"
          >
            <strong>{t('will.conclusionTitle')}</strong> {data.philosophical_conclusion}
          </Alert>

          {/* ── The conclusion that doesn't conclude ── */}
          <div
            className="border border-border rounded p-3"
            data-testid="open-conclusion"
            style={{ background: '#f8f9fa', fontSize: '0.78rem', fontStyle: 'italic' }}
          >
            <strong style={{ fontStyle: 'normal' }}>{t('will.openTitle')}</strong>
            <p className="mt-1 mb-0">{t('will.openText')}</p>
          </div>

          {/* ── Pedagogical note ── */}
          <Alert
            variant="secondary"
            className="mt-3"
            style={{ fontSize: '0.8rem' }}
            data-testid="pedagogical-note"
          >
            <strong>{t('will.noteTitle')}</strong> {data.pedagogical_note}
          </Alert>
        </>
      )}
    </div>
  );
};

export default CollectiveWillPanel;
