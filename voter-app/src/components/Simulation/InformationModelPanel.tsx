/**
 * InformationModelPanel — Configure and display asymmetric information effects.
 *
 * Allows the user to:
 *   1. Toggle the information asymmetry model on/off.
 *   2. Set the media bias for each candidate (−1 = very unfavourable, +1 = very favourable).
 *   3. Set the proportion of voters in each information segment (must sum to 100%).
 *
 * After simulation, displays:
 *   - Sincere winner (true utilities) vs. perceived winner (distorted utilities).
 *   - Visual alert when the two winners differ.
 *   - Information gap metric.
 */
import React, { useCallback } from 'react';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Check, Range } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { OverlayTrigger, Tooltip } from '@/components/ui/tooltip-overlay';
import { InformationModelResult } from '../../types';
import { InformationModelConfig } from '../../services/simulationCompareApi';

// ── Types ─────────────────────────────────────────────────────────────────────

interface Props {
  candidateNames: string[];
  config: InformationModelConfig;
  onChange: (cfg: InformationModelConfig) => void;
  /** Latest simulation result — undefined before first run. */
  result?: InformationModelResult;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function pct(v: number) { return `${(v * 100).toFixed(0)} %`; }

function gapColor(gap: number): string {
  if (gap < 0.05) return '#1b5e20';    // green — low distortion
  if (gap < 0.15) return '#b35c00';    // orange — moderate
  return '#b71c1c';                     // red — high distortion
}

// ── InformationModelPanel ─────────────────────────────────────────────────────

const InformationModelPanel: React.FC<Props> = ({
  candidateNames, config, onChange, result,
}) => {
  const { enabled, media_bias, voter_segments } = config;

  // ── Toggle ──────────────────────────────────────────────────────────────
  const handleToggle = () => onChange({ ...config, enabled: !enabled });

  // ── Media bias slider ───────────────────────────────────────────────────
  const handleBias = useCallback((idx: number, value: number) => {
    onChange({
      ...config,
      media_bias: { ...media_bias, [String(idx)]: value },
    });
  }, [config, media_bias, onChange]);

  // ── Voter segments — auto-adjust remaining when one changes ─────────────
  const handleSegment = useCallback((
    key: 'low_info' | 'medium_info' | 'high_info',
    rawValue: number,
  ) => {
    const value = Math.max(0, Math.min(1, rawValue));
    const others = (['low_info', 'medium_info', 'high_info'] as const).filter((k) => k !== key);
    const remaining = Math.max(0, 1 - value);
    const otherSum = others.reduce((s, k) => s + (voter_segments[k] ?? 0), 0);

    let newSegs = { ...voter_segments, [key]: value };
    if (otherSum > 0) {
      for (const k of others) {
        newSegs[k] = ((voter_segments[k] ?? 0) / otherSum) * remaining;
      }
    } else {
      // Edge case: other segments were 0 — split remaining evenly
      for (const k of others) {
        newSegs[k] = remaining / others.length;
      }
    }
    onChange({ ...config, voter_segments: newSegs });
  }, [config, voter_segments, onChange]);

  const totalSeg = (voter_segments.low_info + voter_segments.medium_info + voter_segments.high_info);
  const segError = Math.abs(totalSeg - 1) > 0.01;

  // ── Bias labels ──────────────────────────────────────────────────────────
  function biasLabel(v: number): string {
    if (v >  0.6) return 'Très favorable';
    if (v >  0.2) return 'Favorable';
    if (v > -0.2) return 'Neutre';
    if (v > -0.6) return 'Défavorable';
    return 'Très défavorable';
  }
  function biasColor(v: number): string {
    if (v > 0.2) return '#1b5e20';
    if (v < -0.2) return '#b71c1c';
    return '#6c757d';
  }

  return (
    <div>
      {/* ── Toggle ──────────────────────────────────────────────────────── */}
      <div className="d-flex align-items-center justify-content-between mb-3">
        <div>
          <Check
            type="switch"
            id="info-model-toggle"
            label={
              <span className="fw-semibold">
                Activer le modèle d'information asymétrique
              </span>
            }
            checked={enabled}
            onChange={handleToggle}
          />
          <div className="text-muted small mt-1">
            Les électeurs perçoivent les positions des candidats avec un biais
            médiatique et un niveau de bruit dépendant de leur exposition à l'information.
          </div>
        </div>
      </div>

      {!enabled && (
        <Alert variant="secondary" className="py-2" style={{ fontSize: '0.85rem' }}>
          Activez le modèle pour configurer les biais et observer leur impact sur le résultat.
        </Alert>
      )}

      {enabled && (
        <>
          {/* ── Voter segments ──────────────────────────────────────────── */}
          <Card className="mb-3">
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2 py-2 fw-semibold" style={{ fontSize: '0.88rem' }}>
              📊 Composition de l'électorat
            </CardHeader>
            <CardBody>
              {segError && (
                <Alert variant="warning" className="py-2 mb-2" style={{ fontSize: '0.8rem' }}>
                  Les segments ne totalisent pas 100 % ({(totalSeg * 100).toFixed(0)} %).
                </Alert>
              )}

              {(
                [
                  { key: 'low_info',    label: 'Peu informés',          color: '#b71c1c', sigma: '0.40', mw: '×1.5' },
                  { key: 'medium_info', label: 'Modérément informés',   color: '#b35c00', sigma: '0.20', mw: '×1.0' },
                  { key: 'high_info',   label: 'Bien informés',         color: '#1b5e20', sigma: '0.05', mw: '×0.3' },
                ] as const
              ).map(({ key, label, color, sigma, mw }) => (
                <Row key={key} className="align-items-center mb-2 g-2">
                  <Col xs={5}>
                    <OverlayTrigger
                      placement="right"
                      overlay={
                        <Tooltip id={`seg-tip-${key}`}>
                          Bruit σ={sigma} · Poids média {mw}
                        </Tooltip>
                      }
                    >
                      <span style={{ fontSize: '0.85rem', color, cursor: 'help', borderBottom: '1px dashed' }}>
                        {label}
                      </span>
                    </OverlayTrigger>
                  </Col>
                  <Col xs={5}>
                    <Range
                      min={0} max={1} step={0.01}
                      value={voter_segments[key]}
                      onChange={(e) => handleSegment(key, Number(e.target.value))}
                      aria-label={`${label}: ${pct(voter_segments[key])}`}
                    />
                  </Col>
                  <Col xs={2} className="text-end">
                    <Badge variant="secondary" style={{ fontSize: '0.75rem' }}>
                      {pct(voter_segments[key])}
                    </Badge>
                  </Col>
                </Row>
              ))}
            </CardBody>
          </Card>

          {/* ── Media bias per candidate ──────────────────────────────────── */}
          <Card className="mb-3">
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2 py-2 fw-semibold" style={{ fontSize: '0.88rem' }}>
              📺 Biais médiatique par candidat
            </CardHeader>
            <CardBody>
              <div className="text-muted small mb-2">
                −1 = couverture très défavorable · 0 = neutre · +1 = couverture très favorable
              </div>
              {candidateNames.map((name, idx) => {
                const bias = Number(media_bias[String(idx)] ?? 0);
                return (
                  <Row key={idx} className="align-items-center mb-2 g-2">
                    <Col xs={4}>
                      <span className="fw-semibold" style={{ fontSize: '0.88rem' }}>{name}</span>
                    </Col>
                    <Col xs={5}>
                      <Range
                        min={-1} max={1} step={0.05}
                        value={bias}
                        onChange={(e) => handleBias(idx, Number(e.target.value))}
                        aria-label={`Biais médiatique pour ${name}: ${bias.toFixed(2)}`}
                      />
                    </Col>
                    <Col xs={3} className="d-flex align-items-center gap-1">
                      <span className="fw-semibold" style={{ color: biasColor(bias), fontSize: '0.82rem' }}>
                        {bias >= 0 ? '+' : ''}{bias.toFixed(2)}
                      </span>
                      <span className="text-muted" style={{ fontSize: '0.72rem' }}>
                        {biasLabel(bias)}
                      </span>
                    </Col>
                  </Row>
                );
              })}
            </CardBody>
          </Card>

          {/* ── Results ────────────────────────────────────────────────────── */}
          {result && result.enabled && (
            <Card>
              <CardHeader className="block space-y-0 border-b border-border px-4 py-2 py-2 fw-semibold" style={{ fontSize: '0.88rem' }}>
                🔍 Impact sur le résultat
              </CardHeader>
              <CardBody>
                <Row className="g-3 mb-3">
                  <Col md={6}>
                    <div className="text-muted small mb-1">Gagnant sincère (vraies utilités)</div>
                    <Badge
                      style={{ fontSize: '0.9rem', padding: '6px 14px', background: '#1b5e20' }}
                    >
                      {result.sincere_winner ?? '—'}
                    </Badge>
                  </Col>
                  <Col md={6}>
                    <div className="text-muted small mb-1">Gagnant perçu (utilités biaisées)</div>
                    <Badge
                      style={{
                        fontSize: '0.9rem',
                        padding: '6px 14px',
                        background: result.winners_differ ? '#b71c1c' : '#1b5e20',
                      }}
                    >
                      {result.perceived_winner ?? '—'}
                    </Badge>
                  </Col>
                </Row>

                {result.winners_differ && (
                  <Alert variant="danger" className="py-2 mb-3" style={{ fontSize: '0.88rem' }}>
                    ⚠️ <strong>Les biais d'information changent le résultat !</strong>{' '}
                    En réalité, <strong>{result.sincere_winner}</strong> aurait gagné.
                    La désinformation conduit à l'élection de{' '}
                    <strong>{result.perceived_winner}</strong>.
                  </Alert>
                )}

                {!result.winners_differ && (
                  <Alert variant="success" className="py-2 mb-3" style={{ fontSize: '0.88rem' }}>
                    ✓ Les biais d'information ne changent pas le vainqueur dans cette simulation.
                  </Alert>
                )}

                <div className="d-flex gap-4 flex-wrap" style={{ fontSize: '0.85rem' }}>
                  <div>
                    <span className="text-muted">Écart d'information :</span>{' '}
                    <strong style={{ color: gapColor(result.information_gap ?? 0) }}>
                      {((result.information_gap ?? 0) * 100).toFixed(1)} %
                    </strong>
                    <span className="text-muted ms-1" style={{ fontSize: '0.75rem' }}>
                      (distorsion moyenne des utilités)
                    </span>
                  </div>
                  {result.sincere_condorcet_winner && (
                    <div>
                      <span className="text-muted">Vainqueur de Condorcet sincère :</span>{' '}
                      <strong>{result.sincere_condorcet_winner}</strong>
                    </div>
                  )}
                </div>
              </CardBody>
            </Card>
          )}
        </>
      )}
    </div>
  );
};

export default InformationModelPanel;
