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

  // Preserve the guided onboarding tour + its ?tour=1 deep link from the navbar.
  const startTour = useCallback(() => {
    localStorage.removeItem('tour_completed');
    setTourRun(false);
    setTimeout(() => setTourRun(true), 100);
  }, []);
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
    // One screen, no scroll — but only where a screen actually has the room:
    // below `lg` the page falls back to normal vertical scrolling rather than
    // clipping content on a phone.
    <div
      data-style="tailwind"
      className="flex min-h-[calc(100dvh-49px)] flex-col lg:h-[calc(100dvh-49px)] lg:min-h-0 lg:overflow-hidden"
    >
      <OnboardingTour run={tourRun} onFinish={() => setTourRun(false)} />

      {/* ── Hero: thesis ⟷ live instrument ── */}
      <section data-tour="hero" className="flex-1 border-b border-border lg:min-h-0">
        <div className="container mx-auto flex h-full max-w-6xl items-center px-4 py-4 sm:py-5">
          <div className="grid w-full items-center gap-6 lg:grid-cols-[1fr_minmax(0,26rem)]">
            <div>
              <p className="font-mono text-[0.7rem] uppercase tracking-[0.22em] text-primary">
                {t('home.eyebrow')}
              </p>
              <h1 className="mt-2 font-display text-3xl font-bold leading-[1.08] tracking-tight sm:text-4xl">
                {t('home.h1Line1')}
                <br />
                <span className="text-primary">{t('home.h1Line2')}</span>
              </h1>
              <p className="mt-3 max-w-md text-sm leading-relaxed text-muted-foreground">
                {t('home.heroLede')}
              </p>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <Button size="lg" variant="primary" className="px-5" onClick={openInstrument}>
                  <SlidersHorizontal aria-hidden className="h-4 w-4" />
                  {t('home.ctaOpen')} →
                </Button>
                <Button size="lg" variant="outline" onClick={startTour}>
                  {t('home.ctaGuided')}
                </Button>
              </div>
              <p className="mt-2 font-mono text-[0.68rem] uppercase tracking-[0.12em] text-muted-foreground">
                {t('home.reassure')}
              </p>
            </div>

            <HeroInstrument />
          </div>
        </div>
      </section>

      {/* ── The journey: five moments, one strip ── */}
      <section className="shrink-0 border-b border-border">
        <div className="container mx-auto max-w-6xl px-4 py-3">
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

      {/* ── Histoires: one horizontal rail, so nine stories cost one row ── */}
      <section className="shrink-0 border-b border-border">
        <div className="container mx-auto max-w-6xl px-4 py-3">
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <p className="font-mono text-[0.7rem] uppercase tracking-[0.22em] text-primary">
              {tp('stories.launch')}
            </p>
            <p className="text-[0.72rem] text-muted-foreground">{tp('stories.launchHint')}</p>
          </div>
          <ul className="mt-2 flex snap-x gap-2 overflow-x-auto pb-1">
            {STORIES.map((s) => (
              <li key={s.id} className="shrink-0 snap-start">
                <Link
                  to={`/playground?story=${s.id}`}
                  title={tp(s.taglineKey)}
                  className="group flex w-52 flex-col gap-0.5 rounded-lg border border-border bg-card px-2.5 py-1.5 transition-colors hover:border-primary/40 hover:bg-accent/40"
                >
                  <span className="flex items-baseline justify-between gap-2">
                    <span className="truncate font-display text-[0.8rem] font-semibold leading-tight group-hover:text-primary">
                      {tp(s.titleKey)}
                    </span>
                    {/* Which instrument the story opens — the two have separate story sets. */}
                    <span className="shrink-0 font-mono text-[0.58rem] uppercase tracking-[0.12em] text-muted-foreground">
                      {tp(s.mode === 'leader' ? 'mode.leader' : 'mode.assembly')}
                    </span>
                  </span>
                  <span className="truncate text-[0.7rem] leading-snug text-muted-foreground">
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
