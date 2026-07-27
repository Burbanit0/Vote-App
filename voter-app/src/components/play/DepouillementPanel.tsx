import React from 'react';
import { useTranslation } from 'react-i18next';
import { Pause, Play, RotateCcw } from 'lucide-react';
import type { NamedPt } from '../../lib/playgroundVoting';
import type { VoteTrace } from '../../lib/voteTrace';
import { STEP_MS } from '../../hooks/useVoteReplay';
import { candidateColor } from '../../lib/palette';
import { track } from '../../lib/analytics';
import ReplayStage from '../playground/ReplayStage';

// DepouillementPanel — the count made transparent: the same engine replay used in
// the playground, but driven by the ballots actually cast on this page (already
// language-transformed). At rest it shows the final tally; press play, or scrub, to
// watch every ballot / round / duel that produced the winner.

const DepouillementPanel: React.FC<{ trace: VoteTrace; candidates: NamedPt[] }> = ({
  trace,
  candidates,
}) => {
  const { t } = useTranslation();
  const last = trace.frames.length - 1;
  const [frame, setFrame] = React.useState(last);
  const [playing, setPlaying] = React.useState(false);

  // A new method (or a new vote) rebuilds the trace — rest at its final tally.
  React.useEffect(() => {
    setFrame(trace.frames.length - 1);
    setPlaying(false);
  }, [trace]);

  React.useEffect(() => {
    if (!playing) return;
    if (frame >= last) {
      setPlaying(false);
      return;
    }
    const ms = (STEP_MS[trace.family] ?? 800) / 2;
    const id = window.setTimeout(() => setFrame((f) => f + 1), ms);
    return () => window.clearTimeout(id);
  }, [playing, frame, last, trace.family]);

  const replay = () => {
    setFrame(0);
    setPlaying(true);
    track('play_depouille_played', { rule: trace.rule });
  };

  return (
    <div
      data-testid="play-depouille"
      className="mt-3 rounded-xl border border-border bg-card p-4 sm:p-5"
    >
      <div className="flex flex-col gap-3">
        <ReplayStage trace={trace} frame={frame} candidates={candidates} colorOf={candidateColor} />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-border pt-3">
        <button
          type="button"
          data-testid="play-depouille-replay"
          onClick={replay}
          className="flex items-center gap-1.5 rounded-md border border-primary bg-primary px-3 py-1.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          {t('play.depouille.replay')}
        </button>
        <button
          type="button"
          aria-label={playing ? t('play.depouille.pause') : t('play.depouille.play')}
          onClick={() => (frame >= last ? replay() : setPlaying((p) => !p))}
          className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          {playing ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
          {playing ? t('play.depouille.pause') : t('play.depouille.play')}
        </button>

        {/* Scrub every step by hand — the fully manual, fully transparent path. */}
        <input
          type="range"
          aria-label={t('play.depouille.step', { n: frame + 1, total: trace.frames.length })}
          className="min-w-[8rem] flex-1"
          min={0}
          max={last}
          value={frame}
          onChange={(e) => {
            setPlaying(false);
            setFrame(Number(e.target.value));
          }}
        />
        <span className="shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
          {t('play.depouille.step', { n: frame + 1, total: trace.frames.length })}
        </span>
      </div>
    </div>
  );
};

export default DepouillementPanel;
