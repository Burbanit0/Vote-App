/**
 * BehavioralBiasPanel — models three empirical voting biases:
 *   1. Expressive voting (Fiorina 1976)
 *   2. Bullet voting in Approval
 *   3. Primacy effect / ballot-order bias (Krosnick 1991)
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { Alert, Badge, Button, Col, Form, Row, Spinner, Table } from 'react-bootstrap';
import { useElection } from '../../context/ElectionContext';
import PinToCentralButton from './PinToCentralButton';

const API = process.env.REACT_APP_API_URL ?? 'http://localhost:4433';
const DEBOUNCE_MS = 400;

// ── Types ─────────────────────────────────────────────────────────────────────

interface MethodEntry {
  sincere: string | null;
  biased:  string | null;
}

interface BiasData {
  sincere_winner:      string;
  biased_winner:       string;
  winner_changed:      boolean;
  vote_breakdown: {
    expressive_voters: number;
    bullet_voters:     number;
    primacy_affected:  number;
    first_listed:      string;
    candidate_order:   string[];
  };
  method_sensitivity:    Record<string, MethodEntry>;
  bullet_immune_methods: string[];
  pedagogical_note:      string;
}

// ── Palette ───────────────────────────────────────────────────────────────────

const CAND_COLORS = ['#005CAB', '#C8590A', '#007A33', '#6c757d', '#9b59b6', '#e67e22'];
function candColor(name: string, names: string[]): string {
  return CAND_COLORS[names.indexOf(name) % CAND_COLORS.length] ?? '#888';
}

// ── Draggable ballot ──────────────────────────────────────────────────────────

interface BallotProps {
  order:       string[];
  onReorder:   (next: string[]) => void;
  t:           (k: string) => string;
}

const DraggableBallot: React.FC<BallotProps> = ({ order, onReorder, t }) => {
  const dragIdx = useRef<number | null>(null);

  const handleDragStart = (i: number) => { dragIdx.current = i; };

  const handleDrop = (i: number) => {
    if (dragIdx.current == null || dragIdx.current === i) return;
    const next = [...order];
    const [moved] = next.splice(dragIdx.current, 1);
    next.splice(i, 0, moved);
    dragIdx.current = null;
    onReorder(next);
  };

  return (
    <div data-testid="draggable-ballot" className="mt-2">
      {order.map((name, i) => (
        <div
          key={name}
          draggable
          onDragStart={() => handleDragStart(i)}
          onDragOver={(e) => e.preventDefault()}
          onDrop={() => handleDrop(i)}
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '6px 10px', marginBottom: 4,
            background: i === 0 ? '#fff3cd' : '#f8f9fa',
            border: '1px solid #dee2e6', borderRadius: 6,
            cursor: 'grab', fontSize: '0.85rem',
          }}
        >
          <span style={{ color: '#6c757d', minWidth: 18 }}>{i + 1}.</span>
          <span
            style={{
              width: 10, height: 10, borderRadius: '50%',
              background: candColor(name, order), display: 'inline-block', flexShrink: 0,
            }}
          />
          <span style={{ flex: 1 }}>{name}</span>
          {i === 0 && (
            <Badge bg="warning" text="dark" style={{ fontSize: '0.65rem' }}>
              {t('behavioral.primacyTag')}
            </Badge>
          )}
          <span style={{ color: '#adb5bd', fontSize: '0.7rem' }}>⠿</span>
        </div>
      ))}
      <div className="text-muted mt-1" style={{ fontSize: '0.72rem' }}>
        {t('behavioral.dragHint')}
      </div>
    </div>
  );
};

// ── Method sensitivity table ──────────────────────────────────────────────────

interface SensitivityTableProps {
  data:          BiasData;
  candidateNames: string[];
  t:             (k: string) => string;
}

const SensitivityTable: React.FC<SensitivityTableProps> = ({ data, candidateNames, t }) => {
  const { method_sensitivity, bullet_immune_methods } = data;
  const rows = Object.entries(method_sensitivity);

  return (
    <Table size="sm" hover className="mt-3" data-testid="sensitivity-table">
      <thead>
        <tr>
          <th style={{ fontSize: '0.78rem' }}>{t('behavioral.method')}</th>
          <th style={{ fontSize: '0.78rem' }}>{t('behavioral.sincere')}</th>
          <th style={{ fontSize: '0.78rem' }}>{t('behavioral.biased')}</th>
          <th style={{ fontSize: '0.78rem' }}>{t('behavioral.status')}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(([method, entry]) => {
          const changed = entry.sincere !== entry.biased;
          const bulletImmune = bullet_immune_methods.includes(method);
          return (
            <tr key={method} style={{ background: changed ? '#fff5f5' : undefined }}>
              <td style={{ fontSize: '0.78rem' }}>
                <code>{method}</code>
                {bulletImmune && (
                  <Badge bg="light" text="secondary" className="ms-1" style={{ fontSize: '0.6rem' }}>
                    {t('behavioral.bulletImmune')}
                  </Badge>
                )}
              </td>
              <td style={{ fontSize: '0.78rem' }}>
                <span style={{ color: candColor(entry.sincere ?? '', candidateNames) }}>
                  {entry.sincere ?? '—'}
                </span>
              </td>
              <td style={{ fontSize: '0.78rem' }}>
                <span style={{ color: candColor(entry.biased ?? '', candidateNames) }}>
                  {entry.biased ?? '—'}
                </span>
              </td>
              <td style={{ fontSize: '0.78rem' }}>
                {changed
                  ? <span style={{ color: '#dc3545' }}>⚠ {t('behavioral.changed')}</span>
                  : <span style={{ color: '#198754' }}>✓ {t('behavioral.stable')}</span>}
              </td>
            </tr>
          );
        })}
      </tbody>
    </Table>
  );
};

// ── Main panel ────────────────────────────────────────────────────────────────

const BehavioralBiasPanel: React.FC = () => {
  const { t }      = useTranslation();
  const { config } = useElection();

  const candidateNames = config.candidates.map((c) => c.name);

  // ── Bias states ──────────────────────────────────────────────────────────
  const [expressiveOn, setExpressiveOn] = useState(false);
  const [expressivePct, setExpressivePct] = useState(0.2);

  const [bulletOn, setBulletOn] = useState(false);
  const [bulletPct, setBulletPct] = useState(0.2);

  const [primacyOn, setPrimacyOn] = useState(false);
  const [primacyBonus, setPrimacyBonus] = useState(0.02);
  const [ballotOrder, setBallotOrder] = useState<string[]>(() => [...candidateNames]);

  // keep ballot order in sync when candidates change
  useEffect(() => {
    setBallotOrder((prev) => {
      const next = candidateNames.filter((n) => prev.includes(n));
      const added = candidateNames.filter((n) => !prev.includes(n));
      return [...next, ...added];
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config.candidates]);

  const [data,    setData]    = useState<BiasData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const runSimulation = useCallback(async (params: {
    expPct: number; bulPct: number; primBonus: number; order: string[];
  }) => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`${API}/api/election/behavioral-biases`, {
        candidates:         config.candidates.map((c) => ({ name: c.name, x: c.x, y: c.y })),
        num_voters:         config.num_voters,
        ideology:           config.ideology,
        seed:               config.seed,
        expressive_pct:     expressiveOn  ? params.expPct   : 0,
        bullet_voting_pct:  bulletOn      ? params.bulPct   : 0,
        primacy_bonus:      primacyOn     ? params.primBonus : 0,
        candidate_order:    params.order,
        method:             'plurality',
      });
      setData(res.data);
    } catch {
      setError(t('behavioral.error'));
    } finally {
      setLoading(false);
    }
  }, [config, expressiveOn, bulletOn, primacyOn, t]);

  const scheduleRun = useCallback((params: Parameters<typeof runSimulation>[0]) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runSimulation(params), DEBOUNCE_MS);
  }, [runSimulation]);

  const currentParams = {
    expPct: expressivePct, bulPct: bulletPct,
    primBonus: primacyBonus, order: ballotOrder,
  };

  const handleSimulate = () => runSimulation(currentParams);

  // Auto-recalculate on bias change (debounced) once data has been loaded once
  const hasData = data != null;
  useEffect(() => {
    if (!hasData) return;
    scheduleRun(currentParams);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expressiveOn, expressivePct, bulletOn, bulletPct, primacyOn, primacyBonus, ballotOrder]);

  return (
    <div>
      {/* Bias controls */}
      <Row className="g-3 mb-3">
        {/* Section 1 — Expressive */}
        <Col xs={12} md={4}>
          <div className="border rounded p-3" style={{ background: '#f8f9fa' }}>
            <Form.Check
              type="switch"
              id="expressive-switch"
              label={<strong style={{ fontSize: '0.85rem' }}>{t('behavioral.expressive')}</strong>}
              checked={expressiveOn}
              onChange={(e) => setExpressiveOn(e.target.checked)}
              data-testid="expressive-switch"
            />
            <div className="text-muted mb-2" style={{ fontSize: '0.72rem' }}>
              {t('behavioral.expressiveDesc')}
            </div>
            {expressiveOn && (
              <>
                <Form.Label className="small mb-0">
                  {t('behavioral.expressivePct')}: <strong>{Math.round(expressivePct * 100)}%</strong>
                </Form.Label>
                <Form.Range
                  data-testid="expressive-slider"
                  min={0} max={1} step={0.05}
                  value={expressivePct}
                  onChange={(e) => setExpressivePct(Number(e.target.value))}
                />
              </>
            )}
          </div>
        </Col>

        {/* Section 2 — Bullet voting */}
        <Col xs={12} md={4}>
          <div className="border rounded p-3" style={{ background: '#f8f9fa' }}>
            <Form.Check
              type="switch"
              id="bullet-switch"
              label={<strong style={{ fontSize: '0.85rem' }}>{t('behavioral.bullet')}</strong>}
              checked={bulletOn}
              onChange={(e) => setBulletOn(e.target.checked)}
              data-testid="bullet-switch"
            />
            <div className="text-muted mb-2" style={{ fontSize: '0.72rem' }}>
              {t('behavioral.bulletDesc')}
            </div>
            {bulletOn && (
              <>
                <Form.Label className="small mb-0">
                  {t('behavioral.bulletPct')}: <strong>{Math.round(bulletPct * 100)}%</strong>
                </Form.Label>
                <Form.Range
                  data-testid="bullet-slider"
                  min={0} max={1} step={0.05}
                  value={bulletPct}
                  onChange={(e) => setBulletPct(Number(e.target.value))}
                />
              </>
            )}
          </div>
        </Col>

        {/* Section 3 — Primacy */}
        <Col xs={12} md={4}>
          <div className="border rounded p-3" style={{ background: '#f8f9fa' }}>
            <Form.Check
              type="switch"
              id="primacy-switch"
              label={<strong style={{ fontSize: '0.85rem' }}>{t('behavioral.primacy')}</strong>}
              checked={primacyOn}
              onChange={(e) => setPrimacyOn(e.target.checked)}
              data-testid="primacy-switch"
            />
            <div className="text-muted mb-2" style={{ fontSize: '0.72rem' }}>
              {t('behavioral.primacyDesc')}
            </div>
            {primacyOn && (
              <>
                <Form.Label className="small mb-0">
                  {t('behavioral.primacyBonus')}: <strong>+{Math.round(primacyBonus * 100)}%</strong>
                </Form.Label>
                <Form.Range
                  data-testid="primacy-slider"
                  min={0} max={0.2} step={0.01}
                  value={primacyBonus}
                  onChange={(e) => setPrimacyBonus(Number(e.target.value))}
                />
                <DraggableBallot order={ballotOrder} onReorder={setBallotOrder} t={t} />
              </>
            )}
          </div>
        </Col>
      </Row>

      <div className="d-flex gap-2 mb-3 flex-wrap">
        <Button variant="primary" onClick={handleSimulate} disabled={loading}>
          {loading ? <Spinner size="sm" animation="border" /> : t('behavioral.run')}
        </Button>
        {data && (
          <PinToCentralButton
            type="behavioral"
            icon="🧠"
            label={t('behavioral.run')}
            summary={
              data.winner_changed
                ? `${data.sincere_winner} → ${data.biased_winner}`
                : `${data.biased_winner}`
            }
            methodsChanged={data.winner_changed ? 1 : 0}
          />
        )}
      </div>

      {!data && !loading && !error && (
        <Alert variant="info" role="alert">{t('behavioral.prompt')}</Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}

      {data && (
        <>
          {/* Headline comparison */}
          <div
            className={`d-flex align-items-center justify-content-around p-3 rounded mb-3 ${
              data.winner_changed ? 'border border-danger' : 'border border-success'
            }`}
            data-testid="comparison-banner"
          >
            <div className="text-center">
              <div className="text-muted" style={{ fontSize: '0.72rem' }}>{t('behavioral.sincereWinner')}</div>
              <Badge
                style={{
                  background: candColor(data.sincere_winner, candidateNames),
                  fontSize: '0.85rem', padding: '6px 12px',
                }}
                data-testid="sincere-winner-badge"
              >
                {data.sincere_winner}
              </Badge>
            </div>

            <div className="text-center px-2">
              {data.winner_changed ? (
                <span style={{ color: '#dc3545', fontSize: '1.4rem' }}>⇒</span>
              ) : (
                <span style={{ color: '#198754', fontSize: '1.4rem' }}>✓</span>
              )}
            </div>

            <div className="text-center">
              <div className="text-muted" style={{ fontSize: '0.72rem' }}>{t('behavioral.biasedWinner')}</div>
              <Badge
                style={{
                  background: candColor(data.biased_winner, candidateNames),
                  fontSize: '0.85rem', padding: '6px 12px',
                }}
                data-testid="biased-winner-badge"
                className={data.winner_changed ? 'border border-danger' : ''}
              >
                {data.biased_winner}
              </Badge>
            </div>
          </div>

          {/* Winner-changed banner */}
          {data.winner_changed && (
            <Alert variant="danger" data-testid="winner-changed-alert">
              {t('behavioral.winnerChanged')}
            </Alert>
          )}

          {/* Vote breakdown badges */}
          <div className="d-flex flex-wrap gap-2 mb-3">
            {data.vote_breakdown.expressive_voters > 0 && (
              <Badge bg="info" text="dark" data-testid="expressive-breakdown-badge">
                {data.vote_breakdown.expressive_voters} {t('behavioral.expressiveLabel')}
              </Badge>
            )}
            {data.vote_breakdown.bullet_voters > 0 && (
              <Badge bg="warning" text="dark" data-testid="bullet-breakdown-badge">
                {data.vote_breakdown.bullet_voters} {t('behavioral.bulletLabel')}
              </Badge>
            )}
            {data.vote_breakdown.primacy_affected > 0 && (
              <Badge bg="secondary" data-testid="primacy-breakdown-badge">
                {data.vote_breakdown.primacy_affected} {t('behavioral.primacyLabel')} ({data.vote_breakdown.first_listed})
              </Badge>
            )}
          </div>

          {/* Method sensitivity table */}
          <div className="fw-semibold mb-1" style={{ fontSize: '0.85rem' }}>
            {t('behavioral.sensitivityTitle')}
          </div>
          <SensitivityTable data={data} candidateNames={candidateNames} t={t} />

          {/* Pedagogical note */}
          <Alert variant="secondary" className="mt-3" style={{ fontSize: '0.8rem' }}>
            <strong>{t('behavioral.noteTitle')}</strong> {data.pedagogical_note}
          </Alert>
        </>
      )}
    </div>
  );
};

export default BehavioralBiasPanel;
