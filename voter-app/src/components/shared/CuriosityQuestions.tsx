import React from 'react';
import { Link } from 'react-router';
import { useTranslation } from 'react-i18next';
import { ArrowRight } from 'lucide-react';
import { CURIOSITY_QUESTIONS } from '../../lib/curiosityQuestions';

// CuriosityQuestions — entry by curiosity, not by mechanism. A self-contained
// section: each plain wondering links to the story that answers it. Reuses the
// existing /playground?story= deep-link, so no new player and no new state.

const CuriosityQuestions: React.FC = () => {
  const { t } = useTranslation('playground');
  return (
    <div>
      <p className="font-mono text-[0.7rem] uppercase tracking-[0.22em] text-primary">
        {t('curiosity.kicker')}
      </p>
      <h2 className="mt-1 font-display text-2xl font-bold tracking-tight">
        {t('curiosity.title')}
      </h2>
      <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
        {t('curiosity.sub')}
      </p>

      <ul data-testid="curiosity-questions" className="mt-5 grid grid-cols-1 gap-2 sm:grid-cols-2">
        {CURIOSITY_QUESTIONS.map((q) => (
          <li key={q.id}>
            <Link
              to={`/playground?story=${q.story}`}
              data-testid={`curiosity-${q.id}`}
              className="group flex h-full items-start justify-between gap-3 rounded-lg border border-border bg-card px-3 py-2.5 text-left transition-colors hover:border-primary/40 hover:bg-accent/40"
            >
              <span className="text-sm font-medium leading-snug group-hover:text-primary">
                {t(`curiosity.q.${q.id}`)}
              </span>
              <ArrowRight
                aria-hidden
                className="mt-0.5 h-4 w-4 shrink-0 text-primary transition-transform group-hover:translate-x-0.5"
              />
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default CuriosityQuestions;
