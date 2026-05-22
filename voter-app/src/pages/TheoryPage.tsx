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
import ApportionmentPanel from '../components/shared/ApportionmentPanel';
import AgendaManipulationPanel from '../components/shared/AgendaManipulationPanel';
import MajorityTyrannyPanel from '../components/shared/MajorityTyrannyPanel';
import PowerIndicesPanel from '../components/shared/PowerIndicesPanel';
import DemocraticBackslidingPanel from '../components/shared/DemocraticBackslidingPanel';
import IntergenerationalPanel from '../components/shared/IntergenerationalPanel';
import EpistocracyPanel from '../components/shared/EpistocracyPanel';
import IdentityVotingPanel from '../components/shared/IdentityVotingPanel';
import AssumptionTesterPanel from '../components/shared/AssumptionTesterPanel';
import CollectiveWillPanel from '../components/shared/CollectiveWillPanel';

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
      {/* ── Identity Voting ── */}
      <Card className="mb-4" style={{ borderColor: '#6610f2' }}>
        <Card.Header className="fw-bold" style={{ color: '#6610f2' }}>
          🏳 {t('identity.cardTitle')}
        </Card.Header>
        <Card.Body>
          <p style={{ fontSize: '0.85rem' }}>{t('identity.cardDesc')}</p>
          <IdentityVotingPanel />
        </Card.Body>
      </Card>

      {/* ── Epistocracy ── */}
      <Card className="mb-4 border-warning">
        <Card.Header className="fw-bold" style={{ color: '#856404' }}>
          🎓 {t('episto.cardTitle')}
        </Card.Header>
        <Card.Body>
          <p style={{ fontSize: '0.85rem' }}>{t('episto.cardDesc')}</p>
          <EpistocracyPanel />
        </Card.Body>
      </Card>

      {/* ── Intergenerational Justice ── */}
      <Card className="mb-4 border-primary">
        <Card.Header className="fw-bold text-primary">🌱 {t('intergen.cardTitle')}</Card.Header>
        <Card.Body>
          <p style={{ fontSize: '0.85rem' }}>{t('intergen.cardDesc')}</p>
          <IntergenerationalPanel />
        </Card.Body>
      </Card>

      {/* ── Democratic Backsliding ── */}
      <Card className="mb-4" style={{ borderColor: '#842029' }}>
        <Card.Header className="fw-bold" style={{ color: '#842029' }}>
          🏚 {t('backsliding.cardTitle')}
        </Card.Header>
        <Card.Body>
          <p style={{ fontSize: '0.85rem' }}>{t('backsliding.cardDesc')}</p>
          <DemocraticBackslidingPanel />
        </Card.Body>
      </Card>

      {/* ── Power Indices ── */}
      <Card className="mb-4 border-success">
        <Card.Header className="fw-bold text-success">⚡ {t('power.cardTitle')}</Card.Header>
        <Card.Body>
          <p style={{ fontSize: '0.85rem' }}>{t('power.cardDesc')}</p>
          <PowerIndicesPanel />
        </Card.Body>
      </Card>

      {/* ── Majority Tyranny ── */}
      <Card className="mb-4" style={{ borderColor: '#6f1d1b' }}>
        <Card.Header className="fw-bold" style={{ color: '#6f1d1b' }}>
          👑 {t('tyranny.cardTitle')}
        </Card.Header>
        <Card.Body>
          <p style={{ fontSize: '0.85rem' }}>{t('tyranny.cardDesc')}</p>
          <MajorityTyrannyPanel />
        </Card.Body>
      </Card>

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

      {/* ── Apportionment ── */}
      <Card className="mb-4 border-secondary">
        <Card.Header className="fw-bold">📊 {t('appor.cardTitle')}</Card.Header>
        <Card.Body>
          <p style={{ fontSize: '0.85rem' }}>{t('appor.cardDesc')}</p>
          <ApportionmentPanel />
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

      {/* ── Agenda Manipulation ── */}
      <Card className="mb-4 border-dark">
        <Card.Header className="fw-bold">🗓 {t('agenda.cardTitle')}</Card.Header>
        <Card.Body>
          <p style={{ fontSize: '0.85rem' }}>{t('agenda.cardDesc')}</p>
          <AgendaManipulationPanel />
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

      {/* ── Collective Will ── */}
      <Card className="mb-4" style={{ borderColor: '#495057' }}>
        <Card.Header className="fw-bold" style={{ color: '#495057' }}>
          🌊 {t('will.cardTitle')}
        </Card.Header>
        <Card.Body>
          <p style={{ fontSize: '0.85rem' }}>{t('will.cardDesc')}</p>
          <CollectiveWillPanel />
        </Card.Body>
      </Card>

      {/* ── Assumption Tester ── */}
      <Card className="mb-4 border-secondary">
        <Card.Header className="fw-bold text-secondary">
          🔬 {t('assumptions.cardTitle')}
        </Card.Header>
        <Card.Body>
          <p style={{ fontSize: '0.85rem' }}>{t('assumptions.cardDesc')}</p>
          <AssumptionTesterPanel />
        </Card.Body>
      </Card>

      <ArrowExplorer />
    </Container>
  );
};

export default TheoryPage;
