import React, { useMemo, useState } from 'react';
import { Alert, Badge, Button, Card, Col, Modal, Row, Table } from 'react-bootstrap';
import { SimulationCompareResult } from '../../types';
import {
  IDEOLOGY_OPTIONS,
  METHOD_DESCRIPTIONS,
  ScenarioConfig,
  mostCommonWinner,
} from './simulationConstants';
import MethodTooltip from '../shared/MethodTooltip';
import ResponsiveTable from '../shared/ResponsiveTable';
import { useTranslation } from 'react-i18next';

const WINNER_BADGE_STYLE: React.CSSProperties = {
  maxWidth: 80,
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
  display: 'inline-block',
  verticalAlign: 'middle',
};

// ── WinnerMatrixTable ───────────────────────────────────────────────────────

interface TableProps {
  results: SimulationCompareResult[];
  allMethodNames: string[];
  colorMap: Record<string, string>;
  label?: string;
  onCellClick?: (methodKey: string, simIndex: number) => void;
}

const WinnerMatrixTable: React.FC<TableProps> = ({ results, allMethodNames, colorMap, label, onCellClick }) => {
  const { t } = useTranslation();
  return (
    <ResponsiveTable>
    {label && (
      <p className="fw-semibold text-center mb-2" style={{ fontSize: '0.9rem' }}>{label}</p>
    )}
    <Table bordered hover size="sm" style={{ minWidth: 500 }}>
      <thead className="table-light">
        <tr>
          <th style={{ minWidth: 130 }}>{t('common.method')}</th>
          {results.map((_, i) => (
            <th key={i} className="text-center" style={{ minWidth: 72 }}>#{i + 1}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {allMethodNames.map((method) => (
          <tr key={method}>
            <td><strong><MethodTooltip method={method} /></strong></td>
            {results.map((r, i) => {
              const winner = r.methods[method]?.winner;
              const notCondorcet = r.condorcet_winner && r.methods[method]?.condorcet_consistent === false;
              return (
                <td
                  key={i}
                  className="text-center"
                  style={onCellClick ? { cursor: 'pointer' } : undefined}
                  onClick={onCellClick ? () => onCellClick(method, i) : undefined}
                  title={onCellClick ? t('simulation.clickForDetails') : undefined}
                >
                  {winner ? (
                    <Badge style={{ backgroundColor: colorMap[winner] ?? '#999', fontSize: '0.72rem', ...WINNER_BADGE_STYLE }}>
                      {winner}{notCondorcet ? ' *' : ''}
                    </Badge>
                  ) : (
                    <span className="text-muted">—</span>
                  )}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </Table>
  </ResponsiveTable>
  );
};

// ── WinnerMatrixTab ─────────────────────────────────────────────────────────

interface Props {
  comparisonResults: SimulationCompareResult[];
  resultsB: SimulationCompareResult[] | null;
  allMethodNames: string[];
  candidateColorMap: Record<string, string>;
  configA: ScenarioConfig;
  configB: ScenarioConfig;
  numSimulations: number;
  scenarioCount: 1 | 2;
}

const WinnerMatrixTab: React.FC<Props> = ({
  comparisonResults, resultsB, allMethodNames, candidateColorMap,
  configA, configB, numSimulations, scenarioCount,
}) => {
  const { t } = useTranslation();
  const [drilldownTarget, setDrilldownTarget] = useState<{ methodKey: string; simIndex: number } | null>(null);

  const diffData = useMemo(() => {
    if (!resultsB || !allMethodNames.length) return [];
    return allMethodNames
      .map((method) => ({
        method,
        winnerA: mostCommonWinner(comparisonResults, method),
        winnerB: mostCommonWinner(resultsB, method),
      }))
      .sort((a, b) => (a.winnerA !== a.winnerB ? 0 : 1) - (b.winnerA !== b.winnerB ? 0 : 1));
  }, [allMethodNames, comparisonResults, resultsB]);

  const labelA = `${t('simulation.scenarioA')} — ${configA.candidateInput} (${IDEOLOGY_OPTIONS.find((o) => o.value === configA.ideology_distribution)?.labelKey ?? configA.ideology_distribution})`;
  const labelB = `${t('simulation.scenarioB')} — ${configB.candidateInput} (${IDEOLOGY_OPTIONS.find((o) => o.value === configB.ideology_distribution)?.labelKey ?? configB.ideology_distribution})`;

  // Colour legend
  const legend = (
    <div className="mb-3 d-flex gap-3 flex-wrap align-items-center">
      {Object.entries(candidateColorMap).map(([name, color]) => (
        <span key={name} className="d-flex align-items-center gap-1">
          <span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: 3, backgroundColor: color }} />
          <small>{name}</small>
        </span>
      ))}
      {comparisonResults.some((r) =>
        Object.values(r.methods).some((m) => m.condorcet_consistent === false)
      ) && <small className="text-muted">{t('simulation.notCondorcet')}</small>}
    </div>
  );

  return (
    <>
      {legend}

      {scenarioCount === 2 && resultsB ? (
        <>
          <Row className="g-3 mb-4">
            <Col md={6}>
              <WinnerMatrixTable
                results={comparisonResults} allMethodNames={allMethodNames}
                colorMap={candidateColorMap} label={labelA}
                onCellClick={(m, i) => setDrilldownTarget({ methodKey: m, simIndex: i })}
              />
            </Col>
            <Col md={6}>
              <WinnerMatrixTable
                results={resultsB} allMethodNames={allMethodNames}
                colorMap={candidateColorMap} label={labelB}
              />
            </Col>
          </Row>

          <Card>
            <Card.Header>
              <strong>{t('simulation.differences')}</strong>
              <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
                {t('simulation.mostFrequentWinner', { n: numSimulations })}
              </span>
            </Card.Header>
            <Card.Body className="p-0">
              <ResponsiveTable>
              <Table bordered size="sm" className="mb-0">
                <thead className="table-light">
                  <tr>
                    <th style={{ minWidth: 140 }}>{t('common.method')}</th>
                    <th className="text-center">{t('simulation.winnerScenarioA')}</th>
                    <th className="text-center">{t('simulation.winnerScenarioB')}</th>
                    <th className="text-center" style={{ width: 60 }}></th>
                  </tr>
                </thead>
                <tbody>
                  {diffData.map(({ method, winnerA, winnerB }) => {
                    const differs = winnerA !== winnerB;
                    return (
                      <tr key={method} style={differs ? { backgroundColor: '#fff8e1' } : undefined}>
                        <td><strong><MethodTooltip method={method} /></strong></td>
                        <td className="text-center">
                          {winnerA ? (
                            <Badge style={{ backgroundColor: candidateColorMap[winnerA] ?? '#999', ...WINNER_BADGE_STYLE }}>{winnerA}</Badge>
                          ) : <span className="text-muted">—</span>}
                        </td>
                        <td className="text-center">
                          {winnerB ? (
                            <Badge style={{ backgroundColor: candidateColorMap[winnerB] ?? '#999', ...WINNER_BADGE_STYLE }}>{winnerB}</Badge>
                          ) : <span className="text-muted">—</span>}
                        </td>
                        <td className="text-center fw-bold" style={{ fontSize: '1.1rem' }}>
                          {differs
                            ? <span style={{ color: '#dc3545' }}>✗</span>
                            : <span style={{ color: '#198754' }}>✓</span>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </Table>
              </ResponsiveTable>
            </Card.Body>
          </Card>
        </>
      ) : (
        <Card>
          <Card.Body>
            <WinnerMatrixTable
              results={comparisonResults} allMethodNames={allMethodNames}
              colorMap={candidateColorMap}
              onCellClick={(m, i) => setDrilldownTarget({ methodKey: m, simIndex: i })}
            />
            <small className="text-muted d-block mt-2">
              {t('simulation.clickCellHint')}
            </small>
          </Card.Body>
        </Card>
      )}

      {/* Drill-down modal */}
      {drilldownTarget && (() => {
        const { methodKey, simIndex } = drilldownTarget;
        const r = comparisonResults[simIndex];
        const m = r?.methods[methodKey];
        if (!r || !m) return null;
        const winner = m.winner;

        return (
          <Modal show centered size="lg" onHide={() => setDrilldownTarget(null)}>
            <Modal.Header closeButton>
              <Modal.Title>
                <MethodTooltip method={methodKey} />
                <span className="text-muted fw-normal ms-2" style={{ fontSize: '1rem' }}>
                  — Simulation #{simIndex + 1}
                </span>
              </Modal.Title>
            </Modal.Header>
            <Modal.Body>
              <div className="text-center mb-4">
                <div className="text-muted small mb-1">{t('simulation.winner')}</div>
                {winner ? (
                  <Badge style={{ backgroundColor: candidateColorMap[winner] ?? '#999', fontSize: '1.1rem', padding: '0.45em 1.1em' }}>
                    {winner}
                  </Badge>
                ) : <span className="text-muted">{t('simulation.noWinner')}</span>}
              </div>

              <Table bordered size="sm" className="mb-3">
                <tbody>
                  {[
                    { label: t('simulation.bayesianRegret'), value: m.bayesian_regret != null ? m.bayesian_regret.toFixed(4) : '—', note: t('simulation.lowerBetter') },
                    { label: t('simulation.majoritySatisfaction'), value: m.majority_satisfaction != null ? `${(m.majority_satisfaction * 100).toFixed(1)} %` : '—', note: t('simulation.higherBetter') },
                    { label: t('simulation.strategicVulnerability'), value: m.strategic_vulnerability != null ? `${(m.strategic_vulnerability * 100).toFixed(1)} %` : '—', note: t('simulation.lowerBetter') },
                  ].map(({ label, value, note }) => (
                    <tr key={label}>
                      <td className="fw-semibold" style={{ width: '40%' }}>{label}</td>
                      <td>{value}</td>
                      <td className="text-muted small">{note}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>

              {r.condorcet_winner ? (
                  m.condorcet_consistent ? (
                    <Alert variant="success" className="py-2 mb-3">{t('simulation.electedCondorcet')}</Alert>
                  ) : (
                    <Alert variant="warning" className="py-2 mb-3">
                      {t('simulation.condorcetWas')}
                      <strong>
                        <Badge style={{ backgroundColor: candidateColorMap[r.condorcet_winner] ?? '#999' }}>
                          {r.condorcet_winner}
                        </Badge>
                      </strong>
                    </Alert>
                  )
                ) : (
                  <Alert variant="secondary" className="py-2 mb-3">
                    {t('simulation.noCondorcetWinner')}
                  </Alert>
                )}

              <p className="text-muted small mb-0" style={{ lineHeight: 1.6 }}>
                <strong><MethodTooltip method={methodKey} />: </strong>
                {METHOD_DESCRIPTIONS[methodKey] ?? t('simulation.noDescription')}
              </p>
            </Modal.Body>
            <Modal.Footer>
              <Button variant="secondary" onClick={() => setDrilldownTarget(null)}>{t('common.close')}</Button>
            </Modal.Footer>
          </Modal>
        );
      })()}
    </>
  );
};

export default WinnerMatrixTab;
