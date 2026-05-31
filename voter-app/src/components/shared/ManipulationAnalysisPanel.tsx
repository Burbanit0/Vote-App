/**
 * ManipulationAnalysisPanel — demonstrates Gibbard-Satterthwaite theorem:
 * identifies voters who can profitably misrepresent their preferences,
 * and shows which strategy they use (compromising, burying, push-over, truncating).
 */
import React, { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Badge, Button, Col, Form, Row, Spinner, Table } from 'react-bootstrap';
import { useElection } from '../../stores/useElectionStore';
import PinToCentralButton from './PinToCentralButton';
import { $api } from '../../api/hooks';
const SVG_SIZE = 340;
const PAD = 28;
const STRATEGIES = ['compromising', 'burying', 'pushover', 'truncating'] as const;
type Strategy = typeof STRATEGIES[number];

// ── Types ─────────────────────────────────────────────────────────────────────

interface Manipulator {
  voter_id:        number;
  voter_ideology:  [number, number];
  sincere_vote:    string[];
  strategic_vote:  string[];
  strategy_type:   Strategy;
  sincere_result:  string;
  strategic_result: string;
  utility_gain:    number;
}

interface ManipData {
  sincere_winner:     string | null;
  manipulable:        boolean;
  manipulation_count: number;
  manipulators:       Manipulator[];
  strategy_breakdown: Record<Strategy, number>;
  key_manipulator:    { voter_id: number; strategy: Strategy; gain: number } | null;
  pedagogical_note:   string;
}

// ── Palette ───────────────────────────────────────────────────────────────────

const STRAT_COLOR: Record<Strategy, string> = {
  compromising: '#005CAB',
  burying:      '#dc3545',
  pushover:     '#fd7e14',
  truncating:   '#6f42c1',
};

function px(v: number) { return PAD + ((v + 1) / 2) * (SVG_SIZE - 2 * PAD); }

// ── Ideology SVG map ──────────────────────────────────────────────────────────

interface MapProps {
  manipulators:   Manipulator[];
  allVoters:      { voter_id: number; voter_ideology: [number, number] }[];
  selected:       number | null;
  onSelect:       (id: number | null) => void;
}

const ManipMap: React.FC<MapProps> = ({ manipulators, allVoters, selected, onSelect }) => {
  const manipSet = new Map(manipulators.map((m) => [m.voter_id, m]));

  return (
    <svg data-testid="manip-map-svg" width={SVG_SIZE} height={SVG_SIZE}
      style={{ border: '1px solid #dee2e6', borderRadius: 8, background: '#f8f9fa', cursor: 'pointer' }}
      onClick={() => onSelect(null)}>
      <line x1={PAD} y1={SVG_SIZE/2} x2={SVG_SIZE-PAD} y2={SVG_SIZE/2} stroke="#dee2e6" />
      <line x1={SVG_SIZE/2} y1={PAD} x2={SVG_SIZE/2} y2={SVG_SIZE-PAD} stroke="#dee2e6" />

      {/* Regular voters */}
      {allVoters.filter((v) => !manipSet.has(v.voter_id)).map((v) => (
        <circle key={v.voter_id}
          cx={px(v.voter_ideology[0])} cy={px(v.voter_ideology[1])} r={4}
          fill="#adb5bd" opacity={0.6} />
      ))}

      {/* Manipulators — halos ∝ gain */}
      {manipulators.map((m) => {
        const cx  = px(m.voter_ideology[0]);
        const cy  = px(m.voter_ideology[1]);
        const col = STRAT_COLOR[m.strategy_type] ?? '#dc3545';
        const r   = Math.max(8, Math.min(18, m.utility_gain * 40));
        const sel = selected === m.voter_id;
        return (
          <g key={m.voter_id} onClick={(e) => { e.stopPropagation(); onSelect(m.voter_id); }}>
            <circle cx={cx} cy={cy} r={r}
              fill={col} fillOpacity={0.15}
              stroke={col} strokeWidth={sel ? 2.5 : 1.5} strokeDasharray={sel ? undefined : '4 2'} />
            <circle cx={cx} cy={cy} r={5} fill={col} opacity={0.9} />
          </g>
        );
      })}
    </svg>
  );
};

