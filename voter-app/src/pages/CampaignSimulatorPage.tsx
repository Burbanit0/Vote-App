import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Control, Range, Select } from '@/components/ui/form-controls';
import { Col, Container, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useMetaTags } from '../hooks/useMetaTags';
import { CHART_COLORS_LIGHT } from '../constants/chartColors';
import { $api } from '../api/hooks';
import type { CampaignResponse } from '../api';

// ── Types ────────────────────────────────────────────────────────────────────

type EventType = 'scandal' | 'gaffe' | 'good_debate' | 'announcement' | 'bad_poll';

interface CampaignEvent {
  id: string;          // client-side only
  day: number;
  type: EventType;
  candidate: number;   // 0-based index
  magnitude: number;
}

// The response shape is the generated `CampaignResponse` (Phase 6 response_model).
// The client-side `CampaignEvent` above is the request-form event (with id +
// the EventType union); the backend echoes events back loosely typed, but the
// panel never reads `result.events`.
type CampaignResult = CampaignResponse;

// ── Constants ─────────────────────────────────────────────────────────────────

const EVENT_ICONS: Record<EventType, string> = {
  scandal:      '💣',
  gaffe:        '📰',
  good_debate:  '🎤',
  announcement: '📢',
  bad_poll:     '📉',
};

const EVENT_LABELS: Record<EventType, string> = {
  scandal:      'Scandale',
  gaffe:        'Gaffe',
  good_debate:  'Bon débat',
  announcement: 'Annonce',
  bad_poll:     'Mauvais sondage',
};

const EVENT_COLORS: Record<EventType, string> = {
  scandal:      '#b71c1c',
  gaffe:        '#b35c00',
  good_debate:  '#1b5e20',
  announcement: '#1a56cc',
  bad_poll:     '#6c757d',
};

const METHODS = [
  { value: 'plurality',  label: 'Pluralité (1 tour)' },
  { value: 'borda',      label: 'Borda' },
  { value: 'irv',        label: 'IRV (préférentiel)' },
  { value: 'approval',   label: 'Approbation' },
  { value: 'schulze',    label: 'Schulze' },
];

function uid() { return `ev-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`; }

// ── Custom tooltip ────────────────────────────────────────────────────────────

function CampaignTooltip({ active, payload, label, candidates }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'var(--bs-body-bg, white)',
      border: '1px solid var(--bs-border-color, #dee2e6)',
      borderRadius: 8, padding: '8px 12px', fontSize: '0.82rem',
      boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
    }}>
      <div className="fw-bold mb-1">Jour {label}</div>
      {[...payload].sort((a, b) => b.value - a.value).map((entry: any) => (
        <div key={entry.dataKey} style={{ color: entry.color }}>
          {entry.name} : <strong>{entry.value?.toFixed(1)} %</strong>
        </div>
      ))}
    </div>
  );
}

// ── Event list item (drag-and-drop) ──────────────────────────────────────────

interface EventItemProps {
  ev: CampaignEvent;
  candidates: string[];
  index: number;
  onRemove: () => void;
  onDragStart: (i: number) => void;
  onDrop: (i: number) => void;
}

const EventItem: React.FC<EventItemProps> = ({
  ev, candidates, index, onRemove, onDragStart, onDrop,
}) => (
  <div
    draggable
    onDragStart={() => onDragStart(index)}
    onDragOver={(e) => e.preventDefault()}
    onDrop={(e) => { e.preventDefault(); onDrop(index); }}
    style={{
      border: '1px solid var(--bs-border-color, #dee2e6)',
      borderRadius: 6,
      padding: '6px 10px',
      marginBottom: 6,
      cursor: 'grab',
      background: 'var(--bs-body-bg, white)',
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      fontSize: '0.82rem',
      userSelect: 'none',
    }}
  >
    <span style={{ color: EVENT_COLORS[ev.type], fontSize: '1.1rem' }} aria-hidden="true">
      {EVENT_ICONS[ev.type]}
    </span>
    <div style={{ flex: 1, overflow: 'hidden' }}>
      <div className="fw-semibold" style={{ color: EVENT_COLORS[ev.type] }}>
        J{ev.day} — {EVENT_LABELS[ev.type]}
      </div>
      <div className="text-muted">
        {candidates[ev.candidate] ?? `Candidat ${ev.candidate}`}
        {ev.magnitude > 0 && ev.type !== 'gaffe' && ` · intensité ${ev.magnitude.toFixed(1)}`}
      </div>
    </div>
    <button
      onClick={onRemove}
      aria-label="Supprimer l'événement"
      style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#dc3545', padding: 0 }}
    >
      ✕
    </button>
  </div>
);

