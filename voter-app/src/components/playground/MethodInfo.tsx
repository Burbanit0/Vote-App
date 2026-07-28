import React from 'react';
import { useTranslation } from 'react-i18next';
import InfoPopover, { InfoLine } from './InfoPopover';
import {
  getMethodInfo,
  methodAnalogy,
  methodContextNote,
  type Lang,
  type MethodContext,
} from '@/lib/methodInfo';

// MethodInfo — a subtle ⓘ that reveals a voting method's explanation on click.
// Renders nothing if the method id has no registry entry, so it's safe to drop
// next to any label. Bilingual (fr/en from i18next) and context-aware: the
// Condorcet family appends a live note when no Condorcet winner exists.
// Test hooks: `info-<method>` (trigger) and `pop-<method>` (popover).

interface Props {
  /** Method id — canonical or a backend/result-table alias (copeland, star_voting…). */
  method: string;
  /** Live state so the card can react (e.g. Condorcet cycle). */
  context?: MethodContext;
  placement?: 'top' | 'bottom' | 'left' | 'right';
  className?: string;
}

const MethodInfo: React.FC<Props> = ({ method, context = {}, placement = 'top', className }) => {
  const { i18n } = useTranslation();
  const lang: Lang = i18n.language?.startsWith('en') ? 'en' : 'fr';

  const entry = getMethodInfo(method);
  if (!entry) return null; // unknown id → render nothing

  const c = entry[lang];
  const note = methodContextNote(method, lang, context);
  const analogy = methodAnalogy(method, lang);
  const labels =
    lang === 'en'
      ? {
          analogy: 'Like real life:',
          how: 'How:',
          strength: 'Strength:',
          weakness: 'Weakness:',
          criterion: 'Criterion:',
          example: 'Example:',
        }
      : {
          analogy: 'Au quotidien :',
          how: 'Principe :',
          strength: 'Force :',
          weakness: 'Faille :',
          criterion: 'Critère :',
          example: 'Exemple :',
        };

  return (
    <InfoPopover
      testid={method}
      placement={placement}
      className={className}
      ariaLabel={`${lang === 'en' ? 'About' : 'À propos de'} ${c.name}`}
    >
      <p className="text-sm font-bold">{c.name}</p>
      <p className="mt-1 text-[0.74rem] leading-snug text-muted-foreground">{c.summary}</p>
      {analogy && <InfoLine label={labels.analogy}>{analogy}</InfoLine>}
      <InfoLine label={labels.how}>{c.how}</InfoLine>
      <InfoLine label={labels.strength}>{c.strength}</InfoLine>
      <InfoLine label={labels.weakness}>{c.weakness}</InfoLine>
      <InfoLine label={labels.criterion}>{c.criterion}</InfoLine>
      <InfoLine label={labels.example}>{c.example}</InfoLine>
      {note && (
        <p className="mt-2 rounded bg-amber-500/10 px-2 py-1 text-[0.7rem] leading-snug text-amber-700 dark:text-amber-400">
          ⚡ {note}
        </p>
      )}
    </InfoPopover>
  );
};

export default MethodInfo;