// ── Voter detail panel ────────────────────────────────────────────────────────

interface DetailProps { manip: Manipulator; t: (k: string) => string; }

const ManipDetail: React.FC<DetailProps> = ({ manip, t }) => (
  <div className="border rounded p-3 mb-3" style={{ background: '#fff5f5' }}
    data-testid="manip-detail">
    <div className="fw-semibold mb-2" style={{ fontSize: '0.85rem' }}>
      {t('gs.voterDetail')} #{manip.voter_id}
      <Badge bg="danger" className="ms-2" style={{ fontSize: '0.65rem' }}>
        {t(`gs.strat_${manip.strategy_type}`)}
      </Badge>
    </div>
    <div className="d-flex gap-3 mb-2" style={{ fontSize: '0.78rem' }}>
      <div>
        <span className="text-muted">{t('gs.sincerevote')}:</span>{' '}
        <code>{manip.sincere_vote.join(' > ')}</code>
      </div>
      <span>→</span>
      <div>
        <span className="text-muted">{t('gs.strategicvote')}:</span>{' '}
        <code style={{ color: '#dc3545' }}>{manip.strategic_vote.join(' > ')}</code>
      </div>
    </div>
    <div style={{ fontSize: '0.78rem' }}>
      <span className="text-muted">{t('gs.sincerely')}:</span>
      <Badge bg="secondary" className="ms-1">{manip.sincere_result} {t('gs.wins')}</Badge>
      {' → '}
      <span className="text-muted">{t('gs.strategically')}:</span>
      <Badge bg="success" className="ms-1">{manip.strategic_result} {t('gs.wins')}</Badge>
    </div>
    <div className="text-muted mt-1" style={{ fontSize: '0.75rem' }}>
      {t('gs.gain')}: +{manip.utility_gain.toFixed(3)} {t('gs.utilityUnits')}
    </div>
  </div>
);

// ── Main panel ────────────────────────────────────────────────────────────────

