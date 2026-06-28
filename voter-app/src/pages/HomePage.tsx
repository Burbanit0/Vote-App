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

// HomePage — the doorway. One job: land the thesis (the rule decides, not just the
// voters) and drop the visitor into the instrument. The hero is that thesis made
// live (HeroInstrument); everything below funnels to /playground.

const FOOTER_LINKS = [
  { href: '/quiz', key: 'nav.quiz' },
  { href: '/theory', key: 'nav.theory' },
  { href: '/regimes-internationaux', key: 'nav.regimesInternationaux' },
  { href: '/galerie', key: 'nav.gallery' },
  { href: '/api-docs', key: 'nav.apiDocs' },
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
    <div data-style="tailwind">
      <OnboardingTour run={tourRun} onFinish={() => setTourRun(false)} />

      {/* ── Hero: thesis ⟷ live instrument ── */}
      <section data-tour="hero" className="border-b border-border">
        <div className="container mx-auto max-w-6xl px-4 py-12 sm:py-16">
          <div className="grid items-start gap-10 lg:grid-cols-[1fr_minmax(0,26rem)]">
            <div className="lg:pt-6">
              <p className="font-mono text-[0.7rem] uppercase tracking-[0.22em] text-primary">
                {t('home.eyebrow')}
              </p>
              <h1 className="mt-3 font-display text-4xl font-bold leading-[1.04] tracking-tight sm:text-5xl">
                {t('home.h1Line1')}
                <br />
                <span className="text-primary">{t('home.h1Line2')}</span>
              </h1>
              <p className="mt-4 max-w-md text-base leading-relaxed text-muted-foreground">
                {t('home.heroLede')}
              </p>
              <div className="mt-7 flex flex-wrap items-center gap-3">
                <Button size="lg" variant="primary" className="px-5" onClick={openInstrument}>
                  <SlidersHorizontal aria-hidden className="h-4 w-4" />
                  {t('home.ctaOpen')} →
                </Button>
                <Button size="lg" variant="outline" onClick={startTour}>
                  {t('home.ctaGuided')}
                </Button>
              </div>
              <p className="mt-4 font-mono text-[0.68rem] uppercase tracking-[0.12em] text-muted-foreground">
                {t('home.reassure')}
              </p>
            </div>

            <HeroInstrument />
          </div>
        </div>
      </section>

      {/* ── The journey: five moments, one instrument ── */}
      <section className="container mx-auto max-w-6xl px-4 py-12 sm:py-16">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.22em] text-primary">
          {t('home.journeyKicker')}
        </p>
        <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <h2 className="font-display text-2xl font-bold tracking-tight sm:text-3xl">
            {t('home.journeyTitle')}
          </h2>
          <p className="max-w-md text-sm text-muted-foreground">{t('home.journeyLede')}</p>
        </div>

        <ol className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {MOMENTS.map((m) => (
            <li key={m.id}>
              <Link
                to="/playground"
                className="group flex h-full flex-col gap-1.5 rounded-xl border border-border bg-card p-4 transition-colors hover:border-primary/40 hover:bg-accent/40"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm font-semibold tabular-nums text-primary">
                    {m.n}
                  </span>
                  <m.Icon
                    aria-hidden
                    className="h-5 w-5 text-muted-foreground transition-colors group-hover:text-primary"
                  />
                </div>
                <span className="font-display text-base font-semibold leading-tight">
                  {tp(`moments.${m.id}.label`)}
                </span>
                <span className="text-[0.78rem] leading-snug text-muted-foreground">
                  {tp(`moments.${m.id}.hint`)}
                </span>
              </Link>
            </li>
          ))}
        </ol>

        <div className="mt-6">
          <Button variant="primary" onClick={() => navigate('/playground')}>
            {t('home.journeyCta')} →
          </Button>
        </div>
      </section>

      {/* ── Footer: go further ── */}
      <footer className="border-t border-border bg-muted/30">
        <div className="container mx-auto max-w-6xl px-4 py-6">
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
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <Link to="/login" className="transition-colors hover:text-foreground">
                {t('nav.login')}
              </Link>
              <Link to="/register" className="transition-colors hover:text-foreground">
                {t('nav.register')}
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default HomePage;
