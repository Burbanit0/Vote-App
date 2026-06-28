import React from 'react';
import { useTranslation } from 'react-i18next';
import Leaf from '../playground/anchors/Leaf';
import { lazyWithPreload } from '../../lib/lazyWithPreload';

// TemporalDynamicsAnchor (C3) — the temporal mechanisms + sequential behaviour
// migrated off the playground onto the "Campagne & dynamique" page. These are
// the family-C phenomena that unfold over TIME (repeated rounds / a sequence),
// the natural companions of the timeline above:
//   • adaptive voting   — tactics that adjust over successive elections
//   • historical replay  — re-running real past elections round by round
//   • primaries          — a two-stage sequential nomination
//   • information cascade — sequential herding as voters observe earlier votes
//   • electoral fatigue   — turnout/quality eroding over repeated ballots
// Each reads the shared electorate (state J0) via useElection(); all lazy +
// Collapsible-gated, so the page mounts nothing until a Leaf is opened.

const AdaptiveVotingPanel = lazyWithPreload(() => import('../shared/AdaptiveVotingPanel'));
const HistoricalReplay = lazyWithPreload(() => import('../shared/HistoricalReplay'));
const PrimarySimulator = lazyWithPreload(() => import('../shared/PrimarySimulator'));
const CascadePanel = lazyWithPreload(() => import('../shared/CascadePanel'));
const ElectoralFatiguePanel = lazyWithPreload(() => import('../shared/ElectoralFatiguePanel'));

const TemporalDynamicsAnchor: React.FC = () => {
  const { t } = useTranslation('playground');
  return (
    <div className="flex flex-col gap-2">
      <p className="text-[0.7rem] text-muted-foreground/80">{t('anchorBody.tdyn.intro')}</p>
      <Leaf
        title={t('anchorBody.tdyn.adaptive')}
        testid="tdyn-adaptive"
        prefetch={AdaptiveVotingPanel.preload}
      >
        <AdaptiveVotingPanel />
      </Leaf>
      <Leaf
        title={t('anchorBody.tdyn.replay')}
        testid="tdyn-replay"
        prefetch={HistoricalReplay.preload}
      >
        <HistoricalReplay />
      </Leaf>
      <Leaf
        title={t('anchorBody.tdyn.primary')}
        testid="tdyn-primary"
        prefetch={PrimarySimulator.preload}
      >
        <PrimarySimulator />
      </Leaf>
      <Leaf
        title={t('anchorBody.tdyn.cascade')}
        testid="tdyn-cascade"
        prefetch={CascadePanel.preload}
      >
        <CascadePanel />
      </Leaf>
      <Leaf
        title={t('anchorBody.tdyn.fatigue')}
        testid="tdyn-fatigue"
        prefetch={ElectoralFatiguePanel.preload}
      >
        <ElectoralFatiguePanel />
      </Leaf>
    </div>
  );
};

export default TemporalDynamicsAnchor;
