import React from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import { usePlayground, useElection } from '../../stores/useElectionStore';
import { ELECTORATE_PRESETS } from '../../stores/useElectionStore';
import { COMMUNITY_PALETTE, type Community } from '../../lib/playgroundElectorate';
import ScenarioInfo from './ScenarioInfo';

// ElectorateComposer (electorate engine) — build a varied electorate as a
// mixture of communities, from textbook shapes to near-real compositions.
// 'simple' falls back to the ideology Gaussian; 'composed' uses the blocs below.
// The composed cloud is what the leader views display + analyse.

const num = (v: string): number => Number(v);

// Round-trip schema for import/export ("données d'entrée"): just the editable
// shape, no UI state. Loose runtime validation keeps a bad paste from crashing.
interface ElectorateDump {
  correlation: number;
  noise: number;
  communities: Community[];
}

function parseDump(text: string): ElectorateDump | null {
  try {
    const o = JSON.parse(text);
    if (!o || !Array.isArray(o.communities) || !o.communities.length) return null;
    const communities: Community[] = o.communities.map((c: Record<string, unknown>, i: number) => ({
      id: typeof c.id === 'string' && c.id ? c.id : `c${i}`,
      label: typeof c.label === 'string' ? c.label : `Bloc ${i + 1}`,
      x: Number(c.x) || 0,
      y: Number(c.y) || 0,
      z: Number(c.z) || 0,
      spread: Number(c.spread) || 0.15,
      weight: Number(c.weight) || 1,
      turnout: c.turnout == null ? 0.85 : Number(c.turnout),
    }));
    return {
      correlation: Number(o.correlation) || 0,
      noise: Number(o.noise) || 0,
      communities,
    };
  } catch {
    return null;
  }
}

