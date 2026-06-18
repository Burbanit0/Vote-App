import React from 'react';
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
    { value: 'random', label: 'Aléatoire (large)' },
    { value: 'centrist', label: 'Centriste (resserré)' },
    { value: 'polarized', label: 'Polarisé (deux camps)' },
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
          Échantillon
        </p>
        <label className="flex items-center gap-2 text-xs">
          <span className="w-44 shrink-0 text-muted-foreground">
            Nombre d’électeurs : {config.num_voters}
          </span>
          <input
            data-testid="electorate-num-voters"
            type="range"
            className="flex-1"
            min={10}
            max={1000}
            step={10}
            value={config.num_voters}
            onChange={(ev) => setConfig({ num_voters: num(ev.target.value) })}
          />
        </label>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="w-44 shrink-0 text-muted-foreground">Graine : {config.seed}</span>
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
            title="Tire un nouvel électorat (mêmes réglages, autre échantillon)."
          >
            🎲 Re-tirer
          </button>
        </div>
        {!composed && (
          <label className="flex items-center gap-2 text-xs">
            <span
              className="w-44 shrink-0 text-muted-foreground"
              title="Forme du nuage gaussien en mode simple (le mode composé la remplace par les communautés)."
            >
              Idéologie (mode simple)
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
            Simple (gaussien)
          </button>
          <button
            type="button"
            data-testid="electorate-mode-composed"
            className={cn('px-3 py-1', composed && 'bg-primary text-primary-foreground')}
            onClick={() => setElectorate({ mode: 'composed' })}
          >
            Composé (communautés)
          </button>
        </div>
        <span className="text-xs text-muted-foreground">
          {composed
            ? 'Mélange de blocs — édite chaque communauté ci-dessous.'
            : 'Nuage idéologique unique (réglage « idéologie »).'}
        </span>
      </div>

      {composed && (
        <>
          {/* Presets */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs font-medium text-muted-foreground">Modèles :</span>
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
            <span
              className="w-44 shrink-0 text-muted-foreground"
              title="Couple l'axe sociétal à l'axe économique."
            >
              Corrélation des axes : {e.correlation.toFixed(2)}
            </span>
            <input
              data-testid="electorate-correlation"
              type="range"
              className="flex-1"
              min={-1}
              max={1}
              step={0.05}
              value={e.correlation}
              onChange={(ev) => setElectorate({ correlation: num(ev.target.value) })}
            />
          </label>

          {/* Measurement noise (polling uncertainty) */}
          <label className="flex items-center gap-2 text-xs">
            <span
              className="w-44 shrink-0 text-muted-foreground"
              title="Flou de mesure global ajouté à toutes les positions — l'incertitude d'un sondage, distincte de la dispersion réelle des blocs."
            >
              Bruit de mesure (sondage) : {Math.round(e.noise * 100)} %
            </span>
            <input
              data-testid="electorate-noise"
              type="range"
              className="flex-1"
              min={0}
              max={1}
              step={0.05}
              value={e.noise}
              onChange={(ev) => setElectorate({ noise: num(ev.target.value) })}
            />
          </label>

          {/* Communities table */}
          <div data-testid="community-list" className="flex flex-col gap-2">
            <div className="grid grid-cols-[1.6rem_8rem_1fr_1fr_1fr_1fr_1.4rem] items-center gap-1 text-[0.62rem] uppercase tracking-wide text-muted-foreground">
              <span />
              <span>Communauté</span>
              <span>Écon. (x)</span>
              <span>Sociétal (y)</span>
              <span>Dispersion</span>
              <span>Taille</span>
              <span />
            </div>
            {e.communities.map((c, i) => (
              <div
                key={c.id}
                data-testid={`community-${c.id}`}
                className="grid grid-cols-[1.6rem_8rem_1fr_1fr_1fr_1fr_1.4rem] items-center gap-1 text-xs"
              >
                <span
                  className="inline-block h-3 w-3 rounded-full"
                  style={{ background: COMMUNITY_PALETTE[i % COMMUNITY_PALETTE.length] }}
                />
                <input
                  className="rounded border border-input bg-background px-1 py-0.5"
                  value={c.label}
                  onChange={(ev) => updateCommunity(c.id, { label: ev.target.value })}
                />
                <input
                  type="range"
                  min={-1}
                  max={1}
                  step={0.05}
                  value={c.x}
                  onChange={(ev) => updateCommunity(c.id, { x: num(ev.target.value) })}
                />
                <input
                  type="range"
                  min={-1}
                  max={1}
                  step={0.05}
                  value={c.y}
                  onChange={(ev) => updateCommunity(c.id, { y: num(ev.target.value) })}
                />
                <input
                  type="range"
                  min={0.05}
                  max={0.6}
                  step={0.01}
                  value={c.spread}
                  onChange={(ev) => updateCommunity(c.id, { spread: num(ev.target.value) })}
                />
                <input
                  type="range"
                  min={0}
                  max={5}
                  step={0.1}
                  value={c.weight}
                  onChange={(ev) => updateCommunity(c.id, { weight: num(ev.target.value) })}
                />
                <button
                  type="button"
                  data-testid={`community-remove-${c.id}`}
                  className="rounded text-muted-foreground hover:text-[#dc3545]"
                  title="Retirer"
                  onClick={() => removeCommunity(c.id)}
                >
                  ✕
                </button>
              </div>
            ))}
            {/* Per-community turnout on its own row to stay readable */}
            <div className="flex flex-col gap-1">
              {e.communities.map((c, i) => (
                <label
                  key={c.id}
                  className="flex items-center gap-2 text-[0.7rem] text-muted-foreground"
                >
                  <span
                    className="inline-block h-2 w-2 rounded-full"
                    style={{ background: COMMUNITY_PALETTE[i % COMMUNITY_PALETTE.length] }}
                  />
                  <span className="w-32 shrink-0 truncate">{c.label} · participation</span>
                  <input
                    data-testid={`community-turnout-${c.id}`}
                    type="range"
                    className="flex-1"
                    min={0}
                    max={1}
                    step={0.05}
                    value={c.turnout}
                    onChange={(ev) => updateCommunity(c.id, { turnout: num(ev.target.value) })}
                  />
                  <span className="w-9 text-right tabular-nums">
                    {Math.round(c.turnout * 100)} %
                  </span>
                </label>
              ))}
            </div>

            {/* 3rd-axis (z) centres — only meaningful when the map is in 3D */}
            {dims >= 3 && (
              <div data-testid="community-z-list" className="flex flex-col gap-1">
                {e.communities.map((c, i) => (
                  <label
                    key={c.id}
                    className="flex items-center gap-2 text-[0.7rem] text-muted-foreground"
                  >
                    <span
                      className="inline-block h-2 w-2 rounded-full"
                      style={{ background: COMMUNITY_PALETTE[i % COMMUNITY_PALETTE.length] }}
                    />
                    <span className="w-32 shrink-0 truncate">{c.label} · 3ᵉ axe (z)</span>
                    <input
                      data-testid={`community-z-${c.id}`}
                      type="range"
                      className="flex-1"
                      min={-1}
                      max={1}
                      step={0.05}
                      value={c.z ?? 0}
                      onChange={(ev) => updateCommunity(c.id, { z: num(ev.target.value) })}
                    />
                    <span className="w-9 text-right tabular-nums">{(c.z ?? 0).toFixed(2)}</span>
                  </label>
                ))}
              </div>
            )}

            <button
              type="button"
              data-testid="community-add"
              onClick={addCommunity}
              className="self-start rounded border border-dashed border-border px-2 py-1 text-xs text-muted-foreground hover:bg-accent"
            >
              + Ajouter une communauté
            </button>
          </div>

          {/* Input data: import / export the composition as JSON */}
          <details data-testid="electorate-io" className="rounded-md border border-border">
            <summary className="cursor-pointer px-2.5 py-1.5 text-xs font-medium text-muted-foreground">
              Données d’entrée — importer / exporter (JSON)
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
                  Importer
                </button>
                <button
                  type="button"
                  data-testid="electorate-export"
                  onClick={doExport}
                  className="rounded border border-border px-2 py-0.5 text-xs hover:bg-accent"
                >
                  {copied ? 'Copié ✓' : 'Exporter (copier)'}
                </button>
                {impErr && (
                  <span
                    data-testid="electorate-json-error"
                    className="text-[0.7rem] text-[#dc3545]"
                  >
                    JSON invalide (il faut un tableau « communities » non vide).
                  </span>
                )}
              </div>
            </div>
          </details>

          <p className="text-[0.68rem] text-muted-foreground/70">
            L’électorat composé alimente la vue dirigeant (carte, zones, bilan, coloré par
            communauté), le parlement (sièges, bilan d’assemblée) et le taux de paradoxe (vrai taux
            de cycle spatial, ré-échantillonné). Le 3ᵉ axe n’agit qu’en mode carte 3D ; le bruit de
            mesure simule l’incertitude d’un sondage.
          </p>
        </>
      )}
    </div>
  );
};

export default ElectorateComposer;
