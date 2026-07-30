import React from 'react';
import { useTranslation } from 'react-i18next';
import {
  Ghost,
  Minimize2,
  RefreshCw,
  Swords,
  Sparkles,
  Shuffle,
  Scissors,
  Landmark,
  Divide,
  Copy,
  Ban,
  TrendingUp,
  Repeat,
  BookOpen,
  X,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { usePlaygroundCtx } from './PlaygroundController';
import { storiesForMode, storyById, type Story, type StoryStep } from '../../lib/stories';
import { track } from '../../lib/analytics';
import type {
  ElectionConfig,
  PlaygroundMode,
  PlaygroundState,
} from '../../stores/useElectionStore';
import type { Rule } from '../../lib/playgroundVoting';
import type { MomentId } from './MomentRail';

// StoryPlayer — the "histoires" surface. A story is scripted data (lib/stories.ts);
// this component is the thin player that applies each beat's patch through the SAME
// context setters the user drives by hand, so a story is just a guided tour of the
// live instrument (never a parallel mock). On start it snapshots the sandbox; on
// quit it restores it, so a story never eats the visitor's own setup.

const ICONS: Record<string, LucideIcon> = {
  Ghost,
  Minimize2,
  RefreshCw,
  Swords,
  Sparkles,
  Shuffle,
  Scissors,
  Landmark,
  Divide,
  Copy,
  Ban,
  TrendingUp,
  Repeat,
};

interface Snapshot {
  config: ElectionConfig;
  playground: PlaygroundState;
  rule: Rule;
  moment: MomentId;
}

const StoryPlayer: React.FC = () => {
  const ctx = usePlaygroundCtx();
  const { t } = useTranslation('playground');
  const [pickerOpen, setPickerOpen] = React.useState(false);
  const [active, setActive] = React.useState<Story | null>(null);
  const [stepIdx, setStepIdx] = React.useState(0);
  const snapshot = React.useRef<Snapshot | null>(null);
  // One completion event per playthrough, however often the user scrubs the end.
  const completed = React.useRef(false);

  // Apply one beat: patch only what the step declares, via the live setters.
  const applyStep = (step: StoryStep) => {
    if (step.mode) ctx.setMode(step.mode);
    if (step.config) ctx.setConfig(step.config);
    if (step.playground) ctx.setPlayground(step.playground);
    if (step.rule) ctx.setLeaderRule(step.rule);
    if (step.moment) ctx.setActiveMoment(step.moment);
  };

  const start = (story: Story) => {
    // Snapshot the current sandbox once, so quitting restores it verbatim.
    snapshot.current = {
      config: ctx.config,
      playground: ctx.playground,
      rule: ctx.leaderRule,
      moment: ctx.activeMoment,
    };
    setActive(story);
    setStepIdx(0);
    setPickerOpen(false);
    completed.current = false;
    track('story_started', { story: story.id });
    applyStep(story.steps[0]);
  };

  const goto = (idx: number) => {
    if (!active) return;
    const clamped = Math.max(0, Math.min(active.steps.length - 1, idx));
    if (clamped === active.steps.length - 1 && !completed.current) {
      completed.current = true;
      track('story_completed', { story: active.id });
    }
    setStepIdx(clamped);
    applyStep(active.steps[clamped]);
  };

  // `mode` lives inside PlaygroundState, so restoring the snapshot restores the
  // instrument too. `keepMode` overrides that for the one case where it would be
  // wrong: the user flipped the Dirigeant/Assemblée toggle themselves.
  const quit = (keepMode?: PlaygroundMode) => {
    const s = snapshot.current;
    if (s) {
      ctx.setConfig(s.config);
      ctx.setPlayground(keepMode ? { ...s.playground, mode: keepMode } : s.playground);
      ctx.setLeaderRule(s.rule);
      ctx.setActiveMoment(s.moment);
    }
    snapshot.current = null;
    setActive(null);
  };

  // Switching instrument abandons the story it was narrating — its beats describe
  // the other mode. The sandbox comes back, but on the mode the user just picked.
  React.useEffect(() => {
    if (active && active.mode !== ctx.mode) quit(ctx.mode);
  }, [ctx.mode]);

  // Homepage hand-off: "/playground?story=<id>" auto-starts that story on mount.
  // Mount-only — `start` captures the pre-story sandbox as the restore point.
  React.useEffect(() => {
    const id = new URLSearchParams(window.location.search).get('story');
    if (id) {
      const s = storyById(id);
      if (s) start(s);
    }
  }, []);

  // ── Active: the "now playing" banner ──────────────────────────────────────
  if (active) {
    const step = active.steps[stepIdx];
    const isLast = stepIdx === active.steps.length - 1;
    return (
      <div
        data-testid="story-bar"
        className="mb-3 rounded-xl border border-primary/40 bg-primary/5 p-3 shadow-sm"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-primary/15 text-primary">
              <BookOpen aria-hidden className="h-3.5 w-3.5" />
            </span>
            <p className="truncate font-display text-sm font-semibold">{t(active.titleKey)}</p>
          </div>
          <Button
            data-testid="story-quit"
            variant="ghost"
            size="sm"
            className="h-7 shrink-0 gap-1 px-2 text-muted-foreground"
            onClick={() => quit()}
          >
            <X aria-hidden className="h-3.5 w-3.5" />
            {t('stories.quit')}
          </Button>
        </div>

        <p data-testid="story-beat" className="mt-2 text-sm leading-relaxed text-foreground">
          {t(step.beatKey)}
        </p>

        <div className="mt-3 flex items-center justify-between gap-3">
          <Button
            data-testid="story-prev"
            variant="outline"
            size="sm"
            disabled={stepIdx === 0}
            onClick={() => goto(stepIdx - 1)}
          >
            {t('stories.prev')}
          </Button>

          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1" aria-hidden>
              {active.steps.map((s, i) => (
                <span
                  key={s.id}
                  className={cn(
                    'h-1.5 w-1.5 rounded-full',
                    i === stepIdx ? 'bg-primary' : i < stepIdx ? 'bg-primary/40' : 'bg-border'
                  )}
                />
              ))}
            </span>
            <span className="font-mono text-[0.7rem] uppercase tracking-[0.12em] text-muted-foreground">
              {t('stories.step', { n: stepIdx + 1, total: active.steps.length })}
            </span>
          </div>

          {isLast ? (
            <Button data-testid="story-restart" variant="outline" size="sm" onClick={() => goto(0)}>
              {t('stories.restart')}
            </Button>
          ) : (
            <Button
              data-testid="story-next"
              variant="primary"
              size="sm"
              onClick={() => goto(stepIdx + 1)}
            >
              {t('stories.next')}
            </Button>
          )}
        </div>
      </div>
    );
  }

  // ── Idle: the launcher + picker ───────────────────────────────────────────
  return (
    <div className="mb-3">
      <Button
        data-testid="story-launch"
        variant="outline"
        size="sm"
        className="gap-2"
        onClick={() => setPickerOpen((o) => !o)}
        aria-expanded={pickerOpen}
      >
        <BookOpen aria-hidden className="h-4 w-4" />
        {t('stories.launch')}
      </Button>

      {pickerOpen && (
        <div
          data-testid="story-picker"
          className="mt-2 grid grid-cols-1 gap-2 rounded-xl border border-border bg-card p-3 sm:grid-cols-2 lg:grid-cols-3"
        >
          {storiesForMode(ctx.mode).map((story) => {
            const Icon = ICONS[story.icon] ?? BookOpen;
            return (
              <button
                key={story.id}
                type="button"
                data-testid={`story-pick-${story.id}`}
                onClick={() => start(story)}
                className="group flex flex-col gap-1 rounded-lg border border-border bg-muted/20 p-3 text-left transition-colors hover:border-primary/40 hover:bg-accent/40"
              >
                <span className="flex items-center gap-2">
                  <Icon
                    aria-hidden
                    className="h-4 w-4 text-primary transition-colors group-hover:text-primary"
                  />
                  <span className="font-display text-sm font-semibold leading-tight">
                    {t(story.titleKey)}
                  </span>
                </span>
                <span className="text-[0.72rem] leading-snug text-muted-foreground">
                  {t(story.taglineKey)}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default StoryPlayer;
