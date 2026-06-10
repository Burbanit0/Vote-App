/**
 * SenParadoxPanel — demonstrates Sen's Impossibility of a Paretian Liberal (1970):
 * no social choice rule can simultaneously satisfy Pareto efficiency and
 * minimal individual liberalism.
 */
import React, { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Control } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import { $api } from '../../api/hooks';
import type { SenParadoxResponse } from '../../api';

const ALTS = ['x', 'y', 'z'] as const;

// ── Types ─────────────────────────────────────────────────────────────────────
// Source of truth is the generated `SenParadoxResponse` (Phase 6 response_model).

type SenData = SenParadoxResponse;
type ParadoxExample = SenParadoxResponse['paradox_examples'][number];
type ResolutionOption = SenParadoxResponse['resolution_options'][number];

// ── Conflict visualisation SVG ────────────────────────────────────────────────

interface ConflictProps {
  data: SenData;
}

const ConflictViz: React.FC<ConflictProps> = ({ data }) => {
  const hasConflict = data.paradox_exists;
  return (
    <svg data-testid="conflict-viz-svg" width={320} height={160} style={{ display: 'block' }}>
      {/* Pareto node */}
      <ellipse
        cx={60}
        cy={80}
        rx={52}
        ry={30}
        fill={hasConflict ? '#dc354520' : '#19875420'}
        stroke={hasConflict ? '#dc3545' : '#198754'}
        strokeWidth={2}
      />
      <text
        x={60}
        y={76}
        textAnchor="middle"
        style={{ fontSize: 11, fontWeight: 700, fill: '#495057' }}
      >
        Pareto
      </text>
      <text x={60} y={92} textAnchor="middle" style={{ fontSize: 9, fill: '#6c757d' }}>
        Efficacité
      </text>

      {/* Liberté node */}
      <ellipse
        cx={260}
        cy={80}
        rx={52}
        ry={30}
        fill={hasConflict ? '#dc354520' : '#19875420'}
        stroke={hasConflict ? '#dc3545' : '#198754'}
        strokeWidth={2}
      />
      <text
        x={260}
        y={76}
        textAnchor="middle"
        style={{ fontSize: 11, fontWeight: 700, fill: '#495057' }}
      >
        Liberté
      </text>
      <text x={260} y={92} textAnchor="middle" style={{ fontSize: 9, fill: '#6c757d' }}>
        Individuelle
      </text>

      {/* Arrow */}
      <defs>
        <marker id="arr" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 Z" fill={hasConflict ? '#dc3545' : '#198754'} />
        </marker>
      </defs>
      <line
        x1={113}
        y1={70}
        x2={207}
        y2={70}
        stroke={hasConflict ? '#dc3545' : '#198754'}
        strokeWidth={2.5}
        markerEnd="url(#arr)"
        strokeDasharray={hasConflict ? '6 3' : undefined}
      />
      <line
        x1={207}
        y1={90}
        x2={113}
        y2={90}
        stroke={hasConflict ? '#dc3545' : '#198754'}
        strokeWidth={2.5}
        markerEnd="url(#arr)"
        strokeDasharray={hasConflict ? '6 3' : undefined}
      />
      <text
        x={160}
        y={64}
        textAnchor="middle"
        style={{ fontSize: 9, fill: hasConflict ? '#dc3545' : '#198754', fontWeight: 700 }}
      >
        {hasConflict ? '⚡ Contradiction' : '✓ Compatible'}
      </text>
    </svg>
  );
};

// ── Main panel ────────────────────────────────────────────────────────────────

