import React from 'react';
import { Alert, Badge, Button, Card, Col, Row, Table } from 'react-bootstrap';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router';
import { useElection } from '../../stores/useElectionStore';
import { ElectionResult } from '../../services/electionApi';
import { HISTORICAL_SCENARIOS } from '../../data/historicalScenarios';

const CORE_METHODS = ['plurality', 'irv', 'borda', 'schulze', 'approval'] as const;

const PHENOMENON_VARIANT: Record<string, string> = {
  'Paradoxe de Condorcet': 'danger',
  'Effet spoiler':          'warning',
  'Fragmentation & coalition': 'info',
  "Cycle d'Arrow (intransitivité)": 'secondary',
  'Consensus parfait (Condorcet)': 'success',
  'Fragmentation & vote blanc': 'warning',
  'Crise constitutionnelle': 'danger',
};

interface Props {
  result: ElectionResult | null;
}

const HistoricalReferencePanel: React.FC<Props> = ({ result }) => {
  const { t }           = useTranslation();
  const { scenarioMeta } = useElection();
  const navigate        = useNavigate();

  if (!scenarioMeta) return null;

  const data = HISTORICAL_SCENARIOS[scenarioMeta.id];
  if (!data) return null;

  const variant = PHENOMENON_VARIANT[data.phenomenon] ?? 'secondary';

  return (
    <Card className="mt-3 border-2" style={{ borderColor: `var(--bs-${variant})` }}>
      <Card.Header
        className="d-flex align-items-center gap-2 flex-wrap py-2"
        style={{ background: `var(--bs-${variant}-bg-subtle, #f8f9fa)` }}
      >
        <span style={{ fontSize: '1.2rem' }}>{data.flag}</span>
        <strong style={{ fontSize: '0.9rem' }}>{data.name}</strong>
        {data.year > 0 && (
          <Badge bg="secondary" style={{ fontSize: '0.65rem' }}>{data.year}</Badge>
        )}
        <Badge bg={variant} style={{ fontSize: '0.65rem' }}>
          {t('scenarios.phenomenon')}: {data.phenomenon}
        </Badge>
        <div className="ms-auto d-flex gap-2 align-items-center">
          <Button
            size="sm"
            variant="outline-primary"
            style={{ fontSize: '0.7rem', padding: '2px 8px' }}
            onClick={() => navigate('/election-lab#replay')}
            data-testid="open-replay-btn"
          >
            📺 {t('replay.openReplay')}
          </Button>
          {data.reference && (
            <a
              href={data.reference}
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted"
              style={{ fontSize: '0.72rem' }}
            >
              Wikipedia ↗
            </a>
          )}
        </div>
      </Card.Header>

      <Card.Body className="p-3">
        {/* Description pédagogique */}
        <p className="text-muted mb-3" style={{ fontSize: '0.83rem', lineHeight: 1.55 }}>
          {data.description}
        </p>

        <Row className="g-3">
          {/* A) Résultat réel */}
          <Col xs={12} md={5}>
            <div
              className="rounded p-3 h-100"
              style={{ background: 'var(--bs-secondary-bg, #f8f9fa)', fontSize: '0.82rem' }}
            >
              <div className="fw-semibold mb-2" style={{ fontSize: '0.85rem' }}>
                🏛️ {t('scenarios.realResult')}
              </div>
              <div className="text-muted mb-1">
                {t('scenarios.method')} : <strong>{data.real_result.method}</strong>
              </div>
              <div className="mb-2">
                {t('scenarios.winner')} :{' '}
                <Badge bg="primary" style={{ fontSize: '0.78rem' }}>
                  {data.real_result.winner}
                </Badge>
              </div>
              <div className="text-muted" style={{ fontSize: '0.78rem', lineHeight: 1.4 }}>
                {data.real_result.context}
              </div>

              {/* Vote shares if available */}
              {data.vote_shares && (
                <div className="mt-3">
                  <div className="text-muted mb-1" style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                    {t('scenarios.voteShares')}
                  </div>
                  {Object.entries(data.vote_shares)
                    .sort(([, a], [, b]) => b - a)
                    .slice(0, 5)
                    .map(([name, pct]) => (
                      <div key={name} className="d-flex align-items-center gap-2 mb-1">
                        <span style={{ minWidth: 100, fontSize: '0.75rem' }}>{name}</span>
                        <div
                          className="rounded"
                          style={{
                            width:      `${Math.round(pct * 2)}px`,
                            height:     8,
                            background: 'var(--bs-primary)',
                            opacity:    0.6,
                            minWidth:   4,
                          }}
                        />
                        <span style={{ fontSize: '0.75rem', color: 'var(--bs-secondary-color)' }}>
                          {pct.toFixed(1)}%
                        </span>
                      </div>
                    ))}
                </div>
              )}
            </div>
          </Col>

          {/* B) Comparaison simulation vs réel */}
          {result && (
            <Col xs={12} md={7}>
              <div className="fw-semibold mb-2" style={{ fontSize: '0.85rem' }}>
                ⚖️ {t('scenarios.simulatedComparison')}
              </div>
              <Table bordered size="sm" style={{ fontSize: '0.78rem' }}>
                <thead className="table-light">
                  <tr>
                    <th>{t('common.method')}</th>
                    <th className="text-center">{t('scenarios.simulatedWinner')}</th>
                    <th className="text-center">{t('scenarios.vsReal')}</th>
                  </tr>
                </thead>
                <tbody>
                  {CORE_METHODS.map((method) => {
                    const md      = result.methods[method];
                    const simWin  = md?.winner ?? '—';
                    const sameAs  = simWin === data.real_result.winner;
                    return (
                      <tr key={method}>
                        <td className="fw-semibold">{method}</td>
                        <td className="text-center">
                          <Badge
                            style={{ fontSize: '0.72rem', background: sameAs ? '#007A33' : 'var(--bs-secondary)' }}
                          >
                            {simWin}
                          </Badge>
                        </td>
                        <td className="text-center">
                          {data.real_result.winner === '—'
                            ? <span className="text-muted">—</span>
                            : sameAs
                              ? <span style={{ color: '#007A33' }}>✓</span>
                              : <span style={{ color: '#B71C1C' }}>✗</span>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </Table>

              {/* Condorcet info */}
              {result.condorcet_winner ? (
                <div style={{ fontSize: '0.78rem', color: '#007A33' }}>
                  ✓ {t('scenarios.condorcetExists', { winner: result.condorcet_winner })}
                </div>
              ) : (
                <div style={{ fontSize: '0.78rem', color: '#B71C1C' }}>
                  ✗ {t('scenarios.condorcetNone')}
                </div>
              )}
            </Col>
          )}
        </Row>

        {/* C) Message pédagogique contextuel */}
        {result && (
          <Alert variant={variant} className="mt-3 py-2 mb-0" style={{ fontSize: '0.8rem' }}>
            {t(`scenarios.pedagogical_${scenarioMeta.id}`, {
              defaultValue: data.description,
            })}
          </Alert>
        )}
      </Card.Body>
    </Card>
  );
};

export default HistoricalReferencePanel;
