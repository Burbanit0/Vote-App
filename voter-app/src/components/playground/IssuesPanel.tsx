import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { ElectionConfig, PlaygroundState } from '../../stores/useElectionStore';
import {
  runIssueVoting,
  runOstrogorskiDemo,
  type IssueVotingResult,
} from '../../services/issuesApi';

// IssuesPanel (frontier FB-2) — the bundling problem. Voters elect a PACKAGE
// (closest party platform), yet each issue also has its own referendum
// majority. The matrix puts the two side by side and highlights divergences;
// the constructed demo shows the full Ostrogorski paradox (the winner opposed
// by the majority on EVERY issue).

const IssuesPanel: React.FC<{ config: ElectionConfig; playground?: PlaygroundState }> = ({
  config,
  playground,
}) => {
  const { t } = useTranslation('playground');
  const [numIssues, setNumIssues] = useState(4);
  const [data, setData] = useState<IssueVotingResult | null>(null);
  const [loading, setLoading] = useState(false);

  const run = async (demo: boolean) => {
    setLoading(true);
    try {
      setData(
        demo ? await runOstrogorskiDemo() : await runIssueVoting(config, numIssues, playground)
      );
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const mark = (v: number): string => (v > 0 ? t('issues.yes') : t('issues.no'));

  return (
    <div
      data-testid="issues-panel"
      className="flex flex-col gap-2 rounded-md border border-border p-3"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {t('issues.title')}
        </span>
        <div className="flex items-center gap-2 text-xs">
          <label className="flex items-center gap-1 text-muted-foreground">
            {t('issues.issuesLabel')}
            <input
              data-testid="issues-count"
              type="range"
              min={2}
              max={7}
              step={1}
              value={numIssues}
              onChange={(e) => setNumIssues(Number(e.target.value))}
            />
            {numIssues}
          </label>
          <Button
            data-testid="issues-run"
            variant="outline"
            size="sm"
            onClick={() => run(false)}
            disabled={loading}
          >
            {loading ? '…' : t('issues.analyze')}
          </Button>
          <Button
            data-testid="issues-demo"
            variant="outline"
            size="sm"
            onClick={() => run(true)}
            title={t('issues.demoTitle')}
          >
            {t('issues.demo')}
          </Button>
        </div>
      </div>
      <p className="text-[0.68rem] text-muted-foreground/70">{t('issues.intro')}</p>

      {data && (
        <>
          {/* Headline */}
          <p
            data-testid="issues-headline"
            className={cn(
              'text-sm',
              data.ostrogorski_paradox
                ? 'font-semibold text-amber-600 dark:text-amber-400'
                : 'text-muted-foreground'
            )}
          >
            {data.ostrogorski_paradox ? t('issues.paradoxPrefix') : ''}
            <strong>{data.bundled_winner}</strong>{' '}
            {t('issues.divergeOn', {
              count: data.divergent_count,
              num: data.num_issues,
            })}
          </p>

          {/* Issue matrix: referendum majority vs elected platform */}
          <div data-testid="issues-matrix" className="flex flex-col gap-1">
            <div className="flex items-center gap-2 text-[0.65rem] uppercase tracking-wide text-muted-foreground">
              <span className="w-20 shrink-0" />
              <span className="flex-1">{t('issues.yesShare')}</span>
              <span className="w-24 text-center">{t('issues.majorityCol')}</span>
              <span className="w-24 text-center">{t('issues.platformCol')}</span>
            </div>
            {data.issues.map((issue) => (
              <div
                key={issue.label}
                data-testid={`issue-row-${issue.label}`}
                className={cn(
                  'flex items-center gap-2 rounded px-1 py-0.5 text-xs',
                  issue.divergent && 'bg-amber-500/10'
                )}
              >
                <span className="w-20 shrink-0 text-muted-foreground">{issue.label}</span>
                <div className="relative h-2.5 flex-1 overflow-hidden rounded bg-muted/50">
                  <div
                    className="h-full bg-primary/60"
                    style={{ width: `${issue.yes_share * 100}%`, transition: 'width 300ms ease' }}
                  />
                  <div className="absolute inset-y-0 left-1/2 w-px bg-foreground/40" />
                </div>
                <span className="w-24 text-center tabular-nums">{mark(issue.majority)}</span>
                <span
                  className={cn(
                    'w-24 text-center tabular-nums',
                    issue.divergent && 'font-semibold text-amber-600 dark:text-amber-400'
                  )}
                >
                  {mark(issue.winner_plank)}
                  {issue.divergent ? ' ✕' : ''}
                </span>
              </div>
            ))}
          </div>

          {/* Parties + platforms */}
          <div
            data-testid="issues-parties"
            className="flex flex-wrap gap-2 text-[0.7rem] text-muted-foreground"
          >
            {data.parties.map((p) => (
              <span
                key={p.name}
                className={cn(
                  'rounded border border-border px-1.5 py-0.5',
                  p.name === data.bundled_winner && 'border-primary font-semibold'
                )}
              >
                {p.name} {(p.vote_share * 100).toFixed(0)} % ·{' '}
                {p.platform.map((v) => (v > 0 ? 'O' : 'N')).join('')}
              </span>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default IssuesPanel;
