import React from 'react';
import { useTranslation } from 'react-i18next';
import { usePlaygroundCtx } from '../PlaygroundController';
import { Field, selectCls } from '../playgroundFields';
import { type Rule } from '../../../lib/playgroundVoting';
import { LEADER_RULES } from '../../../lib/scorecard';

interface RuleFamily {
  key: string;
  rules: Rule[];
}

const FAMILIES: RuleFamily[] = [
  { key: 'majoritarian', rules: ['plurality', 'two_round', 'irv', 'coombs', 'anti_plurality'] },
  { key: 'positional', rules: ['borda', 'bucklin', 'nanson', 'baldwin', 'dowdall'] },
  {
    key: 'condorcet',
    rules: ['condorcet', 'minimax', 'schulze', 'ranked_pairs', 'kemeny', 'black'],
  },
  {
    key: 'cardinal',
    rules: ['approval', 'score', 'star', 'majority_judgment', 'cumulative', 'maximin', 'nash'],
  },
  { key: 'other', rules: ['random_ballot'] },
];

const MethodMoment: React.FC = () => {
  const { t } = useTranslation('playground');
  const { setPlaygroundDeep, mode, assembly, enabledRules, setEnabledRules } = usePlaygroundCtx();

  const toggle = (rule: Rule) =>
    setEnabledRules((prev) => {
      const next = new Set(prev);
      if (next.has(rule)) {
        if (next.size > 1) next.delete(rule);
      } else {
        next.add(rule);
      }
      return next;
    });

  const toggleFamily = (rules: Rule[]) =>
    setEnabledRules((prev) => {
      const allOn = rules.every((r) => prev.has(r));
      const next = new Set(prev);
      for (const r of rules) {
        if (allOn) {
          if (next.size > 1) next.delete(r);
        } else {
          next.add(r);
        }
      }
      return next;
    });

  const selectAll = () => setEnabledRules(new Set(LEADER_RULES));

  return (
    <>
      <p className="text-xs text-muted-foreground">{t('method.multiSelectNote')}</p>

      <div className="flex flex-col gap-3">
        {FAMILIES.map((fam) => (
          <fieldset key={fam.key} className="rounded-md border border-border p-2.5">
            <legend className="px-1 text-[0.7rem] font-semibold uppercase tracking-wide text-muted-foreground">
              <label className="flex cursor-pointer items-center gap-1.5">
                <input
                  type="checkbox"
                  checked={fam.rules.every((r) => enabledRules.has(r))}
                  ref={(el) => {
                    if (el)
                      el.indeterminate =
                        fam.rules.some((r) => enabledRules.has(r)) &&
                        !fam.rules.every((r) => enabledRules.has(r));
                  }}
                  onChange={() => toggleFamily(fam.rules)}
                  className="accent-primary"
                />
                {t(`method.family.${fam.key}`)}
              </label>
            </legend>
            <div className="mt-1 flex flex-col gap-0.5">
              {fam.rules.map((r) => (
                <label
                  key={r}
                  data-testid={`rule-check-${r}`}
                  className="flex cursor-pointer items-center gap-2 rounded px-1 py-0.5 text-xs hover:bg-accent/50"
                >
                  <input
                    type="checkbox"
                    checked={enabledRules.has(r)}
                    onChange={() => toggle(r)}
                    className="accent-primary"
                  />
                  {t(`rules.${r}`)}
                </label>
              ))}
            </div>
          </fieldset>
        ))}
      </div>

      <div className="flex items-center gap-2 text-xs">
        <button
          type="button"
          data-testid="rules-select-all"
          onClick={selectAll}
          className="rounded border border-border px-2 py-0.5 text-muted-foreground hover:bg-accent"
        >
          {t('method.selectAll')}
        </button>
        <span className="text-muted-foreground">
          {t('method.enabledCount', { count: enabledRules.size, total: LEADER_RULES.length })}
        </span>
      </div>

      {mode === 'parliament' && (
        <div className="flex flex-col gap-3 rounded-md border border-border p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {t('method.assemblyTitle')}
          </p>
          <Field label={t('method.structureLabel')} htmlFor="pg-structure">
            <select
              id="pg-structure"
              className={selectCls}
              value={assembly.structure}
              onChange={(e) => setPlaygroundDeep('assembly.structure', e.target.value)}
            >
              <option value="pr">{t('method.structurePr')}</option>
              <option value="fptp">{t('method.structureFptp')}</option>
              <option value="mmp">{t('method.structureMmp')}</option>
            </select>
          </Field>
          <Field label={t('method.seatsLabel', { n: assembly.seats })} htmlFor="pg-seats">
            <input
              id="pg-seats"
              type="range"
              min={10}
              max={500}
              step={10}
              value={assembly.seats}
              onChange={(e) => setPlaygroundDeep('assembly.seats', Number(e.target.value))}
            />
          </Field>
        </div>
      )}
    </>
  );
};

export default MethodMoment;
