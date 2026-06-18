import React, { useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import { getMethodInfo, methodContextNote, type Lang, type MethodContext } from '@/lib/methodInfo';

// MethodInfo — a subtle ⓘ affordance that reveals a voting method's explanation
// on click (mirrors MetricTooltip: a button + an absolutely-positioned popover
// that closes on outside click, keyboard-accessible). Renders nothing if the
// method id has no registry entry, so it's safe to drop next to any label.
//
// The popover is bilingual (picks fr/en from i18next) and context-aware: for the
// Condorcet family it appends a live note when no Condorcet winner exists.

interface Props {
  /** Method id — canonical or a backend/result-table alias (copeland, star_voting…). */
  method: string;
  /** Live state so the card can react (e.g. Condorcet cycle). */
  context?: MethodContext;
  placement?: 'top' | 'bottom' | 'left' | 'right';
  className?: string;
}

const POS: Record<NonNullable<Props['placement']>, string> = {
  top: 'bottom-full left-1/2 mb-2 -translate-x-1/2',
  bottom: 'top-full left-1/2 mt-2 -translate-x-1/2',
  left: 'right-full top-1/2 mr-2 -translate-y-1/2',
  right: 'left-full top-1/2 ml-2 -translate-y-1/2',
};

const Line: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <p className="mt-1.5 text-[0.72rem] leading-snug">
    <span className="font-semibold text-foreground">{label} </span>
    <span className="text-muted-foreground">{children}</span>
  </p>
);

const MethodInfo: React.FC<Props> = ({ method, context = {}, placement = 'top', className }) => {
  const { i18n } = useTranslation();
  const lang: Lang = i18n.language?.startsWith('en') ? 'en' : 'fr';
  const [show, setShow] = React.useState(false);
  const wrapRef = useRef<HTMLSpanElement>(null);

  const entry = getMethodInfo(method);

  const handleClickOutside = React.useCallback((e: MouseEvent) => {
    if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setShow(false);
  }, []);
  React.useEffect(() => {
    if (show) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [show, handleClickOutside]);

  // Unknown method id → render nothing (safe to drop anywhere).
  if (!entry) return null;
  const c = entry[lang];
  const note = methodContextNote(method, lang, context);

  const labels =
    lang === 'en'
      ? {
          how: 'How:',
          strength: 'Strength:',
          weakness: 'Weakness:',
          criterion: 'Criterion:',
          example: 'Example:',
        }
      : {
          how: 'Principe :',
          strength: 'Force :',
          weakness: 'Faille :',
          criterion: 'Critère :',
          example: 'Exemple :',
        };

  return (
    <span ref={wrapRef} className="relative inline-block" data-style="tailwind">
      <button
        type="button"
        className={cn(
          'inline-flex shrink-0 cursor-pointer items-center border-0 bg-transparent px-0.5 align-middle leading-none text-muted-foreground hover:text-foreground',
          className
        )}
        style={{ fontSize: '0.72rem' }}
        aria-label={`${lang === 'en' ? 'About' : 'À propos de'} ${c.name}`}
        aria-expanded={show}
        onClick={(e) => {
          e.stopPropagation();
          setShow((s) => !s);
        }}
        data-testid={`method-info-${method}`}
      >
        ⓘ
      </button>

      {show && (
        <div
          role="tooltip"
          data-testid={`method-pop-${method}`}
          className={cn(
            'absolute z-[1060] w-[300px] max-w-[300px] rounded-md border border-border bg-popover p-3 text-popover-foreground shadow-lg',
            POS[placement]
          )}
        >
          <p className="text-sm font-bold">{c.name}</p>
          <p className="mt-1 text-[0.74rem] leading-snug text-muted-foreground">{c.summary}</p>
          <Line label={labels.how}>{c.how}</Line>
          <Line label={labels.strength}>{c.strength}</Line>
          <Line label={labels.weakness}>{c.weakness}</Line>
          <Line label={labels.criterion}>{c.criterion}</Line>
          <Line label={labels.example}>{c.example}</Line>
          {note && (
            <p className="mt-2 rounded bg-amber-500/10 px-2 py-1 text-[0.7rem] leading-snug text-amber-700 dark:text-amber-400">
              ⚡ {note}
            </p>
          )}
        </div>
      )}
    </span>
  );
};

export default MethodInfo;
