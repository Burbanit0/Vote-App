import React from 'react';
import { useTranslation } from 'react-i18next';
import { POLITY_LENSES, type PolityLens } from '../../lib/polity/urlState';
import { usePolityCtx } from './PolityController';

const LENS_KEYS: Record<PolityLens, string> = {
  activity: 'map.lensActivity',
  act: 'map.lensAct',
  vote: 'map.lensVote',
  candidacy: 'map.lensCandidacy',
  party: 'map.lensParty',
};

/** How the map colours and shapes citizens. */
const LensSelector: React.FC = () => {
  const { t } = useTranslation('polity');
  const { overview, lens, setLens } = usePolityCtx();
  const noBallots = overview?.vote_coverage === 'none';
  return (
    <div
      role="radiogroup"
      aria-label={t('map.lensLabel')}
      className="flex flex-wrap items-center gap-1 text-xs"
    >
      <span className="text-muted-foreground">{t('map.lensLabel')}</span>
      {POLITY_LENSES.map((id) => (
        <button
          key={id}
          type="button"
          role="radio"
          aria-checked={lens === id}
          data-testid={`polity-lens-${id}`}
          // A run that journals no ballot has nothing to show under the vote lens.
          disabled={id === 'vote' && noBallots}
          title={id === 'vote' && noBallots ? t('map.noVotesNote') : undefined}
          className={`rounded border px-2 py-0.5 disabled:opacity-40 ${
            lens === id ? 'border-primary text-primary' : 'border-border text-muted-foreground'
          }`}
          onClick={() => setLens(id)}
        >
          {t(LENS_KEYS[id])}
        </button>
      ))}
    </div>
  );
};

export default LensSelector;
