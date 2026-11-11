import React, { useEffect, useRef } from 'react';
import { Link } from 'react-router';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { useReducedMotion } from '@/hooks/useMediaQuery';
import { useFrameLoop } from '@/hooks/useFrameLoop';
import { dropPose, finaleDuration, finaleHeap } from '@/lib/home/motion';

// BallotBoxFinale — "Your turn": the page's last call to open the instrument, beside a
// glass ballot box that fills with 100 ballots once, the first time it comes into view.

const HEAP = finaleHeap();
const END = finaleDuration(HEAP);

function drawHeap(els: (SVGRectElement | null)[], t: number) {
  HEAP.forEach((d, i) => {
    const p = dropPose(d, t);
    els[i]!.setAttribute(
      'transform',
      `translate(${p.x.toFixed(1)} ${p.y.toFixed(1)}) rotate(${p.rot.toFixed(1)})`
    );
    els[i]!.setAttribute('opacity', String(p.o));
  });
}

const BallotBoxFinale: React.FC<{ onOpen: () => void }> = ({ onOpen }) => {
  const { t } = useTranslation();
  const reduce = useReducedMotion();
  const box = useRef<SVGSVGElement>(null);
  const ballots = useRef<(SVGRectElement | null)[]>([]);
  const start = useRef(0);

  const kick = useFrameLoop((now) => {
    const t = now - start.current;
    drawHeap(ballots.current, t);
    return t < END;
  });

  useEffect(() => {
    const io = new IntersectionObserver(
      ([e]) => {
        if (!e.isIntersecting) return;
        io.disconnect();
        if (reduce) {
          drawHeap(ballots.current, END);
          return;
        }
        start.current = performance.now();
        kick();
      },
      { threshold: 0.35 }
    );
    io.observe(box.current!);
    return () => io.disconnect();
  }, [reduce, kick]);

  return (
    <section
      id="home-turn"
      data-testid="home-turn"
      aria-labelledby="home-turn-title"
      className="border-t border-border bg-muted"
    >
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-16 gap-y-10 px-4 py-20 sm:px-6">
        <div className="flex min-w-0 flex-[1_1_420px] flex-col gap-5">
          <h2
            id="home-turn-title"
            className="font-display text-[64px] leading-[0.9] font-extrabold lg:text-[112px]"
          >
            {t('home.turnTitle')}
          </h2>
          <p className="max-w-[30rem] text-xl text-muted-foreground">{t('home.turnLede')}</p>
          <div className="flex flex-wrap gap-3">
            <Button size="lg" variant="primary" onClick={onOpen}>
              {t('home.ctaOpen')}
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link to="/decouvrir">{t('home.ctaDiscover')}</Link>
            </Button>
          </div>
          <p className="text-base text-muted-foreground">
            <Link to="/laboratoire" className="font-bold text-primary">
              {t('home.turnLab')}
            </Link>
          </p>
        </div>
        <svg
          ref={box}
          viewBox="0 0 420 300"
          role="img"
          aria-label={t('home.boxLabel', { n: HEAP.length })}
          className="block h-auto max-w-[480px] min-w-0 flex-[1_1_380px]"
        >
          <rect
            x="70"
            y="96"
            width="280"
            height="186"
            rx="6"
            className="fill-envelope"
            opacity="0.7"
          />
          {HEAP.map((_, i) => (
            <rect
              key={i}
              ref={(el) => {
                ballots.current[i] = el;
              }}
              x="-6"
              y="-3.5"
              width="12"
              height="7"
              rx="1"
              fill="#FFFFFF"
              stroke="#18212F"
              strokeWidth={0.8}
              opacity="0"
            />
          ))}
          <path
            d="M70 96V276a6 6 0 0 0 6 6H344a6 6 0 0 0 6-6V96"
            fill="none"
            className="stroke-primary"
            strokeWidth={2}
          />
          <rect x="60" y="88" width="120" height="10" rx="2" className="fill-foreground" />
          <rect x="240" y="88" width="120" height="10" rx="2" className="fill-foreground" />
        </svg>
      </div>
    </section>
  );
};

export default BallotBoxFinale;
