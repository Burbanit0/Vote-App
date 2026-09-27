import React from 'react';
import { Link } from 'react-router';
import { useTranslation } from 'react-i18next';
import { GLOSSARY, seeInActionHref } from '../../lib/glossary';
import { track } from '../../lib/analytics';

// LexiquePanel — the browsable master list of every notion the app uses, with a
// search box and, for each term, the same "voir en action" deep-link the inline
// <Term> popover offers. The Laboratoire anchor for "I just want to look
// something up"; the inline <Term> handles "define this word right here".

const LexiquePanel: React.FC = () => {
  const { t, i18n } = useTranslation('playground');
  const fr = i18n.language.startsWith('fr');
  const [q, setQ] = React.useState('');

  const rows = React.useMemo(() => {
    const all = Object.entries(GLOSSARY).map(([id, e]) => ({
      id,
      c: fr ? e.fr : e.en,
      see: e.seeInAction,
    }));
    all.sort((a, b) => a.c.term.localeCompare(b.c.term, fr ? 'fr' : 'en'));
    const needle = q.trim().toLowerCase();
    if (!needle) return all;
    return all.filter(({ c }) => `${c.term} ${c.short} ${c.plain}`.toLowerCase().includes(needle));
  }, [q, fr]);

  return (
    <div data-testid="lexique-panel" className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">{t('lexique.intro')}</p>

      <input
        data-testid="lexique-search"
        type="search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder={t('lexique.search')}
        aria-label={t('lexique.search')}
        className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
      />

      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t('lexique.empty')}</p>
      ) : (
        <ul className="flex flex-col divide-y divide-border">
          {rows.map(({ id, c, see }) => (
            <li key={id} className="py-3">
              <p className="text-sm font-semibold text-foreground">{c.term}</p>
              <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{c.plain}</p>
              {see && (
                <Link
                  to={seeInActionHref(see)}
                  data-testid={`lexique-see-${id}`}
                  onClick={() => track('term_opened', { id, from: 'lexique' })}
                  className="mt-1.5 inline-block text-xs font-medium text-primary hover:underline"
                >
                  {t('lexique.seeInAction')} →
                </Link>
              )}
            </li>
          ))}
        </ul>
      )}

      <p className="text-xs text-muted-foreground">
        {t('lexique.count', { n: Object.keys(GLOSSARY).length })}
      </p>
    </div>
  );
};

export default LexiquePanel;
