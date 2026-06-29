import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { usePlaygroundCtx } from '../PlaygroundController';
import Scorecard from '../Scorecard';
import MethodInfo from '../MethodInfo';
import RealElectionPanel from '../RealElectionPanel';
import FullResultsModule from '../FullResultsModule';
import { useVotingLabels } from '../../../hooks/useVotingLabels';

// Moment ⑤ Bilan — the verdict. The real-ballot proof comes first (the thesis at
// its strongest: same ballots, different winners, no assumptions), then the
// confidence-banded scorecard for the current method, then the full results
// table across every method. Sensitivity-to-values (Lijphart dial + frontier) and
// deep analysis/theory live in /laboratoire.
const BilanMoment: React.FC = () => {
  const { t } = useTranslation('playground');
  const { ruleLabels, structureLabels } = useVotingLabels();
  const { mode, leaderRule, assembly, result, parlSc, currentAxes } = usePlaygroundCtx();

  return (
    <div className="flex flex-col gap-4">
      {/* ── Épreuve du réel — the climax, promoted to the top ── */}
      <div className="flex flex-col gap-2">
        <p className="text-sm font-semibold">{t('realElection.title')}</p>
        <p className="text-xs text-muted-foreground">{t('realElection.sub')}</p>
        <RealElectionPanel />
      </div>

      <hr className="border-border" />

      <div className="flex items-center gap-1 text-sm font-medium">
        <span className="text-muted-foreground">{t('bilan.evaluatedFor')}</span>
        <span>
          {mode === 'leader' ? ruleLabels[leaderRule] : structureLabels[assembly.structure]}
        </span>
        {mode === 'leader' ? (
          <MethodInfo
            method={leaderRule}
            context={{ condorcetExists: result?.condorcet_winner != null }}
            placement="bottom"
          />
        ) : (
          <MethodInfo method={assembly.structure} placement="bottom" />
        )}
      </div>

      <Scorecard
        axes={currentAxes}
        bandNote={t('bilan.bandNote', {
          count: mode === 'leader' ? 20 : (parlSc?.replications ?? 24),
        })}
      />

      <hr className="border-border" />

      <FullResultsModule />

      <hr className="border-border" />

      <div className="text-center">
        <p className="text-xs text-muted-foreground">{t('bilan.labCtaNote')}</p>
        <Link
          to="/laboratoire"
          data-testid="bilan-lab-link"
          className="mt-1 inline-block text-sm text-primary hover:underline"
        >
          {t('bilan.labCta')}
        </Link>
      </div>
    </div>
  );
};

export default BilanMoment;
