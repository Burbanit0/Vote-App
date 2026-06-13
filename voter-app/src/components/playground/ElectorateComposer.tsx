import React from 'react';
import { cn } from '@/lib/utils';
import { usePlayground } from '../../stores/useElectionStore';
import { ELECTORATE_PRESETS } from '../../stores/useElectionStore';
import { COMMUNITY_PALETTE } from '../../lib/playgroundElectorate';

// ElectorateComposer (electorate engine) — build a varied electorate as a
// mixture of communities, from textbook shapes to near-real compositions.
// 'simple' falls back to the ideology Gaussian; 'composed' uses the blocs below.
// The composed cloud is what the leader views display + analyse.

const num = (v: string): number => Number(v);

const ElectorateComposer: React.FC = () => {
  const {
    playground,
    setElectorate,
    updateCommunity,
    addCommunity,
    removeCommunity,
    applyElectoratePreset,
  } = usePlayground();
  const e = playground.electorate;
  const composed = e.mode === 'composed';

  return (
    <div data-testid="electorate-composer" className="flex flex-col gap-3">
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
              <button
                key={id}
                type="button"
                data-testid={`electorate-preset-${id}`}
                onClick={() => applyElectoratePreset(id)}
                className="rounded border border-border px-2 py-0.5 text-xs hover:bg-accent"
              >
                {p.label}
              </button>
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
            <button
              type="button"
              data-testid="community-add"
              onClick={addCommunity}
              className="self-start rounded border border-dashed border-border px-2 py-1 text-xs text-muted-foreground hover:bg-accent"
            >
              + Ajouter une communauté
            </button>
          </div>
          <p className="text-[0.68rem] text-muted-foreground/70">
            L’électorat composé alimente et s’affiche sur la vue dirigeant (carte, zones, bilan),
            coloré par communauté. Le parlement/taux de paradoxe suivront.
          </p>
        </>
      )}
    </div>
  );
};

export default ElectorateComposer;
