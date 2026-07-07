import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Pause, Play, RotateCcw, Shuffle } from 'lucide-react';
import { Modal } from '@/components/ui/modal';
import { useVotingLabels } from '../../hooks/useVotingLabels';
import { buildTrace, sampleVoters } from '../../lib/voteTrace';
import { LEADER_RULES, EXTRA_RULES } from '../../lib/scorecard';
import { type Rule, type Pt, type NamedPt } from '../../lib/playgroundVoting';
import { getMethodInfo, type Lang } from '@/lib/methodInfo';
import { CANDIDATE_COLORS_LIGHT } from '../../constants/chartColors';

// Faster animation ⇒ more ballots (each beat is quicker, so a bigger electorate
// still stays watchable). One shared sample per speed, re-drawn on reshuffle.
const SPEEDS = [
  { key: 'calm', n: 15, div: 1 },
  { key: 'normal', n: 30, div: 2 },
  { key: 'fast', n: 60, div: 4 },
];
// Base beat: counting drops one ballot per beat (fast); rounds/duels need reading.
const STEP_MS: Record<string, number> = {
  count: 380,
  lottery: 900,
  elim: 950,
  pairwise: 850,
  twophase: 1100,
};

interface Props {
  show: boolean;
  onHide: () => void;
  voters: Pt[];
  candidates: NamedPt[];
  initialRule: Rule;
}

