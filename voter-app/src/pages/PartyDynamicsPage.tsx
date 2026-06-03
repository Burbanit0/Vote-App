/**
 * PartyDynamicsPage — standalone page for the party dynamics simulator.
 * Accessible at /party-dynamics.
 */
import React from 'react';
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
    <div data-style="tailwind" className="mx-auto w-full max-w-[960px] px-3 py-6">
      <h2 className="mb-1 text-[1.5rem] font-bold">📊 {t('partyDyn.pageTitle')}</h2>
      <p className="mb-6 text-[0.9rem] text-muted-foreground">
        {t('partyDyn.pageSubtitle')}
      </p>
      <PartyDynamicsPanel />
    </div>
  );
};

export default PartyDynamicsPage;