// ── CampaignSimulatorPage ────────────────────────────────────────────────────

const CampaignSimulatorPage: React.FC = () => {
  useMetaTags({
    title: 'Simulateur de campagne — Vote Lab',
    description: 'Simulez l\'évolution des intentions de vote jour par jour pendant une campagne électorale.',
  });

  // ── Config ──
  const [numCandidates, setNumCandidates] = useState(4);
  const [numDays,       setNumDays]       = useState(30);
  const [method,        setMethod]        = useState('plurality');
  const [animSpeed,     setAnimSpeed]     = useState(4); // 0=instant, 10=slow

  // ── Events ──
  const [events, setEvents] = useState<CampaignEvent[]>([]);
  const [newEv, setNewEv]   = useState<Omit<CampaignEvent, 'id'>>({
    day: 10, type: 'scandal', candidate: 0, magnitude: 0.3,
  });
  const [showAddForm, setShowAddForm] = useState(false);
  const [dragFrom,    setDragFrom]    = useState<number | null>(null);

  // ── Results + animation ──
  const sim = $api.useMutation('post', '/api/v2/simulations/campaign');
  const result: CampaignResult | null = sim.data ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? 'Erreur de simulation' : null;
  const [animatedDay,  setAnimatedDay]  = useState(0);
  const [playing,      setPlaying]      = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Candidate names derived from result (or default preview)
  const PREVIEW_NAMES = ['Alice', 'Bob', 'Carol', 'Dave', 'Eve', 'Frank', 'Grace', 'Hugo'];
  const candidateNames = result?.candidates ?? PREVIEW_NAMES.slice(0, numCandidates);

  // ── Auto-play animation ──
  useEffect(() => {
    if (!playing || !result) return;
    const delay = animSpeed === 0 ? 0 : animSpeed * 60;

    if (animSpeed === 0) {
      setAnimatedDay(result.days.length - 1);
      setPlaying(false);
      return;
    }

    timerRef.current = setTimeout(() => {
      setAnimatedDay((prev) => {
        if (prev >= result.days.length - 1) {
          setPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, delay);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [playing, animatedDay, result, animSpeed]);

  // ── Run simulation ──
  const runSimulation = useCallback(() => {
    setPlaying(false);
    setAnimatedDay(0);
    sim.mutate({ body: {
      num_candidates: numCandidates,
      num_voters:     500,
      num_days:       numDays,
      method,
      events: events.map(({ id: _id, ...ev }) => ev),
    } }, {
      onSuccess: (res) => {
        // Start animation automatically
        if (animSpeed > 0) setPlaying(true);
        else setAnimatedDay(res.days.length - 1);
      },
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [numCandidates, numDays, method, events, animSpeed, sim]);

  // ── Chart data (sliced to animatedDay) ──
  const chartData = result
    ? result.days.slice(0, animatedDay + 1).map((day, i) => ({
        day,
        ...Object.fromEntries(result.candidates.map((n) => [n, result.daily_scores[n][i]])),
      }))
    : [];

  // Event markers visible up to animatedDay
  const visibleEvents = events.filter((ev) => ev.day <= (result?.days[animatedDay] ?? 0));

  // ── Event DnD helpers ──
  const handleDrop = (toIndex: number) => {
    if (dragFrom === null || dragFrom === toIndex) return;
    setEvents((prev) => {
      const arr = [...prev];
      const [moved] = arr.splice(dragFrom, 1);
      arr.splice(toIndex, 0, moved);
      return arr;
    });
    setDragFrom(null);
  };

  const addEvent = () => {
    setEvents((prev) => [...prev, { ...newEv, id: uid() }]);
    setShowAddForm(false);
  };

  // ── Lead-change badges ──
  const leaderAtDay = result?.daily_leader[animatedDay] ?? null;

  return (
    <Container fluid className="py-3" style={{ maxWidth: 1400 }}>
      <h2 className="mb-1 fw-bold">📅 Simulateur de campagne</h2>
      <p className="text-muted mb-3" style={{ fontSize: '0.9rem' }}>
        Observez l'évolution des intentions de vote jour par jour. Ajoutez des événements
        (scandales, débats, annonces) et simulez leur impact sur la course.
      </p>

      <Row className="g-3">
        {/* ── Left panel — config ────────────────────────────────────────── */}
        <Col lg={3}>
          <Card className="mb-3">
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2 fw-semibold">⚙️ Configuration</CardHeader>
            <CardBody>
              <div className="mb-3">
                <label htmlFor="camp-cands" className="mb-1 inline-block small mb-1">
                  Candidats : <strong>{numCandidates}</strong>
                </label>
                <Range
                  id="camp-cands" min={2} max={6} step={1}
                  value={numCandidates}
                  onChange={(e) => setNumCandidates(Number(e.target.value))}
                />
              </div>

              <div className="mb-3">
                <label htmlFor="camp-days" className="mb-1 inline-block small mb-1">
                  Durée : <strong>{numDays} jours</strong>
                </label>
                <Range
                  id="camp-days" min={7} max={90} step={1}
                  value={numDays}
                  onChange={(e) => setNumDays(Number(e.target.value))}
                />
              </div>

              <div className="mb-3">
                <label htmlFor="camp-method" className="mb-1 inline-block small mb-1">Méthode de vote</label>
                <Select
                  id="camp-method" size="sm"
                  value={method}
                  onChange={(e) => setMethod(e.target.value)}
                >
                  {METHODS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
                </Select>
              </div>

              <div className="mb-3">
                <label htmlFor="camp-speed" className="mb-1 inline-block small mb-1">
                  Vitesse animation : {animSpeed === 0 ? 'Instant' : `${animSpeed * 60} ms/j`}
                </label>
                <Range
                  id="camp-speed" min={0} max={10} step={1}
                  value={animSpeed}
                  onChange={(e) => setAnimSpeed(Number(e.target.value))}
                />
              </div>

              <Button
                variant="primary" className="w-100"
                onClick={runSimulation} disabled={loading}
              >
                {loading
                  ? <><Spinner size="sm" className="me-2" />Simulation…</>
                  : '▶ Simuler la campagne'}
              </Button>
            </CardBody>
          </Card>

          {/* Candidate legend */}
          <Card>
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2 fw-semibold py-2" style={{ fontSize: '0.85rem' }}>
              Candidats
            </CardHeader>
            <CardBody className="py-2">
              {candidateNames.map((name, i) => (
                <div key={name} className="d-flex align-items-center gap-2 mb-1">
                  <span style={{ width: 12, height: 12, borderRadius: 2, background: CHART_COLORS_LIGHT[i % CHART_COLORS_LIGHT.length], display: 'inline-block', flexShrink: 0 }} />
                  <span style={{ fontSize: '0.85rem' }}>{name}</span>
                  {leaderAtDay === name && <Badge variant="success" style={{ fontSize: '0.65rem' }}>Leader</Badge>}
                </div>
              ))}
            </CardBody>
          </Card>
        </Col>

        {/* ── Centre panel — chart ──────────────────────────────────────── */}
        <Col lg={6}>
          <Card className="h-100">
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2 d-flex align-items-center justify-content-between">
              <strong>Intentions de vote</strong>
              <div className="d-flex align-items-center gap-2">
                {result && (
                  <>
                    <small className="text-muted">
                      Jour {result.days[animatedDay] ?? 0} / {numDays}
                      {result.lead_changes > 0 && ` · ${result.lead_changes} changement${result.lead_changes > 1 ? 's' : ''} de tête`}
                    </small>
                    <Button
                      variant="outline-secondary" size="sm"
                      onClick={() => {
                        if (animatedDay >= result.days.length - 1) {
                          setAnimatedDay(0);
                          setPlaying(true);
                        } else {
                          setPlaying((p) => !p);
                        }
                      }}
                      aria-label={playing ? 'Pause' : 'Lire'}
                    >
                      {playing ? '⏸' : '▶'}
                    </Button>
                    <Button
                      variant="outline-secondary" size="sm"
                      onClick={() => { setAnimatedDay(result.days.length - 1); setPlaying(false); }}
                      aria-label="Fin"
                    >
                      ⏭
                    </Button>
                  </>
                )}
              </div>
            </CardHeader>
            <CardBody>
              {error && <Alert variant="danger" className="mb-3">{error}</Alert>}

              {!result && !loading && (
                <Alert variant="info" style={{ fontSize: '0.88rem' }}>
                  Configurez la campagne et cliquez sur <strong>Simuler</strong>.
                  Ajoutez des événements dans le panneau droit pour voir leur impact.
                </Alert>
              )}

              {(result || loading) && (
                <ResponsiveContainer width="100%" height={340}>
                  <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--bs-border-color, #dee2e6)" />
                    <XAxis
                      dataKey="day"
                      label={{ value: 'Jour', position: 'insideBottom', offset: -12, fontSize: 11 }}
                      tick={{ fontSize: 11 }}
                    />
                    <YAxis
                      domain={[0, 100]}
                      tickFormatter={(v) => `${v}%`}
                      label={{ value: '% intentions', angle: -90, position: 'insideLeft', fontSize: 11 }}
                      tick={{ fontSize: 11 }}
                      width={56}
                    />
                    <Tooltip content={<CampaignTooltip candidates={candidateNames} />} />
                    <Legend verticalAlign="top" wrapperStyle={{ fontSize: '0.82rem' }} />

                    {/* Event markers */}
                    {visibleEvents.map((ev) => (
                      <ReferenceLine
                        key={ev.id}
                        x={ev.day}
                        stroke={EVENT_COLORS[ev.type]}
                        strokeDasharray="4 2"
                        strokeWidth={1.5}
                        label={{
                          value: EVENT_ICONS[ev.type],
                          position: 'top',
                          fontSize: 14,
                          offset: 4,
                        }}
                      />
                    ))}

                    {candidateNames.map((name, i) => (
                      <Line
                        key={name}
                        type="monotone"
                        dataKey={name}
                        stroke={CHART_COLORS_LIGHT[i % CHART_COLORS_LIGHT.length]}
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4 }}
                        isAnimationActive={false}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              )}

              {/* Final summary */}
              {result && animatedDay >= result.days.length - 1 && (
                <div className="d-flex gap-3 mt-2 flex-wrap">
                  <Alert variant="success" className="py-2 mb-0 flex-grow-1" style={{ fontSize: '0.88rem' }}>
                    🏆 Vainqueur final : <strong>{result.final_winner}</strong>
                    {' '}sous la méthode <strong>{METHODS.find((m) => m.value === method)?.label}</strong>
                  </Alert>
                  {result.lead_changes > 0 && (
                    <Alert variant="warning" className="py-2 mb-0" style={{ fontSize: '0.88rem' }}>
                      ⇄ {result.lead_changes} changement{result.lead_changes > 1 ? 's' : ''} de tête
                    </Alert>
                  )}
                </div>
              )}
            </CardBody>
          </Card>
        </Col>

        {/* ── Right panel — events ──────────────────────────────────────── */}
        <Col lg={3}>
          <Card>
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2 d-flex align-items-center justify-content-between">
              <span className="fw-semibold">🗓 Événements</span>
              <Button
                variant="outline-success" size="sm"
                onClick={() => setShowAddForm((v) => !v)}
                aria-expanded={showAddForm}
              >
                {showAddForm ? '✕' : '+ Ajouter'}
              </Button>
            </CardHeader>
            <CardBody>
              {/* Add event form */}
              {showAddForm && (
                <Card className="mb-3 border-success">
                  <CardBody className="py-2 px-3">
                    <Row className="g-2 mb-2">
                      <Col xs={6}>
                        <label className="mb-1 inline-block small mb-1" htmlFor="ev-day">Jour</label>
                        <Control
                          id="ev-day" type="number" size="sm"
                          min={0} max={numDays}
                          value={newEv.day}
                          onChange={(e) => setNewEv({ ...newEv, day: Number(e.target.value) })}
                        />
                      </Col>
                      <Col xs={6}>
                        <label className="mb-1 inline-block small mb-1" htmlFor="ev-type">Type</label>
                        <Select
                          id="ev-type" size="sm"
                          value={newEv.type}
                          onChange={(e) => setNewEv({ ...newEv, type: e.target.value as EventType })}
                        >
                          {Object.entries(EVENT_LABELS).map(([v, l]) => (
                            <option key={v} value={v}>{EVENT_ICONS[v as EventType]} {l}</option>
                          ))}
                        </Select>
                      </Col>
                      <Col xs={6}>
                        <label className="mb-1 inline-block small mb-1" htmlFor="ev-cand">Candidat</label>
                        <Select
                          id="ev-cand" size="sm"
                          value={newEv.candidate}
                          onChange={(e) => setNewEv({ ...newEv, candidate: Number(e.target.value) })}
                        >
                          {candidateNames.map((n, i) => (
                            <option key={i} value={i}>{n}</option>
                          ))}
                        </Select>
                      </Col>
                      <Col xs={6}>
                        <label className="mb-1 inline-block small mb-1" htmlFor="ev-mag">
                          Intensité : {newEv.magnitude.toFixed(1)}
                        </label>
                        <Range
                          id="ev-mag" min={0.1} max={0.5} step={0.1}
                          value={newEv.magnitude}
                          onChange={(e) => setNewEv({ ...newEv, magnitude: Number(e.target.value) })}
                        />
                      </Col>
                    </Row>
                    <Button variant="success" size="sm" className="w-100" onClick={addEvent}>
                      Ajouter l'événement
                    </Button>
                  </CardBody>
                </Card>
              )}

              {/* Events legend */}
              <div className="mb-2 d-flex flex-wrap gap-1" style={{ fontSize: '0.75rem' }}>
                {Object.entries(EVENT_ICONS).map(([type, icon]) => (
                  <span key={type} style={{ color: EVENT_COLORS[type as EventType] }}>
                    {icon} {EVENT_LABELS[type as EventType]}
                  </span>
                ))}
              </div>

              {/* Events list */}
              {events.length === 0 ? (
                <p className="text-muted small mb-0">
                  Aucun événement. Cliquez sur "+" pour en ajouter.
                </p>
              ) : (
                <div role="list" aria-label="Liste des événements">
                  {events.map((ev, i) => (
                    <EventItem
                      key={ev.id}
                      ev={ev}
                      candidates={candidateNames}
                      index={i}
                      onRemove={() => setEvents((prev) => prev.filter((e) => e.id !== ev.id))}
                      onDragStart={setDragFrom}
                      onDrop={handleDrop}
                    />
                  ))}
                </div>
              )}

              {/* Quick-add preset events */}
              <hr className="my-3" />
              <p className="text-muted small mb-2">Préréglages rapides :</p>
              <div className="d-flex flex-wrap gap-1">
                {[
                  { label: '💣 Scandale Alice J10', ev: { day: 10, type: 'scandal' as EventType, candidate: 0, magnitude: 0.3 } },
                  { label: '🎤 Débat Bob J15',      ev: { day: 15, type: 'good_debate' as EventType, candidate: 1, magnitude: 0.2 } },
                  { label: '📰 Gaffe Carol J20',    ev: { day: 20, type: 'gaffe' as EventType, candidate: 2, magnitude: 0.1 } },
                ].map(({ label, ev }) => (
                  <Button
                    key={label}
                    variant="outline-secondary"
                    size="sm"
                    style={{ fontSize: '0.72rem' }}
                    onClick={() => setEvents((prev) => [...prev, { ...ev, id: uid() }])}
                    disabled={ev.candidate >= numCandidates}
                  >
                    {label}
                  </Button>
                ))}
              </div>
            </CardBody>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default CampaignSimulatorPage;
