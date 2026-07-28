import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Play } from 'lucide-react';
import { usePlaygroundCtx } from '../playground/PlaygroundController';
import MethodReplayModal from '../playground/MethodReplayModal';
import { useVotingLabels } from '../../hooks/useVotingLabels';
import { LEADER_RULES, EXTRA_RULES } from '../../lib/scorecard';
import { ruleWinner, type Rule } from '../../lib/playgroundVoting';
import { getMethodInfo, methodAnalogy, type Lang } from '../../lib/methodInfo';
import { CANDIDATE_COLORS_LIGHT } from '../../constants/chartColors';

// MethodGallery — one browsable card per voting method. Common methods first
// (the ones a newcomer recognises), then the Tier B "explained, not compared"
// methods. Each card shows the plain-language gist, the everyday analogy
// ("comme dans la vie") when one exists, the live winner on the current
// electorate, and opens the step-by-step replay so anyone can see how it works.
const MethodGallery: React.FC = () => {
  const { t, i18n } = useTranslation('playground');
  const lang: Lang = i18n.language?.startsWith('en') ? 'en' : 'fr';
  const analogyLabel = lang === 'en' ? 'Like real life:' : 'Comme dans la vie :';
  const { ruleLabels } = useVotingLabels();
  const { votingVoters, leaderCandidates } = usePlaygroundCtx();
  const [replayRule, setReplayRule] = useState<Rule | null>(null);

  const candColor = (i: number) => CANDIDATE_COLORS_LIGHT[i % CANDIDATE_COLORS_LIGHT.length];

  return (
    <section className="flex flex-col gap-3">
      <div>
        <p className="font-mono text-[0.62rem] uppercase tracking-[0.2em] text-primary">
          {t('gallery.eyebrow')}
        </p>
        <h2 className="font-display text-lg font-bold tracking-tight">{t('gallery.title')}</h2>
        <p className="mt-0.5 max-w-2xl text-sm text-muted-foreground">{t('gallery.intro')}</p>
      </div>

      <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
        {[...LEADER_RULES, ...EXTRA_RULES].map((rule) => {
          const info = getMethodInfo(rule)?.[lang];
          const analogy = methodAnalogy(rule, lang);
          const winIdx =
            votingVoters.length && leaderCandidates.length
              ? ruleWinner(votingVoters, leaderCandidates, rule)
              : -1;
          const winner = winIdx >= 0 ? leaderCandidates[winIdx] : null;
          return (
            <div
              key={rule}
              data-testid={`gallery-${rule}`}
              className="flex flex-col gap-2 rounded-lg border border-border bg-card p-3"
            >
              <div className="flex items-start justify-between gap-2">
                <h3 className="text-sm font-semibold leading-tight">{ruleLabels[rule]}</h3>
                {winner && (
                  <span
                    className="shrink-0 rounded border px-1.5 py-0.5 font-mono text-[0.62rem] font-semibold"
                    style={{
                      color: candColor(winIdx),
                      borderColor: `${candColor(winIdx)}55`,
                      background: `${candColor(winIdx)}12`,
                    }}
                    title={t('gallery.liveWinner')}
                  >
                    {winner.name}
                  </span>
                )}
              </div>
              {info && (
                <p className="text-xs leading-relaxed text-muted-foreground">{info.summary}</p>
              )}
              {analogy && (
                <p className="text-xs leading-relaxed text-muted-foreground">
                  <span className="font-semibold text-primary">{analogyLabel} </span>
                  {analogy}
                </p>
              )}
              <button
                type="button"
                data-testid={`gallery-replay-${rule}`}
                onClick={() => setReplayRule(rule)}
                className="mt-auto flex items-center gap-1 self-start rounded-md border border-primary px-2 py-1 text-xs text-primary hover:bg-primary/10"
              >
                <Play className="h-3 w-3" /> {t('gallery.watch')}
              </button>
            </div>
          );
        })}
      </div>

      {replayRule && (
        <MethodReplayModal
          show
          onHide={() => setReplayRule(null)}
          voters={votingVoters}
          candidates={leaderCandidates}
          initialRule={replayRule}
        />
      )}
    </section>
  );
};

export default MethodGallery;
