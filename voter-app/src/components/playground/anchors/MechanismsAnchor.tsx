import React from 'react';
import { useTranslation } from 'react-i18next';
import Leaf from './Leaf';
import { lazyWithPreload } from '../../../lib/lazyWithPreload';
import { useElection } from '../../../stores/useElectionStore';

// MechanismsAnchor — the "Mécanismes alternatifs" Lab family, re-homed in the
// leader canvas: these are other ways to designate a single outcome (jury,
// sortition, delegation, deliberation…) — the leader question by another route.
// Each reads the shared electorate; lazy + Collapsible-gated.
//
// Perf (Phase 0): panels use lazyWithPreload + Leaf `prefetch`, so hovering a
// toggle warms its chunk before the click.

const JuryTheoremPanel = lazyWithPreload(() => import('../../shared/JuryTheoremPanel'));
const NOTAPanel = lazyWithPreload(() => import('../../shared/NOTAPanel'));
const LiquidDemocracyPanel = lazyWithPreload(() => import('../../shared/LiquidDemocracyPanel'));
const SortitionPanel = lazyWithPreload(() => import('../../shared/SortitionPanel'));
const DeliberationPanel = lazyWithPreload(() => import('../../shared/DeliberationPanel'));
const ConvictionVotingPanel = lazyWithPreload(() => import('../../shared/ConvictionVotingPanel'));
const EpistocracyPanel = lazyWithPreload(() => import('../../shared/EpistocracyPanel'));
const IdentityVotingPanel = lazyWithPreload(() => import('../../shared/IdentityVotingPanel'));

const MechanismsAnchor: React.FC = () => {
  const { t } = useTranslation('playground');
  // Epistocracy + Identity read the shared electorate (labMode), like the Lab did.
  const { config } = useElection();
  const lab = {
    labMode: true as const,
    labCandidates: config.candidates,
    labNumVoters: config.num_voters,
    labSeed: config.seed,
  };
  return (
    <div className="flex flex-col gap-2">
      <p className="text-[0.7rem] text-muted-foreground/80">{t('anchorBody.mechanisms.intro')}</p>
      <Leaf
        title={t('anchorBody.mechanisms.jury')}
        testid="mech-jury"
        prefetch={JuryTheoremPanel.preload}
      >
        <JuryTheoremPanel />
      </Leaf>
      <Leaf title={t('anchorBody.mechanisms.nota')} testid="mech-nota" prefetch={NOTAPanel.preload}>
        <NOTAPanel />
      </Leaf>
      <Leaf
        title={t('anchorBody.mechanisms.liquid')}
        testid="mech-liquid"
        prefetch={LiquidDemocracyPanel.preload}
      >
        <LiquidDemocracyPanel />
      </Leaf>
      <Leaf
        title={t('anchorBody.mechanisms.sortition')}
        testid="mech-sortition"
        prefetch={SortitionPanel.preload}
      >
        <SortitionPanel />
      </Leaf>
      <Leaf
        title={t('anchorBody.mechanisms.deliberation')}
        testid="mech-deliberation"
        prefetch={DeliberationPanel.preload}
      >
        <DeliberationPanel />
      </Leaf>
      <Leaf
        title={t('anchorBody.mechanisms.conviction')}
        testid="mech-conviction"
        prefetch={ConvictionVotingPanel.preload}
      >
        <ConvictionVotingPanel />
      </Leaf>
      <Leaf
        title={t('anchorBody.mechanisms.epistocracy')}
        testid="mech-epistocracy"
        prefetch={EpistocracyPanel.preload}
      >
        <EpistocracyPanel {...lab} />
      </Leaf>
      <Leaf
        title={t('anchorBody.mechanisms.identity')}
        testid="mech-identity"
        prefetch={IdentityVotingPanel.preload}
      >
        <IdentityVotingPanel {...lab} />
      </Leaf>
    </div>
  );
};

export default MechanismsAnchor;
