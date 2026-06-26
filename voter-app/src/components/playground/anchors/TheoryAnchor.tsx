import React from 'react';
import { useTranslation } from 'react-i18next';
import Leaf from './Leaf';
import { lazyWithPreload } from '../../../lib/lazyWithPreload';

// TheoryAnchor — the social-choice paradoxes & democratic-theory panels that
// used to live only on TheoryPage, re-homed into the playground so the single
// surface covers the whole inventory. All panels are self-contained (no props);
// lazy + Collapsible-gated, so nothing computes until a leaf is opened.
//
// Perf (Phase 0): panels use lazyWithPreload + Leaf `prefetch`, so hovering a
// toggle warms its chunk before the click.

const SenParadoxPanel = lazyWithPreload(() => import('../../shared/SenParadoxPanel'));
const JudgmentAggregationPanel = lazyWithPreload(
  () => import('../../shared/JudgmentAggregationPanel')
);
const AgendaManipulationPanel = lazyWithPreload(
  () => import('../../shared/AgendaManipulationPanel')
);
const MajorityTyrannyPanel = lazyWithPreload(() => import('../../shared/MajorityTyrannyPanel'));
const ApportionmentPanel = lazyWithPreload(() => import('../../shared/ApportionmentPanel'));
const PowerIndicesPanel = lazyWithPreload(() => import('../../shared/PowerIndicesPanel'));
const DemocraticBackslidingPanel = lazyWithPreload(
  () => import('../../shared/DemocraticBackslidingPanel')
);
const IntergenerationalPanel = lazyWithPreload(() => import('../../shared/IntergenerationalPanel'));
const PolisPanel = lazyWithPreload(() => import('../../shared/PolisPanel'));

const TheoryAnchor: React.FC = () => {
  const { t } = useTranslation('playground');
  return (
    <div className="flex flex-col gap-2">
      <p className="text-[0.7rem] text-muted-foreground/80">{t('anchorBody.theory.intro')}</p>
      <Leaf title={t('anchorBody.theory.sen')} testid="thy-sen" prefetch={SenParadoxPanel.preload}>
        <SenParadoxPanel />
      </Leaf>
      <Leaf
        title={t('anchorBody.theory.judgment')}
        testid="thy-judgment"
        prefetch={JudgmentAggregationPanel.preload}
      >
        <JudgmentAggregationPanel />
      </Leaf>
      <Leaf
        title={t('anchorBody.theory.agenda')}
        testid="thy-agenda"
        prefetch={AgendaManipulationPanel.preload}
      >
        <AgendaManipulationPanel />
      </Leaf>
      <Leaf
        title={t('anchorBody.theory.tyranny')}
        testid="thy-tyranny"
        prefetch={MajorityTyrannyPanel.preload}
      >
        <MajorityTyrannyPanel />
      </Leaf>
      <Leaf
        title={t('anchorBody.theory.apportionment')}
        testid="thy-apportionment"
        prefetch={ApportionmentPanel.preload}
      >
        <ApportionmentPanel />
      </Leaf>
      <Leaf
        title={t('anchorBody.theory.power')}
        testid="thy-power"
        prefetch={PowerIndicesPanel.preload}
      >
        <PowerIndicesPanel />
      </Leaf>
      <Leaf
        title={t('anchorBody.theory.backsliding')}
        testid="thy-backsliding"
        prefetch={DemocraticBackslidingPanel.preload}
      >
        <DemocraticBackslidingPanel />
      </Leaf>
      <Leaf
        title={t('anchorBody.theory.intergen')}
        testid="thy-intergen"
        prefetch={IntergenerationalPanel.preload}
      >
        <IntergenerationalPanel />
      </Leaf>
      <Leaf title={t('anchorBody.theory.polis')} testid="thy-polis" prefetch={PolisPanel.preload}>
        <PolisPanel />
      </Leaf>
    </div>
  );
};

export default TheoryAnchor;