const ElectorateComposer: React.FC = () => {
  const { t } = useTranslation('playground');
  const {
    playground,
    setElectorate,
    updateCommunity,
    addCommunity,
    removeCommunity,
    applyElectoratePreset,
  } = usePlayground();
  const { config, setConfig } = useElection();
  const e = playground.electorate;
  const composed = e.mode === 'composed';
  const dims = playground.space.dims;

  const IDEOLOGIES: { value: string; label: string }[] = [
    { value: 'random', label: t('composer.ideoRandom') },
    { value: 'centrist', label: t('composer.ideoCentrist') },
    { value: 'polarized', label: t('composer.ideoPolarized') },
  ];

  const [imp, setImp] = React.useState('');
  const [impErr, setImpErr] = React.useState(false);
  const [copied, setCopied] = React.useState(false);

  const exportJson = () =>
    JSON.stringify(
      { correlation: e.correlation, noise: e.noise, communities: e.communities },
      null,
      2
    );

  const doImport = () => {
    const dump = parseDump(imp);
    if (!dump) {
      setImpErr(true);
      return;
    }
    setImpErr(false);
    setElectorate({
      mode: 'composed',
      correlation: dump.correlation,
      noise: dump.noise,
      communities: dump.communities,
    });
  };

  const doExport = async () => {
    const text = exportJson();
    setImp(text);
    try {
      await navigator.clipboard?.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable — the textarea still holds the JSON */
    }
  };

  return (
    <div data-testid="electorate-composer" className="flex flex-col gap-3">
      {/* Sample size, seed, ideology — apply to BOTH modes (shared with the Lab). */}
      <div className="flex flex-col gap-2 rounded-md border border-border p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {t('composer.sample')}
        </p>
        <label className="flex items-center gap-2 text-xs">
          <span className="w-44 shrink-0 text-muted-foreground">
            {t('composer.numVoters', { n: config.num_voters })}
          </span>
          <input
            data-testid="electorate-num-voters"
            type="range"
            className="min-w-0 flex-1"
            min={10}
            max={1000}
            step={10}
            value={config.num_voters}
            onChange={(ev) => setConfig({ num_voters: num(ev.target.value) })}
          />
        </label>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="w-44 shrink-0 text-muted-foreground">
            {t('composer.seed', { seed: config.seed })}
          </span>
          <input
            data-testid="electorate-seed"
            type="number"
            className="w-24 rounded border border-input bg-background px-1.5 py-0.5"
            min={0}
            value={config.seed}
            onChange={(ev) =>
              setConfig({ seed: Math.max(0, Math.floor(num(ev.target.value) || 0)) })
            }
          />
          <button
            type="button"
            data-testid="electorate-seed-reroll"
            onClick={() => setConfig({ seed: Math.floor(Math.random() * 100000) })}
            className="rounded border border-border px-2 py-0.5 hover:bg-accent"
            title={t('composer.rerollTitle')}
          >
            {t('composer.reroll')}
          </button>
        </div>
        {!composed && (
          <label className="flex items-center gap-2 text-xs">
            <span className="w-44 shrink-0 text-muted-foreground" title={t('composer.ideoTitle')}>
              {t('composer.ideoLabel')}
            </span>
            <select
              data-testid="electorate-ideology"
              className="flex-1 rounded border border-input bg-background px-2 py-1"
              value={config.ideology}
              onChange={(ev) => setConfig({ ideology: ev.target.value })}
            >
              {IDEOLOGIES.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      {/* Mode */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="grid grid-cols-2 overflow-hidden rounded-md border border-border text-xs">
          <button
            type="button"
            data-testid="electorate-mode-simple"
            className={cn('px-3 py-1', !composed && 'bg-primary text-primary-foreground')}
            onClick={() => setElectorate({ mode: 'simple' })}
          >
            {t('composer.modeSimple')}
          </button>
          <button
            type="button"
            data-testid="electorate-mode-composed"
            className={cn('px-3 py-1', composed && 'bg-primary text-primary-foreground')}
            onClick={() => setElectorate({ mode: 'composed' })}
          >
            {t('composer.modeComposed')}
          </button>
        </div>
        <span className="text-xs text-muted-foreground">
          {composed ? t('composer.hintComposed') : t('composer.hintSimple')}
        </span>
      </div>

      {composed && (
        <>
          {/* Presets */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs font-medium text-muted-foreground">
              {t('composer.models')}
            </span>
            {Object.entries(ELECTORATE_PRESETS).map(([id, p]) => (
              <span key={id} className="inline-flex items-center gap-0.5">
                <button
                  type="button"
                  data-testid={`electorate-preset-${id}`}
                  onClick={() => applyElectoratePreset(id)}
                  className="rounded border border-border px-2 py-0.5 text-xs hover:bg-accent"
                >
                  {p.label}
                </button>
                <ScenarioInfo scenario={id} kind="electorate" placement="bottom" />
              </span>
            ))}
          </div>

          {/* Axis correlation */}
          <label className="flex items-center gap-2 text-xs">
            <span className="w-44 shrink-0 text-muted-foreground" title={t('composer.corrTitle')}>
              {t('composer.corr', { val: e.correlation.toFixed(2) })}
            </span>
            <input
              data-testid="electorate-correlation"
              type="range"
              className="min-w-0 flex-1"
              min={-1}
              max={1}
              step={0.05}
              value={e.correlation}
              onChange={(ev) => setElectorate({ correlation: num(ev.target.value) })}
            />
          </label>

          {/* Measurement noise (polling uncertainty) */}
          <label className="flex items-center gap-2 text-xs">
            <span className="w-44 shrink-0 text-muted-foreground" title={t('composer.noiseTitle')}>
              {t('composer.noise', { pct: Math.round(e.noise * 100) })}
            </span>
            <input
              data-testid="electorate-noise"
              type="range"
              className="min-w-0 flex-1"
              min={0}
              max={1}
              step={0.05}
              value={e.noise}
              onChange={(ev) => setElectorate({ noise: num(ev.target.value) })}
            />
          </label>

          {/* Communities — one card per bloc, sliders stacked vertically */}
          <div data-testid="community-list" className="flex flex-col gap-2">
            {e.communities.map((c, i) => (
              <div
                key={c.id}
                data-testid={`community-${c.id}`}
                className="flex flex-col gap-1.5 rounded-md border border-border p-2"
              >
                <div className="flex items-center gap-2">
                  <span
                    className="inline-block h-3 w-3 shrink-0 rounded-full"
                    style={{ background: COMMUNITY_PALETTE[i % COMMUNITY_PALETTE.length] }}
                  />
                  <input
                    className="min-w-0 flex-1 rounded border border-input bg-background px-1 py-0.5 text-xs"
                    value={c.label}
                    onChange={(ev) => updateCommunity(c.id, { label: ev.target.value })}
                  />
                  <button
                    type="button"
                    data-testid={`community-remove-${c.id}`}
                    className="rounded text-muted-foreground hover:text-[#dc3545]"
                    title={t('composer.removeTitle')}
                    onClick={() => removeCommunity(c.id)}
                  >
                    ✕
                  </button>
                </div>
                {([
                  { label: t('composer.colEcon'), key: 'x' as const, min: -1, max: 1, step: 0.05, fmt: (v: number) => v.toFixed(2) },
                  { label: t('composer.colSocial'), key: 'y' as const, min: -1, max: 1, step: 0.05, fmt: (v: number) => v.toFixed(2) },
                  ...(dims >= 3 ? [{ label: t('composer.colZ', { defaultValue: 'Axe 3' }), key: 'z' as const, min: -1, max: 1, step: 0.05, fmt: (v: number) => v.toFixed(2) }] : []),
                  { label: t('composer.colSpread'), key: 'spread' as const, min: 0.05, max: 0.6, step: 0.01, fmt: (v: number) => v.toFixed(2) },
                  { label: t('composer.colSize'), key: 'weight' as const, min: 0, max: 5, step: 0.1, fmt: (v: number) => v.toFixed(1) },
                  { label: t('composer.colTurnout', { defaultValue: 'Participation' }), key: 'turnout' as const, min: 0, max: 1, step: 0.05, fmt: (v: number) => `${Math.round(v * 100)} %` },
                ] as const).map((s) => (
                  <label key={s.key} className="flex items-center gap-2 text-[0.7rem] text-muted-foreground">
                    <span className="w-20 shrink-0 truncate">{s.label}</span>
                    <input
                      data-testid={`community-${s.key}-${c.id}`}
                      type="range"
                      className="min-w-0 flex-1"
                      min={s.min}
                      max={s.max}
                      step={s.step}
                      value={(c as unknown as Record<string, number>)[s.key] ?? 0}
                      onChange={(ev) => updateCommunity(c.id, { [s.key]: num(ev.target.value) })}
                    />
                    <span className="w-10 text-right tabular-nums">
                      {s.fmt((c as unknown as Record<string, number>)[s.key] ?? 0)}
                    </span>
                  </label>
                ))}
              </div>
            ))}

            <button
              type="button"
              data-testid="community-add"
              onClick={addCommunity}
              className="self-start rounded border border-dashed border-border px-2 py-1 text-xs text-muted-foreground hover:bg-accent"
            >
              {t('composer.addCommunity')}
            </button>
          </div>

          {/* Input data: import / export the composition as JSON */}
          <details data-testid="electorate-io" className="rounded-md border border-border">
            <summary className="cursor-pointer px-2.5 py-1.5 text-xs font-medium text-muted-foreground">
              {t('composer.ioSummary')}
            </summary>
            <div className="flex flex-col gap-2 p-2.5 pt-0">
              <textarea
                data-testid="electorate-json"
                className="h-28 w-full rounded border border-input bg-background p-2 font-mono text-[0.68rem]"
                placeholder='{ "correlation": 0, "noise": 0, "communities": [ … ] }'
                value={imp}
                onChange={(ev) => {
                  setImp(ev.target.value);
                  setImpErr(false);
                }}
              />
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  data-testid="electorate-import"
                  onClick={doImport}
                  className="rounded border border-border px-2 py-0.5 text-xs hover:bg-accent"
                >
                  {t('composer.import')}
                </button>
                <button
                  type="button"
                  data-testid="electorate-export"
                  onClick={doExport}
                  className="rounded border border-border px-2 py-0.5 text-xs hover:bg-accent"
                >
                  {copied ? t('composer.copied') : t('composer.export')}
                </button>
                {impErr && (
                  <span
                    data-testid="electorate-json-error"
                    className="text-[0.7rem] text-[#dc3545]"
                  >
                    {t('composer.jsonError')}
                  </span>
                )}
              </div>
            </div>
          </details>

          <p className="text-[0.68rem] text-muted-foreground">{t('composer.footer')}</p>
        </>
      )}
    </div>
  );
};

export default ElectorateComposer;