const ManipulationAnalysisPanel: React.FC = () => {
  const { t }      = useTranslation();
  const { config } = useElection();

  const [method,   setMethod]   = useState('plurality');
  const sim = $api.useMutation('post', '/api/v2/theory/manipulation-analysis');
  const data: ManipData | null = (sim.data as ManipData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('gs.error') : null;
  const [selected, setSelected] = useState<number | null>(null);

  const runAnalysis = useCallback(() => {
    setSelected(null);
    sim.mutate({ body: {
      candidates:               config.candidates.map((c) => ({ name: c.name, x: c.x, y: c.y })),
      num_voters:               Math.min(config.num_voters, 50),
      ideology:                 config.ideology,
      seed:                     config.seed,
      method,
      manipulation_strategies:  ['compromising', 'burying', 'pushover', 'truncating'],
    } });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config, method, t, sim]);

  const selectedManip = data?.manipulators.find((m) => m.voter_id === selected) ?? null;

  // All voter positions (for the map background)
  const allVoterPositions = data?.manipulators.map((m) => ({
    voter_id: m.voter_id, voter_ideology: m.voter_ideology,
  })) ?? [];

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 align-items-end">
        <Col xs={12} md={4}>
          <Form.Label className="small mb-0">{t('gs.method')}</Form.Label>
          <Form.Select size="sm" value={method} data-testid="method-select"
            onChange={(e) => setMethod(e.target.value)}>
            <option value="plurality">Plurality</option>
            <option value="borda">Borda</option>
            <option value="irv">IRV</option>
            <option value="schulze">Schulze</option>
          </Form.Select>
        </Col>
        <Col xs="auto">
          <Button variant="primary" onClick={runAnalysis} disabled={loading}
            data-testid="analyze-btn">
            {loading ? <Spinner size="sm" animation="border" /> : t('gs.analyze')}
          </Button>
        </Col>
        {data && (
          <Col xs="auto">
            <PinToCentralButton
              type="manipulation"
              icon="🕵"
              label={t('gs.analyze')}
              summary={
                data.manipulable
                  ? `${t('gs.manipulable')}: ${data.manipulation_count} ${t('electionLab.voters')}`
                  : t('gs.notManipulable')
              }
              methodsChanged={data.manipulable ? 1 : 0}
            />
          </Col>
        )}
      </Row>

      {!data && !loading && !error && (
        <Alert variant="info" role="alert">{t('gs.prompt')}</Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}

      {data && (
        <>
          {/* Headline */}
          <div className="d-flex flex-wrap gap-2 mb-3">
            <Badge
              bg={data.manipulable ? 'danger' : 'success'}
              data-testid="manipulable-badge"
            >
              {data.manipulable ? t('gs.manipulable') : t('gs.notManipulable')}
            </Badge>
            <Badge bg="secondary" data-testid="count-badge">
              {data.manipulation_count} {t('gs.manipulators')}
            </Badge>
            {data.sincere_winner && (
              <Badge bg="primary" data-testid="winner-badge">
                {t('gs.sincereWinner')}: {data.sincere_winner}
              </Badge>
            )}
          </div>

          <Row className="g-3">
            <Col xs={12} md={6}>
              {/* Map */}
              <div className="fw-semibold mb-1" style={{ fontSize: '0.85rem' }}>
                {t('gs.mapTitle')}
              </div>
              <ManipMap
                manipulators={data.manipulators}
                allVoters={allVoterPositions}
                selected={selected}
                onSelect={setSelected}
              />
              <div className="d-flex flex-wrap gap-2 mt-1">
                {STRATEGIES.map((s) => (
                  <span key={s} style={{ fontSize: '0.7rem' }}>
                    <span style={{ display: 'inline-block', width: 10, height: 10,
                      borderRadius: '50%', background: STRAT_COLOR[s], marginRight: 3 }} />
                    {t(`gs.strat_${s}`)} ({data.strategy_breakdown[s] ?? 0})
                  </span>
                ))}
              </div>
            </Col>

            <Col xs={12} md={6}>
              {/* Selected voter detail */}
              {selectedManip && <ManipDetail manip={selectedManip} t={t} />}

              {/* Strategy breakdown table */}
              <Table size="sm" hover data-testid="strategy-table">
                <thead>
                  <tr>
                    <th style={{ fontSize: '0.78rem' }}>{t('gs.strategy')}</th>
                    <th style={{ fontSize: '0.78rem' }}>{t('gs.count')}</th>
                    <th style={{ fontSize: '0.78rem' }}>{t('gs.description')}</th>
                  </tr>
                </thead>
                <tbody>
                  {STRATEGIES.map((s) => (
                    <tr key={s}>
                      <td style={{ fontSize: '0.78rem' }}>
                        <span style={{ color: STRAT_COLOR[s], fontWeight: 700 }}>
                          {t(`gs.strat_${s}`)}
                        </span>
                      </td>
                      <td style={{ fontSize: '0.78rem' }}>
                        <Badge bg={data.strategy_breakdown[s] > 0 ? 'danger' : 'light'}
                          text={data.strategy_breakdown[s] > 0 ? undefined : 'dark'}>
                          {data.strategy_breakdown[s] ?? 0}
                        </Badge>
                      </td>
                      <td style={{ fontSize: '0.72rem', color: '#6c757d' }}>
                        {t(`gs.stratDesc_${s}`)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>

              {/* Pedagogical note */}
              <Alert variant="secondary" style={{ fontSize: '0.78rem' }}>
                <strong>{t('gs.noteTitle')}</strong> {data.pedagogical_note}
              </Alert>
            </Col>
          </Row>
        </>
      )}
    </div>
  );
};

export default ManipulationAnalysisPanel;
