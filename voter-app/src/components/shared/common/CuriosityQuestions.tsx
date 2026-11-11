import React from 'react';
import { Link } from 'react-router';
import { useTranslation } from 'react-i18next';
import { ArrowRight } from 'lucide-react';
import { CURIOSITY_QUESTIONS } from '../../../lib/curiosityQuestions';

// CuriosityQuestions — entry by curiosity, not by mechanism. A self-contained
// section: each plain wondering links to the story that answers it. Reuses the
// existing /playground?story= deep-link, so no new player and no new state.

const CuriosityQuestions: React.FC = () => {
  const { t } = useTranslation('playground');
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-8 gap-y-2">
        <h2 className="font-display text-[44px] leading-none font-extrabold sm:text-[56px]">
          {t('curiosity.title')}
        </h2>
        <p className="max-w-md text-base text-muted-foreground">{t('curiosity.sub')}</p>
      </div>

      {/* A register, like the homepage's stories: one ruled line per question. */}
      <ul
        data-testid="curiosity-questions"
        className="grid grid-cols-1 border-t-2 border-foreground sm:grid-cols-2 sm:gap-x-10"
      >
        {CURIOSITY_QUESTIONS.map((q) => (
          <li key={q.id} className="border-b border-border">
            <Link
              to={`/playground?story=${q.story}`}
              data-testid={`curiosity-${q.id}`}
              className="group flex h-full items-center justify-between gap-4 px-1 py-4 text-foreground no-underline"
            >
              <span className="text-[17px] leading-snug font-semibold transition-transform duration-[240ms] ease-[cubic-bezier(.2,.7,.2,1)] motion-reduce:transition-none group-hover:translate-x-1.5 group-focus-visible:translate-x-1.5">
                {t(`curiosity.q.${q.id}`)}
              </span>
              <ArrowRight
                aria-hidden
                className="h-4 w-4 shrink-0 text-primary transition-transform duration-[240ms] group-hover:translate-x-1 motion-reduce:transition-none"
              />
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default CuriosityQuestions;
