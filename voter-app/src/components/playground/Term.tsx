import React from 'react';
import { Link } from 'react-router';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import InfoPopover from './InfoPopover';
import { GLOSSARY, seeInActionHref } from '../../lib/glossary';
import { track } from '../../lib/analytics';

// Term — the inline glossary affordance. Wrap any piece of jargon:
//   <Term id="condorcet">Condorcet</Term>
// The word gets a dotted underline and the shared ⓘ; the popover gives a
// plain-language gist and a "voir en action" deep-link into the demo that shows
// it. Fails safe: an unknown id renders the children untouched, so a typo can
// never blank out running text.

const Term: React.FC<{ id: string; children?: React.ReactNode; className?: string }> = ({
  id,
  children,
  className,
}) => {
  const { t, i18n } = useTranslation('playground');
  const entry = GLOSSARY[id];
  if (!entry) return <>{children}</>;
  const c = i18n.language.startsWith('fr') ? entry.fr : entry.en;

  return (
    <span className={cn('inline', className)}>
      <span className="border-b border-dotted border-muted-foreground/60">
        {children ?? c.term}
      </span>
      <InfoPopover
        testid={`term-${id}`}
        ariaLabel={c.term}
        onOpen={() => track('term_opened', { id })}
      >
        <p className="text-[0.78rem] font-semibold text-foreground">{c.term}</p>
        <p className="mt-1 text-[0.72rem] leading-snug text-muted-foreground">{c.plain}</p>
        {entry.seeInAction && (
          <Link
            to={seeInActionHref(entry.seeInAction)}
            data-testid={`term-see-${id}`}
            className="mt-2 inline-block text-[0.72rem] font-medium text-primary hover:underline"
          >
            {t('lexique.seeInAction')} →
          </Link>
        )}
      </InfoPopover>
    </span>
  );
};

export default Term;
