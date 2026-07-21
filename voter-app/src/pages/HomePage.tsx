import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { useTranslation } from 'react-i18next';
import { SlidersHorizontal } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useMetaTags } from '../hooks/useMetaTags';
import { useElection } from '../stores/useElectionStore';
import OnboardingTour from '../components/shared/OnboardingTour';
import HeroInstrument from '../components/home/HeroInstrument';
import { MOMENTS } from '../components/playground/MomentRail';
import { STORIES } from '../lib/stories';

// HomePage — the doorway. One job: land the thesis (the rule decides, not just the
// voters) and drop the visitor into the instrument. The hero is that thesis made
// live (HeroInstrument); everything below funnels to /playground.

const FOOTER_LINKS = [
  { href: '/decouvrir', key: 'home.ctaDiscover' },
  { href: '/playground', key: 'nav.playground' },
  { href: '/laboratoire', key: 'nav.laboratoire' },
];

const HomePage: React.FC = () => {
  const { t } = useTranslation();
  const { t: tp } = useTranslation('playground');
  const navigate = useNavigate();
  const { applyScenario } = useElection();
  const [tourRun, setTourRun] = useState(false);

  useMetaTags({
    title: `Vote Lab — ${t('home.h1Line1')} ${t('home.h1Line2')}`,
    description: t('home.heroLede'),
  });

  // The onboarding tour is started from the navbar "?" (a ?tour=1 deep link).
  useEffect(() => {
    // Only the navbar's "?tour=1" deep link (or the button) starts the tour — the
    // landing page leads with the instrument, not a popup.
    if (new URLSearchParams(window.location.search).get('tour') === '1') {
      const id = setTimeout(() => setTourRun(true), 600);
      return () => clearTimeout(id);
    }
  }, []);

  // Primary CTA: seed the spoiler electorate (the hero's story) then open the instrument.
  const openInstrument = useCallback(() => {
    applyScenario('france2002');
    navigate('/playground');
  }, [applyScenario, navigate]);

  return (
    // One screen, no scroll — but only where a screen actually has the room.
    // The gate is width AND height: with the nine story cards on one panel the
    // stack needs ~1020px of viewport, so shorter screens scroll normally rather
    // than have content clipped off. Note the `_` in the arbitrary variant — a
    // media query without spaces around `and` is invalid CSS and silently
    // mis-matches.
    <div
      data-style="tailwind"
      className="flex min-h-[calc(100dvh-49px)] flex-col [@media(min-width:1024px)_and_(min-height:1020px)]:h-[calc(100dvh-49px)] [@media(min-width:1024px)_and_(min-height:1020px)]:min-h-0 [@media(min-width:1024px)_and_(min-height:1020px)]:overflow-hidden"
    >
      <OnboardingTour run={tourRun} onFinish={() => setTourRun(false)} />

      {/* ── Hero: thesis ⟷ live instrument ──
          The hero takes NO leftover height (grow-0) — it is already the tallest
          band; the slack goes to the two panels below (1 / 2) so the page reads
          as three balanced blocks instead of one giant hero over two crammed
          rails. `grow-N` + `basis-auto`, never `flex-N` — the latter sets
          basis:0 and sizes sections by ratio alone, which shrinks the hero under
          its own instrument and clips it. */}
      <section
        data-tour="hero"
        className="flex flex-1 flex-col justify-center border-b border-border lg:grow-0 lg:basis-auto"
      >
        <div className="container mx-auto flex h-full max-w-6xl items-center px-4 py-4 sm:py-5">
          <div className="grid w-full items-center gap-6 lg:grid-cols-[1fr_minmax(0,26rem)]">
            <div className="flex flex-col justify-center gap-5">
              <div>
                <p className="font-mono text-[0.7rem] uppercase tracking-[0.22em] text-primary">
                  {t('home.eyebrow')}
                </p>
                <h1 className="mt-2 font-display text-3xl font-bold leading-[1.08] tracking-tight sm:text-4xl xl:text-5xl">
                  {t('home.h1Line1')}
                  <br />
                  <span className="text-primary">{t('home.h1Line2')}</span>
                </h1>
                <p className="mt-3 max-w-md text-sm leading-relaxed text-muted-foreground">
                  {t('home.heroLede')}
                </p>
              </div>
              <div>
                <div className="flex flex-wrap items-center gap-3">
                  <Button size="lg" variant="primary" className="px-5" onClick={openInstrument}>
                    <SlidersHorizontal aria-hidden className="h-4 w-4" />
                    {t('home.ctaOpen')} →
                  </Button>
                  {/* Newcomer on-ramp: /decouvrir teaches the concepts before the
                      full instrument. The UI tour stays on the navbar "?" button. */}
                  <Button size="lg" variant="outline" asChild>
                    <Link to="/decouvrir">{t('home.ctaDiscover')}</Link>
                  </Button>
                </div>
                <p className="mt-2 font-mono text-[0.68rem] uppercase tracking-[0.12em] text-muted-foreground">
                  {t('home.reassure')}
                </p>
              </div>
            </div>

            <HeroInstrument />
          </div>
        </div>
      </section>

      {/* ── The journey: five moments, one strip ── */}
      <section className="flex shrink-0 flex-col justify-center border-b border-border lg:grow lg:basis-auto">
        <div className="container mx-auto w-full max-w-6xl px-4 py-2.5">
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <p className="font-mono text-[0.7rem] uppercase tracking-[0.22em] text-primary">
              {t('home.journeyKicker')}
            </p>
            <p className="text-[0.72rem] text-muted-foreground">{t('home.journeyLede')}</p>
          </div>
          <ol className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
            {MOMENTS.map((m) => (
              <li key={m.id}>
                <Link
                  to="/playground"
                  title={tp(`moments.${m.id}.hint`)}
                  className="group flex items-center gap-2 rounded-lg border border-border bg-card px-2.5 py-1.5 transition-colors hover:border-primary/40 hover:bg-accent/40"
                >
                  <span className="font-mono text-xs font-semibold tabular-nums text-primary">
                    {m.n}
                  </span>
                  <m.Icon
                    aria-hidden
                    className="h-3.5 w-3.5 shrink-0 text-muted-foreground transition-colors group-hover:text-primary"
                  />
                  <span className="truncate font-display text-[0.8rem] font-semibold leading-tight">
                    {tp(`moments.${m.id}.label`)}
                  </span>
                </Link>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ── Histoires: all nine on one panel, no rail to scroll ── */}
      <section className="flex shrink-0 flex-col justify-center border-b border-border lg:grow-[2] lg:basis-auto">
        <div className="container mx-auto w-full max-w-6xl px-4 py-2.5">
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <p className="font-mono text-[0.7rem] uppercase tracking-[0.22em] text-primary">
              {tp('stories.launch')}
            </p>
            <p className="text-[0.72rem] text-muted-foreground">{tp('stories.launchHint')}</p>
          </div>
          <ul className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {STORIES.map((s) => (
              <li key={s.id}>
                <Link
                  to={`/playground?story=${s.id}`}
                  className="group flex h-full flex-col gap-1 rounded-lg border border-border bg-card px-3 py-2 transition-colors hover:border-primary/40 hover:bg-accent/40"
                >
                  <span className="flex items-baseline justify-between gap-2">
                    <span className="font-display text-sm font-semibold leading-tight group-hover:text-primary">
                      {tp(s.titleKey)}
                    </span>
                    {/* Which instrument the story opens — the two have separate story sets. */}
                    <span className="shrink-0 font-mono text-[0.58rem] uppercase tracking-[0.12em] text-muted-foreground">
                      {tp(s.mode === 'leader' ? 'mode.leader' : 'mode.assembly')}
                    </span>
                  </span>
                  <span className="text-[0.75rem] leading-snug text-muted-foreground">
                    {tp(s.taglineKey)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* ── Footer: the Lab bridge + where to go next, on one line ── */}
      <footer className="shrink-0 border-t border-border bg-muted/30">
        <div className="container mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-5 gap-y-2 px-4 py-2">
          <div className="flex flex-wrap items-center gap-x-5 gap-y-1">
            <span className="font-mono text-[0.7rem] uppercase tracking-[0.14em] text-muted-foreground">
              {t('home.footMore')}
            </span>
            {FOOTER_LINKS.map((l) => (
              <Link
                key={l.href}
                to={l.href}
                className="text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                {t(l.key)}
              </Link>
            ))}
          </div>
          <div className="flex items-center gap-3">
            <p className="hidden text-[0.72rem] text-muted-foreground sm:block">
              {t('home.labLede')}
            </p>
            <Button variant="outline" size="sm" asChild className="shrink-0">
              <Link to="/laboratoire">{t('home.ctaLab')}</Link>
            </Button>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default HomePage;
