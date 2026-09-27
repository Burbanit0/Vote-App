import React, { useEffect, useReducer, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  INITIAL_PLAYER,
  PLAYER_SPEEDS,
  beatMs,
  keyTarget,
  nextBeat,
  playFrom,
  playerReducer,
  type PlayerSpeed,
} from '../../lib/polity/playerClock';
import { simulatedDate } from '../../lib/polity/ticks';
import { usePolityCtx } from './PolityController';

/**
 * The tick player: a scrubber over the run's ticks, play and pause, a step each
 * way and a speed. The tick is the page's (in the URL); playback never starts on
 * its own and stops at the run's last tick.
 */
const TickPlayer: React.FC = () => {
  const { t } = useTranslation('polity');
  const { overview, tick, setTick } = usePolityCtx();
  const [player, dispatch] = useReducer(playerReducer, INITIAL_PLAYER);
  const lastTick = overview?.last_tick ?? 0;
  const ticksPerYear = overview?.ticks_per_year ?? 1;
  const tickRef = useRef(tick);
  tickRef.current = tick;

  useEffect(() => {
    if (!player.playing) return undefined;
    const id = window.setInterval(() => {
      const next = nextBeat(tickRef.current, lastTick);
      if (next === null) dispatch({ type: 'pause' });
      else setTick(next);
    }, beatMs(player.speed));
    return () => window.clearInterval(id);
  }, [player.playing, player.speed, lastTick, setTick]);

  if (!overview) return null;

  const toggle = () => {
    if (!player.playing) setTick(playFrom(tick, lastTick));
    dispatch({ type: 'toggle' });
  };
  const onKeyDown = (event: React.KeyboardEvent) => {
    // Space belongs to whichever control has focus: it opens the speed menu and presses
    // the buttons (the play button's own Space toggles playback, the same as this
    // shortcut). The toolbar claims it only when the key came from the toolbar itself.
    if (event.key === ' ' && event.target !== event.currentTarget) return;
    const target = keyTarget(event.key, tick, lastTick, ticksPerYear);
    if (target === null) return;
    event.preventDefault();
    if (target === 'toggle') toggle();
    else setTick(target);
  };
  const date = simulatedDate(tick, ticksPerYear);
  const dateLabel = t('runFacts.tickValue', { year: date.year, quarter: date.quarter });

  return (
    <div
      data-testid="polity-player"
      role="toolbar"
      aria-label={t('player.label')}
      onKeyDown={onKeyDown}
      className="flex flex-wrap items-center gap-3 rounded-md border border-border px-3 py-2"
    >
      <div className="flex items-center gap-1">
        <button
          type="button"
          data-testid="player-step-back"
          aria-label={t('player.stepBack')}
          className="rounded border border-border px-2 py-1 text-sm disabled:opacity-40"
          disabled={tick <= 0}
          onClick={() => setTick(tick - 1)}
        >
          ◀
        </button>
        <button
          type="button"
          data-testid="player-toggle"
          aria-pressed={player.playing}
          className="min-w-[4.5rem] rounded border border-primary px-3 py-1 text-sm font-semibold text-primary"
          onClick={toggle}
        >
          {player.playing ? t('player.pause') : t('player.play')}
        </button>
        <button
          type="button"
          data-testid="player-step-forward"
          aria-label={t('player.stepForward')}
          className="rounded border border-border px-2 py-1 text-sm disabled:opacity-40"
          disabled={tick >= lastTick}
          onClick={() => setTick(tick + 1)}
        >
          ▶
        </button>
      </div>
      <input
        type="range"
        data-testid="player-slider"
        aria-label={t('player.slider')}
        aria-valuetext={dateLabel}
        className="min-w-[10rem] flex-1 accent-[var(--bs-primary)]"
        min={0}
        max={lastTick}
        step={1}
        value={tick}
        onChange={(e) => setTick(Number(e.target.value))}
      />
      <span data-testid="player-position" className="font-mono text-xs tabular-nums">
        {t('player.position', { year: date.year, quarter: date.quarter, tick, last: lastTick })}
      </span>
      <label className="flex items-center gap-1 text-xs" htmlFor="player-speed">
        {t('player.speed')}
        <select
          id="player-speed"
          data-testid="player-speed"
          className="rounded border border-border bg-background px-1 py-0.5"
          value={player.speed}
          onChange={(e) =>
            dispatch({ type: 'speed', speed: Number(e.target.value) as PlayerSpeed })
          }
        >
          {PLAYER_SPEEDS.map((speed) => (
            <option key={speed} value={speed}>
              {t('player.speedValue', { speed })}
            </option>
          ))}
        </select>
      </label>
      <p className="w-full text-[0.68rem] text-muted-foreground">{t('player.keys')}</p>
    </div>
  );
};

export default TickPlayer;
