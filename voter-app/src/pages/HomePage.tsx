import React, { useCallback, useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { useMetaTags } from '../hooks/useMetaTags';
import { hasSavedConfig, useElection } from '../stores/useElectionStore';
import { homeExampleCandidates } from '../lib/home/carry';
import HeroInstrument from '../components/home/HeroInstrument';
import HomeEntrance from '../components/home/HomeEntrance';
import CountStory from '../components/home/CountStory';
import MomentsTrack from '../components/home/MomentsTrack';
import StoriesRegister from '../components/home/StoriesRegister';
import BallotBoxFinale from '../components/home/BallotBoxFinale';
import SectionRail from '../components/home/SectionRail';
import MethodStrip from '../components/home/MethodStrip';
import type { RuleId } from '../lib/home/scenario';
import HandoverMap from '../components/home/HandoverMap';

// HomePage — the doorway, "Bureau de vote": the thesis (the rule decides, not just the
// voters) made live in the hero, then told as a count you scroll through, then the
// five moments of the instrument, the guided stories, and a last call to open it.
// Every motion has a still version (prefers-reduced-motion), and the design source is
// the "Iteration 2: motion" row of the identity canvas.

const FOOTER_LINKS = [
  { href: '/decouvrir', key: 'home.ctaDiscover' },
  { href: '/playground', key: 'nav.playground' },
  { href: '/laboratoire', key: 'nav.laboratoire' },
  { href: '/laboratoire?exp=lexique', key: 'nav.lexique' },
  { href: '/polity', key: 'nav.polity', testid: 'home-foot-polity' },
];

/** Hero lines and blocks, in the order they settle in after the entrance. */
const rise = (entered: boolean, delayMs: number): React.CSSProperties => ({
  animationPlayState: entered ? 'running' : 'paused',
  animationDelay: `${delayMs}ms`,
});

const HomePage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { setConfig } = useElection();
  const [entered, setEntered] = useState(false);
  const onEntered = useCallback(() => setEntered(true), []);
  // The tally sheet's rule: the hero's instrument sets it, the method strip echoes it.
  const [rule, setRule] = useState<RuleId>('plurality');

  useMetaTags({
    title: `Vote Lab — ${t('home.h1Line1')} ${t('home.h1Line2')}`,
    description: t('home.heroLede'),
  });

  // Open the instrument on the example the page has just taught. Only for a visitor with nothing
  // saved: a returning one finds their own candidates, not ours.
  const openInstrument = useCallback(() => {
    if (!hasSavedConfig()) setConfig({ candidates: homeExampleCandidates() });
    navigate('/playground');
  }, [setConfig, navigate]);

  return (
    <div data-style="tailwind" data-home>
      <HomeEntrance onReveal={onEntered} />
      <SectionRail />
      <HandoverMap />

      <section
        id="home-top"
        data-testid="home-hero"
        aria-labelledby="home-title"
        // The whole first screen: the thesis and its instrument, then every method's verdict.
        className="mx-auto flex min-h-[calc(100dvh-49px)] max-w-6xl flex-col justify-center gap-12 px-4 py-10 sm:px-6 [@media(max-height:960px)]:gap-8 [@media(max-height:960px)]:py-6"
      >
        <div className="flex flex-wrap items-center gap-x-16 gap-y-12">
          <div
            className="flex min-w-0 flex-[1_1_440px] flex-col gap-6"
            // Lifts away as the map flies on to the count (HandoverMap).
            data-handover-out
            style={{
              opacity: 'calc(1 - var(--handover, 0) * 1.6)',
              transform: 'translateY(calc(var(--handover, 0) * -60px))',
            }}
          >
            <h1
              id="home-title"
              className="font-display text-[clamp(56px,6vw,96px)] leading-[0.9] font-extrabold [@media(max-height:960px)]:text-[clamp(52px,5.4vw,84px)]"
            >
              <span className="-mb-[0.08em] block overflow-hidden pb-[0.08em]">
                <span className="home-rise block" style={rise(entered, 100)}>
                  {t('home.h1Line1')}
                </span>
              </span>{' '}
              <span className="-mb-[0.08em] block overflow-hidden pb-[0.08em]">
                <span className="home-rise block" style={rise(entered, 160)}>
                  {t('home.h1Line2')}
                </span>
              </span>
            </h1>
            <p
              className="home-up max-w-[34rem] text-xl text-muted-foreground"
              style={rise(entered, 340)}
            >
              {t('home.heroLede')}
            </p>
            <div className="home-up flex flex-wrap gap-3" style={rise(entered, 420)}>
              <Button size="lg" variant="primary" asChild>
                <Link to="/decouvrir">{t('home.ctaDiscover')}</Link>
              </Button>
              <Button size="lg" variant="outline" data-testid="home-open" onClick={openInstrument}>
                {t('home.ctaOpen')}
              </Button>
            </div>
            <p className="home-up text-[15px] text-muted-foreground" style={rise(entered, 500)}>
              {t('home.reassure')}
            </p>
          </div>
          <div
            className="home-up flex min-w-0 flex-[1_1_460px] justify-center"
            style={rise(entered, 240)}
          >
            <HeroInstrument rule={rule} onRule={setRule} />
          </div>
        </div>
        <MethodStrip active={rule} play={entered} />
      </section>

      <CountStory />
      <MomentsTrack />
      <StoriesRegister />
      <BallotBoxFinale onOpen={openInstrument} />

      <footer className="border-t border-border bg-muted">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-8 gap-y-3 px-4 py-6 text-[15px] sm:px-6">
          <nav aria-label={t('home.footMore')} className="flex flex-wrap gap-x-6 gap-y-1">
            {FOOTER_LINKS.map((l) => (
              <Link key={l.href} to={l.href} data-testid={l.testid} className="text-primary">
                {t(l.key)}
              </Link>
            ))}
          </nav>
          <p className="text-muted-foreground">{t('home.licence')}</p>
        </div>
      </footer>
    </div>
  );
};

export default HomePage;
