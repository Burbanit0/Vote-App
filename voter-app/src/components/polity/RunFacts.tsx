import React from 'react';
import { useTranslation } from 'react-i18next';
import { unfinished } from '../../lib/polity/runs';
import { completedYears, simulatedDate } from '../../lib/polity/ticks';
import { usePolityCtx } from './PolityController';

/** One fact; with `changeKey`, its value rises in again each time the key changes. */
const Fact: React.FC<{ label: string; value: string; testId: string; changeKey?: number }> = ({
  label,
  value,
  testId,
  changeKey,
}) => (
  <div className="flex flex-col gap-1.5">
    <dt className="text-sm font-semibold text-muted-foreground">{label}</dt>
    <dd
      key={changeKey}
      className={`font-display text-[28px] leading-none font-extrabold tabular-nums ${changeKey === undefined ? '' : 'home-up'}`}
      data-testid={testId}
    >
      {value}
    </dd>
  </div>
);

/** The shown run at a glance, and where the player stands in it. */
const RunFacts: React.FC = () => {
  const { t } = useTranslation('polity');
  const { run, overview, tick, frame } = usePolityCtx();
  if (!overview) return null;

  const date = simulatedDate(tick, overview.ticks_per_year);
  const votes = {
    all: t('runFacts.votesAll'),
    audit_sample: t('runFacts.votesAuditSample'),
    none: t('runFacts.votesNone'),
  }[overview.vote_coverage];
  const engines: Record<string, string> = {
    llm: t('runFacts.engineLlm'),
    deterministic: t('runFacts.engineDeterministic'),
  };
  const engine = engines[run?.engine ?? ''] ?? '—';
  const progress = run ? unfinished(run) : null;

  return (
    <dl
      data-testid="polity-run-facts"
      className="flex flex-wrap gap-x-12 gap-y-5 border-y border-border py-5"
    >
      <Fact
        testId="polity-fact-population"
        label={t('runFacts.population')}
        value={t('runFacts.populationValue', { count: overview.population })}
      />
      <Fact
        testId="polity-fact-duration"
        label={t('runFacts.duration')}
        value={`${t('runFacts.years', {
          count: completedYears(overview.last_tick, overview.ticks_per_year),
        })} · ${t('runFacts.ticks', { count: overview.last_tick + 1 })}`}
      />
      {progress && (
        <Fact
          testId="polity-fact-status"
          label={t('runFacts.status')}
          value={t('runFacts.unfinished', progress)}
        />
      )}
      <Fact testId="polity-fact-engine" label={t('runFacts.engine')} value={engine} />
      <Fact testId="polity-fact-votes" label={t('runFacts.votes')} value={votes} />
      <Fact
        testId="polity-fact-tick"
        changeKey={tick}
        label={t('runFacts.tick')}
        value={
          t('runFacts.tickValue', { year: date.year, quarter: date.quarter }) +
          (frame?.partial ? ` — ${t('runFacts.partial')}` : '')
        }
      />
    </dl>
  );
};

export default RunFacts;
