/**
 * PartyDynamicsPage — standalone page for the party dynamics simulator.
 * Accessible at /party-dynamics.
 */
import React from 'react';
import { Container } from 'react-bootstrap';
import { useTranslation } from 'react-i18next';
import { useMetaTags } from '../hooks/useMetaTags';
import PartyDynamicsPanel from '../components/shared/PartyDynamicsPanel';

const PartyDynamicsPage: React.FC = () => {
  const { t } = useTranslation();
  useMetaTags({
    title: 'Dynamique des partis — Vote Lab',
    description: "Simulez la Loi de Duverger : comment le scrutin uninominal converge vers le bipartisme et la proportionnelle maintient le multipartisme.",
  });

  return (
    <Container className="py-4" style={{ maxWidth: 960 }}>
      <h2 className="fw-bold mb-1">📊 {t('partyDyn.pageTitle')}</h2>
      <p className="text-muted mb-4" style={{ fontSize: '0.9rem' }}>
        {t('partyDyn.pageSubtitle')}
      </p>
      <PartyDynamicsPanel />
    </Container>
  );
};

export default PartyDynamicsPage;
