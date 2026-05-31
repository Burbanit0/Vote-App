/**
 * SortitionPage — standalone page for the sortition (tirage au sort) simulator.
 * Accessible at /sortition.
 */
import React from 'react';
import { Container } from 'react-bootstrap';
import { useTranslation } from 'react-i18next';
import { useMetaTags } from '../hooks/useMetaTags';
import { ElectionProvider } from '../stores/useElectionStore';
import SortitionPanel from '../components/shared/SortitionPanel';

const SortitionPage: React.FC = () => {
  const { t } = useTranslation();
  useMetaTags({
    title: 'Tirage au sort — Vote Lab',
    description: 'Comparez assemblée élue, tirage au sort pur et tirage au sort stratifié sur les mêmes métriques démocratiques.',
  });

  return (
    <Container className="py-4" style={{ maxWidth: 960 }}>
      <h2 className="fw-bold mb-1">🎲 {t('sortition.pageTitle')}</h2>
      <p className="text-muted mb-4" style={{ fontSize: '0.9rem' }}>
        {t('sortition.pageSubtitle')}
      </p>
      <ElectionProvider>
        <SortitionPanel />
      </ElectionProvider>
    </Container>
  );
};

export default SortitionPage;