const SenParadoxPanel: React.FC = () => {
  const { t } = useTranslation();

  const [seed, setSeed] = useState(42);
  const sim = $api.useMutation('post', '/api/v2/theory/sen-paradox');
  const simCustom = $api.useMutation('post', '/api/v2/theory/sen-paradox');
  const data: SenData | null = sim.data ?? null;
  const loading = sim.isPending || simCustom.isPending;
  const error = sim.isError ? t('sen.error') : null;

  // Interactive: user sets their own preferences for Person 1
  const [userPref1, setUserPref1] = useState(['z', 'x', 'y']);
  const [userPref2, setUserPref2] = useState(['x', 'y', 'z']);
  const [customResult, setCustomResult] = useState<ParadoxExample | null>(null);

  const runSimulation = useCallback(() => {
    setCustomResult(null);
    sim.mutate({
      body: {
        num_voters: 2,
        seed,
        rights_definition: 'liberal',
      },
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seed, t, sim]);

  const testCustomPrefs = useCallback(() => {
    if (!data) return;
    simCustom.mutate(
      {
        body: {
          num_voters: 2,
          seed,
          rights_definition: 'liberal',
        },
      },
      {
        onSuccess: (res) => {
          const ex = res.paradox_examples;
          setCustomResult(ex.length > 0 ? ex[0] : null);
        },
      }
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, seed, simCustom]);

  const swapPref1 = (arr: string[], i: number, j: number) => {
    const next = [...arr];
    [next[i], next[j]] = [next[j], next[i]];
    setUserPref1(next);
  };
  const swapPref2 = (arr: string[], i: number, j: number) => {
    const next = [...arr];
    [next[i], next[j]] = [next[j], next[i]];
    setUserPref2(next);
  };

  const altLabel = (a: string) => data?.alternative_names[a] ?? a;

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 items-end">
        <Col xs={6} md={3}>
          <label className="mb-1 inline-block text-sm mb-0">{t('sen.seed')}</label>
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
            variant="primary"
            onClick={runSimulation}
            disabled={loading}
            data-testid="simulate-btn"
          >
            {loading ? <Spinner size="sm" /> : t('sen.run')}
          </Button>
        </Col>
      </Row>

      {!data && !loading && !error && (
        <Alert variant="info" role="alert">
          {t('sen.prompt')}
        </Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}

      {data && (
        <>
          {/* Headline badges */}
          <div className="flex flex-wrap gap-2 mb-3">
            <Badge variant={data.paradox_exists ? 'danger' : 'success'} data-testid="paradox-badge">
              {data.paradox_exists ? t('sen.paradoxExists') : t('sen.noParadox')}
            </Badge>
            <Badge variant="warning" data-testid="frequency-badge">
              {t('sen.frequency')}: {Math.round(data.paradox_frequency * 100)}%
            </Badge>
          </div>

          <Row className="g-3">
            <Col xs={12} md={6}>
              {/* Conflict visualisation */}
              <div className="font-semibold mb-1" style={{ fontSize: '0.85rem' }}>
                {t('sen.vizTitle')}
              </div>
              <div
                className="border border-border rounded p-2 mb-3"
                style={{ background: '#f8f9fa' }}
              >
                <ConflictViz data={data} />
              </div>

              {/* Canonical example */}
              {data.paradox_examples.length > 0 && (
                <div data-testid="paradox-example">
                  {data.paradox_examples.slice(0, 1).map((ex, i) => (
                    <Card key={i} className="border-danger mb-2">
                      <CardHeader
                        className="block space-y-0 border-b border-border px-4 py-2 py-1 bg-[#dc3545] bg-opacity-10"
                        style={{ fontSize: '0.8rem', fontWeight: 700 }}
                      >
                        ⚡ {ex.name}
                      </CardHeader>
                      <CardBody className="py-2">
                        <div className="flex gap-4 mb-2" style={{ fontSize: '0.78rem' }}>
                          <div>
                            <div className="text-muted-foreground">{t('sen.person1')}:</div>
                            {ex.voters_preferences[0].map((a, j) => (
                              <div key={j}>
                                {j + 1}. {altLabel(a)}
                              </div>
                            ))}
                          </div>
                          <div>
                            <div className="text-muted-foreground">{t('sen.person2')}:</div>
                            {ex.voters_preferences[1].map((a, j) => (
                              <div key={j}>
                                {j + 1}. {altLabel(a)}
                              </div>
                            ))}
                          </div>
                        </div>
                        <div className="flex gap-3 mb-1" style={{ fontSize: '0.78rem' }}>
                          <div>
                            <span className="text-muted-foreground">
                              {t('sen.liberalOutcome')}:
                            </span>
                            <Badge variant="warning" className="ms-1">
                              {altLabel(ex.liberal_outcome)}
                            </Badge>
                          </div>
                          <div>
                            <span className="text-muted-foreground">{t('sen.paretoOutcome')}:</span>
                            <Badge variant="primary" className="ms-1">
                              {altLabel(ex.pareto_outcome)}
                            </Badge>
                          </div>
                        </div>
                        <div className="text-[#dc3545]" style={{ fontSize: '0.75rem' }}>
                          {ex.explanation}
                        </div>
                      </CardBody>
                    </Card>
                  ))}
                </div>
              )}

              {/* Real world analogy */}
              <Alert variant="light" style={{ fontSize: '0.78rem', border: '1px solid #dee2e6' }}>
                🏙 <strong>{t('sen.analogyTitle')}</strong> {data.real_world_analogy}
              </Alert>
            </Col>

            <Col xs={12} md={6}>
              {/* Resolution options */}
              <div className="font-semibold mb-2" style={{ fontSize: '0.85rem' }}>
                {t('sen.resolutionsTitle')}
              </div>
              {data.resolution_options.map((r, i) => (
                <Card
                  key={i}
                  className="mb-2"
                  style={{ fontSize: '0.78rem' }}
                  data-testid={`resolution-${i}`}
                >
                  <CardBody className="py-2">
                    <div className="font-semibold">
                      {r.name}
                      <span className="text-muted-foreground ms-2" style={{ fontSize: '0.68rem' }}>
                        ({r.theorist})
                      </span>
                    </div>
                    <div style={{ color: '#198754' }}>✓ {r.outcome}</div>
                    <div style={{ color: '#dc3545' }}>✗ {r.cost}</div>
                  </CardBody>
                </Card>
              ))}

              {/* Pedagogical note */}
              <Alert variant="secondary" style={{ fontSize: '0.78rem' }}>
                <strong>{t('sen.noteTitle')}</strong> {data.pedagogical_note}
              </Alert>
            </Col>
          </Row>
        </>
      )}
    </div>
  );
};

export default SenParadoxPanel;
