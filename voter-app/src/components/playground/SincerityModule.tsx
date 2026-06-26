import React from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { type NamedPt, type Pt, type Rule } from '../../lib/playgroundVoting';
import { useVotingLabels } from '../../hooks/useVotingLabels';
import {
  sincerityProbe,
  sincerityScan,
  type SincerityVerdict,
  type SincerityScan,
} from '../../lib/playgroundSincerity';

// SincerityModule — the project's central constraint made interactive: should YOU
// vote by conviction, or does the method tempt you to vote "utile"? You set your
// sincere position; a bloc of like-minded voters sizes your collective leverage;
// each rule is judged conviction-safe or strategy-tempting (with the lie it
// invites). Client-side, live, deterministic — complements the aggregate
// Gibbard–Satterthwaite rate of the strategic module.

// Keep the live probe snappy on big electorates: an evenly-strided sub-sample.
function subsample<T>(arr: T[], cap: number): T[] {
  if (arr.length <= cap) return arr;
  const step = arr.length / cap;
  const out: T[] = [];
  for (let i = 0; i < cap; i++) out.push(arr[Math.floor(i * step)]);
  return out;
}

const SincerityModule: React.FC<{
  voters: Pt[];
  candidates: NamedPt[];
  dims: number;
  /** Your sincere position — controlled so the marker is draggable on the map. */
  you: Pt;
  onYouChange: (p: Pt) => void;
}> = ({ voters, candidates, dims, you, onYouChange }) => {
  const { t } = useTranslation('playground');
  const { ruleLabels } = useVotingLabels();
  const typeLabel = (type: NonNullable<SincerityVerdict['temptation']>['type']): string =>
    type === 'compromise' ? t('sincerity.typeCompromise') : t('sincerity.typeBurying');
  const setYou = (updater: (p: Pt) => Pt) => onYouChange(updater(you));
  const [blocShare, setBlocShare] = React.useState(0.12);

  const others = React.useMemo(() => subsample(voters, 400), [voters]);
  const report = React.useMemo(
    () => sincerityProbe(you, blocShare, others, candidates),
    [you, blocShare, others, candidates]
  );

  const safe = report.verdicts.filter((v) => v.sincereIsBest);
  // Tempting methods, the most rewarding lie first (biggest betrayal incentive).
  const tempting = report.verdicts.filter((v) => !v.sincereIsBest).sort((a, b) => b.gain - a.gain);
  const label = (r: Rule) => ruleLabels[r] ?? r;

  // Electorate sweep (on-demand): per-method temptation rate over many voters.
  const [scan, setScan] = React.useState<SincerityScan | null>(null);
  // Drop a stale scan whenever the electorate or bloc changes.
  React.useEffect(() => setScan(null), [others, candidates, blocShare]);

  return (
    <div data-testid="sincerity-module" className="flex flex-col gap-3">
      <p className="text-[0.7rem] text-muted-foreground/80">{t('sincerity.intro')}</p>

      {/* Your sincere position */}
      <div className="flex flex-col gap-1.5">
        <label className="flex items-center gap-2 text-xs">
          <span className="w-40 shrink-0 text-muted-foreground">
            {t('sincerity.posEcon', { val: you.x.toFixed(2) })}
          </span>
          <input
            data-testid="sincerity-you-x"
            type="range"
            className="flex-1"
            min={-1}
            max={1}
            step={0.05}
            value={you.x}
            onChange={(e) => setYou((p) => ({ ...p, x: Number(e.target.value) }))}
          />
        </label>
        {dims >= 2 && (
          <label className="flex items-center gap-2 text-xs">
            <span className="w-40 shrink-0 text-muted-foreground">
              {t('sincerity.posSocial', { val: you.y.toFixed(2) })}
            </span>
            <input
              data-testid="sincerity-you-y"
              type="range"
              className="flex-1"
              min={-1}
              max={1}
              step={0.05}
              value={you.y}
              onChange={(e) => setYou((p) => ({ ...p, y: Number(e.target.value) }))}
            />
          </label>
        )}
        <p className="text-[0.7rem] text-muted-foreground">
          {t('sincerity.sincereOrder')} <strong>{report.ranking.join(' ＞ ')}</strong>
        </p>
        <p className="text-[0.65rem] text-muted-foreground/70">
          {t('sincerity.tip')} <strong>{t('sincerity.tipMarker')}</strong> {t('sincerity.tipEnd')}
        </p>
      </div>

      {/* Conviction bloc size */}
      <label className="flex items-center gap-2 text-xs">
        <span className="w-40 shrink-0 text-muted-foreground" title={t('sincerity.blocTitle')}>
          {t('sincerity.blocLabel', { n: report.blocSize })}
        </span>
        <input
          data-testid="sincerity-bloc"
          type="range"
          className="flex-1"
          min={0.02}
          max={0.4}
          step={0.02}
          value={blocShare}
          onChange={(e) => setBlocShare(Number(e.target.value))}
        />
      </label>

      {/* Headline */}
      <p data-testid="sincerity-headline" className="text-sm">
        {t('sincerity.headlinePre')}{' '}
        <strong className="text-green-700 dark:text-green-400">{safe.length}</strong>
        {t('sincerity.headlineMid')}{' '}
        <strong className="text-amber-600 dark:text-amber-400">{tempting.length}</strong>{' '}
        {t('sincerity.headlineEnd')}
      </p>

      {/* Strategy-tempting methods */}
      {tempting.length > 0 && (
        <div data-testid="sincerity-tempting" className="flex flex-col gap-1">
          <p className="text-[0.65rem] font-semibold uppercase tracking-wide text-amber-600 dark:text-amber-400">
            {t('sincerity.temptingHead')}
          </p>
          {tempting.map((v) => (
            <div key={v.rule} className="flex flex-col rounded bg-amber-500/10 px-2 py-1 text-xs">
              <span className="font-medium">{label(v.rule)}</span>
              <span className="text-[0.7rem] text-muted-foreground">
                {t('sincerity.temptSincere', { winner: v.sincereWinner })}{' '}
                <strong>{v.temptation!.voteFor}</strong> →{' '}
                <strong>{v.temptation!.newWinner}</strong>{' '}
                <em>({typeLabel(v.temptation!.type)})</em>
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Conviction-safe methods */}
      {safe.length > 0 && (
        <div data-testid="sincerity-safe" className="flex flex-col gap-1">
          <p className="text-[0.65rem] font-semibold uppercase tracking-wide text-green-700 dark:text-green-400">
            {t('sincerity.safeHead')}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {safe.map((v) => (
              <span
                key={v.rule}
                className="rounded border border-border px-1.5 py-0.5 text-[0.7rem] text-muted-foreground"
                title={t('sincerity.elects', { winner: v.sincereWinner })}
              >
                {label(v.rule)}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Electorate sweep — the synthesis: which methods minimise the vote utile? */}
      <div className="flex flex-col gap-1.5 border-t border-border pt-2">
        <Button
          data-testid="sincerity-scan-run"
          variant="outline"
          size="sm"
          className="self-start"
          onClick={() => setScan(sincerityScan(others, candidates, blocShare))}
          title={t('sincerity.scanTitle')}
        >
          {scan ? t('sincerity.scanRescan') : t('sincerity.scanRun')}
        </Button>

        {scan && scan.sampled > 0 && (
          <div data-testid="sincerity-scan" className="flex flex-col gap-1">
            <p className="text-xs">
              {t('sincerity.scanHeadPre', { sampled: scan.sampled })}{' '}
              <strong className="text-green-700 dark:text-green-400">
                {label(scan.rows[0].rule)}
              </strong>{' '}
              {t('sincerity.scanHeadEnd', { pct: Math.round(scan.rows[0].temptRate * 100) })}
            </p>
            {scan.rows.map(({ rule, temptRate }) => (
              <div key={rule} className="flex items-center gap-2 text-xs">
                <span className="w-40 shrink-0 truncate text-muted-foreground">{label(rule)}</span>
                <div className="h-2.5 flex-1 overflow-hidden rounded bg-muted/50">
                  <div
                    className={
                      'h-full rounded ' +
                      (temptRate <= 0.1
                        ? 'bg-green-600/70'
                        : temptRate <= 0.33
                          ? 'bg-amber-500/70'
                          : 'bg-red-500/70')
                    }
                    style={{ width: `${temptRate * 100}%`, transition: 'width 300ms ease' }}
                  />
                </div>
                <span className="w-10 text-right tabular-nums text-muted-foreground">
                  {Math.round(temptRate * 100)} %
                </span>
              </div>
            ))}
            <p className="text-[0.65rem] text-muted-foreground/70">{t('sincerity.scanFooter')}</p>
          </div>
        )}
      </div>

      <p className="text-[0.65rem] text-muted-foreground/70">{t('sincerity.note')}</p>
    </div>
  );
};

export default SincerityModule;
