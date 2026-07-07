import React from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import { usePlaygroundCtx } from '../PlaygroundController';
import { Field, selectCls } from '../playgroundFields';
import Collapsible from '../Collapsible';
import ScenarioInfo from '../ScenarioInfo';
import ElectorateComposer from '../ElectorateComposer';
import { isSpatialSource, type PrefSource } from '../../../stores/useElectionStore';

// Preference sources, grouped: spatial (candidates placed in the space, draggable
// map) vs statistical cultures (no geometry — the map becomes a read-only biplot).
const SPATIAL_SOURCES: PrefSource[] = ['spatial', 'single_peaked'];
const CULTURE_SOURCES: PrefSource[] = [
  'impartial',
  'iac',
  'mallows',
  'urn',
  'plackett_luce',
  'didi',
  'stratification',
];

// The single continuous knob each culture exposes (if any). key = source_params key.
const SOURCE_PARAM: Partial<
  Record<PrefSource, { key: string; min: number; max: number; step: number; def: number }>
> = {
  mallows: { key: 'phi', min: 0.05, max: 1, step: 0.05, def: 0.6 },
  urn: { key: 'alpha', min: 0.1, max: 10, step: 0.1, def: 1 },
  plackett_luce: { key: 'quality', min: 0, max: 5, step: 0.25, def: 1 },
  didi: { key: 'concentration', min: 0.1, max: 10, step: 0.1, def: 1 },
  stratification: { key: 'weight', min: 0.1, max: 0.9, step: 0.1, def: 0.5 },
};

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
    prefParams,
    composed,
    electorate,
  } = usePlaygroundCtx();
  const pointWord = mode === 'leader' ? t('common.candidates') : t('common.parties');
  const param = SOURCE_PARAM[prefSource];

  return (
    <>
      {/* ── Presets: the fast on-ramp ── */}
      <Field label={t('electorate.startLabel')}>
        <div className="flex flex-col gap-2.5">
          {(
            [
              { cat: 'model', labelKey: 'electorate.startModels' },
              { cat: 'election', labelKey: 'electorate.startElections' },
            ] as const
          ).map(({ cat, labelKey }) => (
            <div key={cat}>
              <p className="mb-1 font-mono text-[0.62rem] uppercase tracking-wider text-muted-foreground">
                {t(labelKey)}
              </p>
              <div className="grid grid-cols-2 gap-1.5">
                {presets
                  .filter((p) => p.category === cat)
                  .map((p) => (
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
              disabled={prefSource === 'single_peaked'}
              onChange={(e) => setPlaygroundDeep('space.dims', Number(e.target.value))}
            >
              <option value={1}>{t('electorate.dims1')}</option>
              <option value={2}>{t('electorate.dims2')}</option>
              <option value={3}>{t('electorate.dims3')}</option>
            </select>
          </Field>
          {prefSource === 'single_peaked' && (
            <p className="-mt-1 text-[0.7rem] text-muted-foreground">
              {t('electorate.dimsLockedSingle')}
            </p>
          )}

          {/* Source is a leader/spatial concept: the assembly is computed from
              spatial seat geometry only, so non-spatial cultures don't apply. */}
          {mode === 'leader' && (
            <>
              <Field label={t('electorate.sourceLabel')} htmlFor="pg-source">
                <select
                  id="pg-source"
                  className={selectCls}
                  value={prefSource}
                  onChange={(e) => {
                    const src = e.target.value as PrefSource;
                    // Single-peaked is definitionally 1-D (Black's theorem): lock the
                    // map to one axis so it matches the profile the backend builds.
                    setPlayground(
                      src === 'single_peaked'
                        ? { prefSource: src, space: { ...space, dims: 1 } }
                        : { prefSource: src }
                    );
                  }}
                >
                  <optgroup label={t('electorate.sourceGroupSpatial')}>
                    {SPATIAL_SOURCES.map((s) => (
                      <option key={s} value={s}>
                        {t(`electorate.source_${s}`)}
                      </option>
                    ))}
                  </optgroup>
                  <optgroup label={t('electorate.sourceGroupCulture')}>
                    {CULTURE_SOURCES.map((s) => (
                      <option key={s} value={s}>
                        {t(`electorate.source_${s}`)}
                      </option>
                    ))}
                  </optgroup>
                </select>
              </Field>

              {/* Per-culture knob (Mallows φ, urn α, PL quality, DiDi concentration…). */}
              {param && (
                <Field
                  label={t(`electorate.param_${prefSource}`, {
                    value: (prefParams[param.key] ?? param.def).toFixed(2),
                  })}
                  htmlFor="pg-source-param"
                >
                  <input
                    id="pg-source-param"
                    data-testid="source-param"
                    type="range"
                    min={param.min}
                    max={param.max}
                    step={param.step}
                    value={prefParams[param.key] ?? param.def}
                    onChange={(e) =>
                      setPlayground({
                        prefParams: { ...prefParams, [param.key]: Number(e.target.value) },
                      })
                    }
                  />
                </Field>
              )}

              {/* Non-spatial cultures have no candidate geometry: the map turns into a
              read-only biplot and candidates can't be dragged. State it plainly. */}
              {!isSpatialSource(prefSource) && (
                <p
                  data-testid="nonspatial-note"
                  className="rounded-md border border-border bg-muted/20 px-2.5 py-2 text-[0.7rem] leading-relaxed text-muted-foreground"
                >
                  {t('electorate.nonSpatialNote')}
                </p>
              )}
            </>
          )}

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