const MethodReplayModal: React.FC<Props> = ({ show, onHide, voters, candidates, initialRule }) => {
  const { t, i18n } = useTranslation('playground');
  const { ruleLabels } = useVotingLabels();
  const lang: Lang = i18n.language?.startsWith('en') ? 'en' : 'fr';
  const [rule, setRule] = useState<Rule>(initialRule);
  const [seed, setSeed] = useState(1);
  const [speedIdx, setSpeedIdx] = useState(0);
  const [frame, setFrame] = useState(0);
  const [playing, setPlaying] = useState(true);

  // Re-sync the selected rule whenever the modal is (re)opened for a new method.
  useEffect(() => {
    if (show) setRule(initialRule);
  }, [show, initialRule]);

  const speed = SPEEDS[speedIdx];
  const sample = useMemo(() => sampleVoters(voters, speed.n, seed), [voters, speed.n, seed]);
  const trace = useMemo(
    () => (candidates.length >= 2 ? buildTrace(sample, candidates, rule) : null),
    [sample, candidates, rule]
  );

  // Restart the animation on any change of what's being shown.
  useEffect(() => {
    setFrame(0);
    setPlaying(true);
  }, [rule, seed, speedIdx, show]);

  const nFrames = trace?.frames.length ?? 0;
  const atEnd = frame >= nFrames - 1;

  // Auto-advance while playing.
  const timer = useRef<number | null>(null);
  useEffect(() => {
    if (!show || !playing || !trace || atEnd) return;
    const ms = (STEP_MS[trace.family] ?? 800) / speed.div;
    timer.current = window.setTimeout(() => setFrame((f) => f + 1), ms);
    return () => {
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [show, playing, trace, frame, atEnd, speed.div]);

  if (!trace) return null;

  const cur = trace.frames[Math.min(frame, nFrames - 1)];
  const scale = Math.max(1, ...trace.frames.flatMap((f) => f.bars));
  const color = (i: number) => CANDIDATE_COLORS_LIGHT[i % CANDIDATE_COLORS_LIGHT.length];
  const winnerName = trace.winner >= 0 ? candidates[trace.winner].name : '—';
  const summary = getMethodInfo(rule)?.[lang].summary;

  return (
    <Modal show={show} onHide={onHide} size="lg" centered scrollable>
      <Modal.Header closeButton>
        <Modal.Title>{t('replay.title', { method: ruleLabels[rule] })}</Modal.Title>
      </Modal.Header>

      <Modal.Body className="flex flex-col gap-3">
        {/* Method picker — keeps the SAME sampled ballots for direct comparison. */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <label className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">{t('replay.methodLabel')}</span>
            <select
              data-testid="replay-method"
              className="rounded-md border border-input bg-background px-2 py-1 text-sm"
              value={rule}
              onChange={(e) => setRule(e.target.value as Rule)}
            >
              <optgroup label={t('replay.groupCompared')}>
                {LEADER_RULES.map((r) => (
                  <option key={r} value={r}>
                    {ruleLabels[r]}
                  </option>
                ))}
              </optgroup>
              <optgroup label={t('replay.groupExtra')}>
                {EXTRA_RULES.map((r) => (
                  <option key={r} value={r}>
                    {ruleLabels[r]}
                  </option>
                ))}
              </optgroup>
            </select>
          </label>
          <div className="flex items-center gap-1 text-xs">
            <span className="text-muted-foreground">{t('replay.speed')}</span>
            {SPEEDS.map((s, i) => (
              <button
                key={s.key}
                type="button"
                data-testid={`replay-speed-${s.key}`}
                onClick={() => setSpeedIdx(i)}
                className={`rounded border px-2 py-0.5 ${
                  i === speedIdx
                    ? 'border-primary text-primary'
                    : 'border-border text-muted-foreground'
                }`}
              >
                {t(`replay.speed_${s.key}`)}
              </button>
            ))}
          </div>
        </div>

        {/* Plain-language explanation of the method + what the animation shows. */}
        <div className="rounded-md border border-border bg-muted/20 px-3 py-2">
          {summary && <p className="text-sm">{summary}</p>}
          <p className="mt-1 text-xs text-muted-foreground">{t(`replay.family.${trace.family}`)}</p>
        </div>

        <p className="text-right text-[0.7rem] text-muted-foreground">
          {t('replay.sampleNote', { count: trace.sampleSize })}
        </p>

        {/* Bars */}
        <div className="flex flex-col gap-1.5" data-testid="replay-bars">
          {candidates.map((c, i) => {
            const val = cur.bars[i] ?? 0;
            const dead = cur.eliminated?.[i];
            const lit = cur.highlight?.includes(i);
            return (
              <div
                key={c.name}
                className={`flex items-center gap-2 rounded px-1 py-0.5 transition-opacity ${
                  dead ? 'opacity-35' : ''
                } ${lit ? 'bg-muted/60' : ''}`}
              >
                <span
                  className={`w-24 shrink-0 truncate text-xs ${lit ? 'font-semibold' : ''} ${
                    dead ? 'line-through' : ''
                  }`}
                  style={{ color: color(i) }}
                >
                  {c.name}
                </span>
                <div className="relative h-4 flex-1 overflow-hidden rounded bg-muted/40">
                  <div
                    className="absolute inset-y-0 left-0 rounded transition-[width] duration-300 ease-out"
                    style={{ width: `${(val / scale) * 100}%`, background: color(i) }}
                  />
                </div>
                <span className="w-10 shrink-0 text-right text-xs tabular-nums text-muted-foreground">
                  {Math.round(val * 10) / 10}
                </span>
              </div>
            );
          })}
        </div>
        <p className="text-[0.65rem] text-muted-foreground">{t(trace.unitKey)}</p>

        {/* Caption for the current beat */}
        <div
          data-testid="replay-caption"
          className="min-h-[2.5rem] rounded-md border border-border bg-muted/30 px-3 py-2 text-sm"
        >
          {t(cur.caption.key, cur.caption.params)}
        </div>

        {/* Progress */}
        <div className="flex items-center gap-2">
          <div className="h-1 flex-1 overflow-hidden rounded-full bg-muted/50">
            <div
              className="h-full rounded-full bg-primary transition-[width] duration-300"
              style={{ width: `${nFrames > 1 ? (frame / (nFrames - 1)) * 100 : 100}%` }}
            />
          </div>
          <span className="text-[0.65rem] tabular-nums text-muted-foreground">
            {t('replay.step', { i: frame + 1, n: nFrames })}
          </span>
        </div>
      </Modal.Body>

      <Modal.Footer className="justify-between">
        <span className="text-sm">
          {t('replay.winner')}{' '}
          <strong style={{ color: color(Math.max(0, trace.winner)) }}>{winnerName}</strong>
        </span>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            data-testid="replay-reshuffle"
            onClick={() => setSeed((s) => s + 1)}
            title={t('replay.reshuffle')}
            className="flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs hover:bg-accent"
          >
            <Shuffle className="h-3.5 w-3.5" /> {t('replay.reshuffle')}
          </button>
          <button
            type="button"
            data-testid="replay-restart"
            onClick={() => {
              setFrame(0);
              setPlaying(true);
            }}
            title={t('replay.restart')}
            className="flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs hover:bg-accent"
          >
            <RotateCcw className="h-3.5 w-3.5" /> {t('replay.restart')}
          </button>
          <button
            type="button"
            data-testid="replay-playpause"
            onClick={() => {
              if (atEnd) {
                setFrame(0);
                setPlaying(true);
              } else setPlaying((p) => !p);
            }}
            className="flex items-center gap-1 rounded-md border border-primary px-3 py-1 text-xs font-medium text-primary hover:bg-primary/10"
          >
            {playing && !atEnd ? (
              <>
                <Pause className="h-3.5 w-3.5" /> {t('replay.pause')}
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5" /> {t('replay.play')}
              </>
            )}
          </button>
        </div>
      </Modal.Footer>
    </Modal>
  );
};

export default MethodReplayModal;
