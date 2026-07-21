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
    <div data-style="tailwind" className="flex min-h-[calc(100dvh-49px)] flex-col">
      <OnboardingTour run={tourRun} onFinish={() => setTourRun(false)} />

      {/* ── Hero: thesis ⟷ live instrument ── */}
      <section data-tour="hero" className="flex-1 border-b border-border">
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

      {/* ── The journey: five moments, one instrument ── */}
      <section className="container mx-auto max-w-6xl px-4 py-4 sm:py-5">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.22em] text-primary">
          {t('home.journeyKicker')}
        </p>
        <div className="mt-1 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <h2 className="font-display text-xl font-bold tracking-tight sm:text-2xl">
            {t('home.journeyTitle')}
          </h2>
          <p className="max-w-md text-sm text-muted-foreground">{t('home.journeyLede')}</p>
        </div>

        <ol className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-5">
          {MOMENTS.map((m) => (
            <li key={m.id}>
              <Link
                to="/playground"
                className="group flex h-full flex-col gap-1 rounded-xl border border-border bg-card p-3 transition-colors hover:border-primary/40 hover:bg-accent/40"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm font-semibold tabular-nums text-primary">
                    {m.n}
                  </span>
                  <m.Icon
                    aria-hidden
                    className="h-4 w-4 text-muted-foreground transition-colors group-hover:text-primary"
                  />
                </div>
                <span className="font-display text-sm font-semibold leading-tight">
                  {tp(`moments.${m.id}.label`)}
                </span>
                <span className="text-[0.72rem] leading-snug text-muted-foreground">
                  {tp(`moments.${m.id}.hint`)}
                </span>
              </Link>
            </li>
          ))}
        </ol>

        <div className="mt-3">
          <Button variant="primary" onClick={() => navigate('/playground')}>
            {t('home.journeyCta')} →
          </Button>
        </div>
      </section>

      {/* ── Histoires: guided narratives ── */}
      <section className="border-t border-border">
        <div className="container mx-auto max-w-6xl px-4 py-4 sm:py-5">
          <p className="font-mono text-[0.7rem] uppercase tracking-[0.22em] text-primary">
            {tp('stories.launch')}
          </p>
          <p className="mt-1 max-w-md text-sm text-muted-foreground">{tp('stories.launchHint')}</p>
          <ul className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {STORIES.map((s) => (
              <li key={s.id}>
                <Link
                  to={`/playground?story=${s.id}`}
                  className="group flex h-full flex-col gap-1 rounded-xl border border-border bg-card p-3 transition-colors hover:border-primary/40 hover:bg-accent/40"
                >
                  <span className="flex items-baseline justify-between gap-2">
                    <span className="font-display text-sm font-semibold leading-tight group-hover:text-primary">
                      {tp(s.titleKey)}
                    </span>
                    {/* Which instrument the story opens — the two have separate story sets. */}
                    <span className="shrink-0 font-mono text-[0.6rem] uppercase tracking-[0.12em] text-muted-foreground">
                      {tp(s.mode === 'leader' ? 'mode.leader' : 'mode.assembly')}
                    </span>
                  </span>
                  <span className="text-[0.72rem] leading-snug text-muted-foreground">
                    {tp(s.taglineKey)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* ── Lab bridge ── */}
      <section className="border-t border-border bg-accent/20">
        <div className="container mx-auto max-w-6xl px-4 py-4 sm:py-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-mono text-[0.7rem] uppercase tracking-[0.22em] text-primary">
                {t('home.labKicker')}
              </p>
              <h2 className="mt-1 font-display text-xl font-bold tracking-tight">
                {t('home.labTitle')}
              </h2>
              <p className="mt-1 max-w-md text-sm text-muted-foreground">{t('home.labLede')}</p>
            </div>
            <Button variant="outline" asChild className="shrink-0">
              <Link to="/laboratoire">{t('home.ctaLab')}</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* ── Footer: go further ── */}
      <footer className="border-t border-border bg-muted/30">
        <div className="container mx-auto max-w-6xl px-4 py-3">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
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
          </div>
        </div>
      </footer>
    </div>
  );
};

export default HomePage;
