import React from 'react';
import { useTranslation } from 'react-i18next';
import { completedYears, simulatedDate } from '../../lib/polity/ticks';
import { usePolityCtx } from './PolityController';

const Fact: React.FC<{ label: string; value: string; testId: string }> = ({
  label,
  value,
  testId,
}) => (
  <div className="flex flex-col">
    <dt className="font-mono text-[0.62rem] uppercase tracking-[0.16em] text-muted-foreground">
      {label}
    </dt>
    <dd className="text-sm font-medium tabular-nums" data-testid={testId}>
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
  const engine =
    run?.engine === 'llm'
      ? t('runFacts.engineLlm')
      : run?.engine === 'deterministic'
        ? t('runFacts.engineDeterministic')
        : '—';

  return (
    <dl
      data-testid="polity-run-facts"
      className="flex flex-wrap gap-x-8 gap-y-2 rounded-md border border-border bg-muted/30 px-4 py-3"
    >
      <Fact
        testId="polity-fact-population"
        label={t('runFacts.population')}
        value={t('runFacts.populationValue', { count: overview.population })}
      />
      <Fact
        testId="polity-fact-duration"
        label={t('runFacts.duration')}
        value={t('runFacts.durationValue', {
          years: completedYears(overview.last_tick, overview.ticks_per_year),
          ticks: overview.last_tick + 1,
        })}
      />
      <Fact testId="polity-fact-engine" label={t('runFacts.engine')} value={engine} />
      <Fact testId="polity-fact-votes" label={t('runFacts.votes')} value={votes} />
      <Fact
        testId="polity-fact-tick"
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
