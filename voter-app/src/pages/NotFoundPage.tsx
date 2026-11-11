/**
 * NotFoundPage — catch-all 404 for unknown / removed routes (e.g. the retired
 * /campaign, /blank-contagion, /constitutional-crisis paths). A spoiled ballot: the
 * slip drops in with the page's address printed on it, and is stamped void.
 */
import React from 'react';
import { Link } from 'react-router';
import { useTranslation } from 'react-i18next';
import { ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { RiseWords, Slip } from '@/components/ui/slip';
import { useMetaTags } from '../hooks/useMetaTags';

const NotFoundPage: React.FC = () => {
  const { t } = useTranslation();
  useMetaTags({ title: '404 — Vote Lab', description: t('notFound.message') });

  return (
    <div
      data-style="tailwind"
      className="mx-auto flex min-h-[calc(100dvh-49px)] max-w-6xl flex-wrap items-center gap-x-16 gap-y-10 px-4 py-14 sm:px-6"
    >
      <div className="flex min-w-0 flex-[1_1_480px] flex-col gap-5">
        <h1 className="font-display text-[clamp(44px,5.4vw,80px)] leading-[0.92] font-extrabold">
          <RiseWords text={t('notFound.title')} delay={80} />
        </h1>
        <p
          className="home-up max-w-[34rem] text-xl text-muted-foreground"
          style={{ animationDelay: '240ms' }}
        >
          {t('notFound.message')}
        </p>
        <div className="home-up flex flex-wrap gap-3" style={{ animationDelay: '320ms' }}>
          <Button size="lg" variant="primary" asChild className="px-5">
            <Link to="/">{t('notFound.home')}</Link>
          </Button>
          <Button size="lg" variant="outline" asChild>
            <Link to="/playground">
              {t('notFound.playground')} <ArrowRight aria-hidden className="h-4 w-4" />
            </Link>
          </Button>
        </div>
      </div>

      {/* The spoiled ballot: it drops in, then the stamp lands with its ink bleed. */}
      <div
        className="ballot-drop mx-auto w-full max-w-[240px] min-w-0 sm:max-w-none lg:mx-0 lg:flex-[0_1_340px]"
        style={{ '--tilt': '-4deg', animationDelay: '200ms' } as React.CSSProperties}
      >
        <Slip fold={32} className="relative flex aspect-[4/5] items-center justify-center">
          <span className="font-display text-[96px] leading-none sm:text-[120px] font-extrabold text-muted-foreground/40">
            404
          </span>
          <span className="absolute inset-0 flex items-center justify-center">
            <span className="relative">
              <span
                aria-hidden="true"
                className="home-bleed absolute inset-0 rounded-md border-4 border-ballot-stamp"
                style={{ animationDelay: '1.1s' }}
              />
              <span
                className="home-stamp block rounded-md border-4 border-ballot-stamp bg-card/85 px-5 pt-1 pb-1.5 font-display text-[44px] leading-none font-extrabold tracking-[0.08em] sm:text-[56px] text-ballot-stamp uppercase"
                style={{ animationDelay: '0.9s' }}
              >
                {t('notFound.stamp')}
              </span>
            </span>
          </span>
        </Slip>
      </div>
    </div>
  );
};

export default NotFoundPage;
