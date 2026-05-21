/**
 * TheoryPage — Interactive exploration of voting theory:
 * Arrow's Impossibility Theorem with per-method axiom violations.
 */
import React from 'react';
import { Container, Card } from 'react-bootstrap';
import { useTranslation } from 'react-i18next';
import { useMetaTags } from '../hooks/useMetaTags';
import ArrowExplorer from '../components/Simulation/ArrowExplorer';
import PlottChaosPanel from '../components/Simulation/PlottChaosPanel';
import JudgmentAggregationPanel from '../components/shared/JudgmentAggregationPanel';
import SenParadoxPanel from '../components/shared/SenParadoxPanel';

const TheoryPage: React.FC = () => {
  const { t } = useTranslation();
  useMetaTags({
    title: 'Théorie du vote — Vote Lab',
    description: "Explorez le théorème d'impossibilité d'Arrow : aucune méthode de vote ne peut satisfaire simultanément tous les critères de rationalité collective.",
  });

  return (
    <Container className="py-4" style={{ maxWidth: 1000 }}>
      <h2 className="fw-bold mb-1">🏛 {t('arrow.pageTitle')}</h2>
      <p className="text-muted mb-4" style={{ fontSize: '0.9rem' }}>
        {t('arrow.pageSubtitle')}
      </p>

      {/* Arrow context */}
      {/* ── Plott Chaos ── */}
      <Card className="mb-4 border-danger">
        <Card.Header className="fw-bold text-danger">🌀 {t('plott.cardTitle')}</Card.Header>
        <Card.Body>
          <p style={{ fontSize: '0.85rem' }}>{t('plott.cardDesc')}</p>
          <PlottChaosPanel />
        </Card.Body>
      </Card>

      <Card className="mb-4 border-primary">
        <Card.Body>
          <h6 className="fw-bold">{t('arrow.contextTitle')}</h6>
          <p style={{ fontSize: '0.85rem' }}>{t('arrow.contextDesc')}</p>
          <div className="d-flex flex-wrap gap-2">
            {['iia', 'pareto', 'transitivity', 'non_dictatorship'].map((ax) => (
              <span key={ax} className="border rounded px-2 py-1" style={{ fontSize: '0.75rem' }}>
                <strong>{t(`arrow.${ax}Short`)}</strong>: {t(`arrow.${ax}Def`)}
              </span>
            ))}
          </div>
        </Card.Body>
      </Card>

      {/* ── Sen Paradox ── */}
      <Card className="mb-4 border-warning">
        <Card.Header className="fw-bold" style={{ color: '#856404' }}>⚖️ {t('sen.cardTitle')}</Card.Header>
        <Card.Body>
          <p style={{ fontSize: '0.85rem' }}>{t('sen.cardDesc')}</p>
          <SenParadoxPanel />
        </Card.Body>
      </Card>

      {/* ── Judgment Aggregation ── */}
      <Card className="mb-4 border-info">
        <Card.Header className="fw-bold text-info">⚖️ {t('judg.cardTitle')}</Card.Header>
        <Card.Body>
          <p style={{ fontSize: '0.85rem' }}>{t('judg.cardDesc')}</p>
          <JudgmentAggregationPanel />
        </Card.Body>
      </Card>

      <ArrowExplorer />
    </Container>
  );
};

export default TheoryPage;
