/**
 * SortitionPage — standalone page for the sortition (tirage au sort) simulator.
 * Accessible at /sortition.
 */
import React from 'react';
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
    <div data-style="tailwind" className="mx-auto w-full max-w-[960px] px-3 py-6">
      <h2 className="mb-1 text-[1.5rem] font-bold">🎲 {t('sortition.pageTitle')}</h2>
      <p className="mb-6 text-[0.9rem] text-muted-foreground">
        {t('sortition.pageSubtitle')}
      </p>
      <ElectionProvider>
        <SortitionPanel />
      </ElectionProvider>
    </div>
  );
};

export default SortitionPage;
