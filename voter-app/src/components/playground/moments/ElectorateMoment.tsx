import React from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import { usePlaygroundCtx } from '../PlaygroundController';
import { Field, selectCls } from '../playgroundFields';
import Collapsible from '../Collapsible';
import ScenarioInfo from '../ScenarioInfo';
import ElectorateComposer from '../ElectorateComposer';

const ElectorateMoment: React.FC = () => {
  const { t } = useTranslation('playground');
  const {
    config,
    setConfig,
    setPlayground,
    setPlaygroundDeep,
    applyPreset,
    presets,
    mode,
    space,
    prefSource,
    composed,
    electorate,
  } = usePlaygroundCtx();
  const pointWord = mode === 'leader' ? t('common.candidates') : t('common.parties');

  return (
    <>
      {/* ── Presets: the fast on-ramp ── */}
      <Field label={t('electorate.startLabel')}>
        <div className="grid grid-cols-2 gap-1.5">
          {presets.map((p) => (
            <div key={p.id} className="flex items-center gap-1">
              <button
                data-testid={`preset-${p.id}`}
                type="button"
                onClick={() => applyPreset(p.id)}
                className={cn(
                  'flex-1 rounded-md border border-border px-2 py-1.5 text-left text-xs transition-colors hover:bg-accent hover:text-accent-foreground'
                )}
                title={t(`presets.${p.id}.desc`, { defaultValue: p.description })}
              >
                {t(`presets.${p.id}.label`, { defaultValue: p.label })}
              </button>
              <ScenarioInfo scenario={p.id} />
            </div>
          ))}
        </div>
      </Field>

      {/* ── Summary ── */}
      <div className="rounded-md bg-muted/40 px-2.5 py-2 text-xs text-muted-foreground">
        {t('electorate.summary', {
          points: config.candidates.length,
          pointWord,
          voters: config.num_voters,
          ideology: config.ideology,
        })}
      </div>

      {/* ── Composer (core controls) ── */}
      <Collapsible
        title={t('electorate.composeTitle')}
        subtitle={
          composed
            ? t('electorate.composeSubComposed', { count: electorate.communities.length })
            : t('electorate.composeSubSimple')
        }
        testid="module-electorate"
      >
        <ElectorateComposer />
      </Collapsible>

      {/* ── Advanced settings (dims, source, valence only) ── */}
      <Collapsible
        title={t('electorate.advancedTitle')}
        subtitle={t('electorate.advancedSubtitle')}
        testid="electorate-advanced"
      >
        <div className="flex flex-col gap-3">
          <Field label={t('electorate.dimsLabel')} htmlFor="pg-dims">
            <select
              id="pg-dims"
              className={selectCls}
              value={space.dims}
              onChange={(e) => setPlaygroundDeep('space.dims', Number(e.target.value))}
            >
              <option value={1}>{t('electorate.dims1')}</option>
              <option value={2}>{t('electorate.dims2')}</option>
              <option value={3}>{t('electorate.dims3')}</option>
            </select>
          </Field>

          <Field label={t('electorate.sourceLabel')} htmlFor="pg-source">
            <select
              id="pg-source"
              className={selectCls}
              value={prefSource}
              onChange={(e) => setPlayground({ prefSource: e.target.value as typeof prefSource })}
            >
              <option value="spatial">{t('electorate.sourceSpatial')}</option>
              <option value="impartial">{t('electorate.sourceImpartial')}</option>
              <option value="mallows">{t('electorate.sourceMallows')}</option>
              <option value="urn">{t('electorate.sourceUrn')}</option>
              <option value="handcrafted">{t('electorate.sourceHandcrafted')}</option>
            </select>
          </Field>

          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={space.valenceEnabled}
                onChange={(e) => setPlaygroundDeep('space.valenceEnabled', e.target.checked)}
              />
              {t('electorate.valence')}
            </label>
            {space.valenceEnabled && mode === 'leader' && (
              <div
                data-testid="valence-editor"
                className="flex flex-col gap-1.5 rounded-md border border-border p-2.5"
              >
                <p className="text-[0.7rem] text-muted-foreground">{t('electorate.valenceHint')}</p>
                {config.candidates.map((c, i) => (
                  <label key={c.name} className="flex items-center gap-2 text-xs">
                    <span className="w-20 shrink-0 truncate text-muted-foreground">{c.name}</span>
                    <input
                      data-testid={`valence-${i}`}
                      type="range"
                      className="min-w-0 flex-1"
                      min={-1}
                      max={1}
                      step={0.05}
                      value={c.valence ?? 0}
                      onChange={(e) =>
                        setConfig({
                          candidates: config.candidates.map((cc, j) =>
                            j === i ? { ...cc, valence: Number(e.target.value) } : cc
                          ),
                        })
                      }
                    />
                    <span className="w-9 text-right tabular-nums text-muted-foreground">
                      {(c.valence ?? 0).toFixed(2)}
                    </span>
                  </label>
                ))}
              </div>
            )}
          </div>
        </div>
      </Collapsible>
    </>
  );
};

export default ElectorateMoment;
