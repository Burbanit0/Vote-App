import React from 'react';
import { cn } from '@/lib/utils';
import { usePlaygroundCtx } from '../PlaygroundController';
import { Field, selectCls, AnchorFallback } from '../playgroundFields';
import Collapsible from '../Collapsible';
import ScenarioInfo from '../ScenarioInfo';
import ElectorateComposer from '../ElectorateComposer';

const AbstentionPanel = React.lazy(() => import('../../shared/AbstentionPanel'));

// Moment ① Électorat — who votes, how they cluster and behave.
const ElectorateMoment: React.FC = () => {
  const {
    config,
    setPlayground,
    setPlaygroundDeep,
    applyPreset,
    presets,
    mode,
    space,
    behavior,
    prefSource,
    turnout,
    pointWord,
    composed,
    electorate,
    voters,
    votingVoters,
  } = usePlaygroundCtx();

  return (
    <>
      <Collapsible
        title="🧭 Composer l’électorat"
        subtitle={
          composed ? `${electorate.communities.length} communautés · mélange` : 'gaussien simple'
        }
        testid="module-electorate"
      >
        <ElectorateComposer />
      </Collapsible>

      <Field label="Point de départ (synthétique)">
        <div className="flex flex-col gap-1.5">
          {presets.map((p) => (
            <div key={p.id} className="flex items-center gap-1">
              <button
                data-testid={`preset-${p.id}`}
                type="button"
                onClick={() => applyPreset(p.id)}
                className={cn(
                  'flex-1 rounded-md border border-border px-2.5 py-1.5 text-left text-sm transition-colors hover:bg-accent hover:text-accent-foreground'
                )}
                title={p.description}
              >
                {p.label}
              </button>
              <ScenarioInfo scenario={p.id} />
            </div>
          ))}
        </div>
      </Field>

      <div className="rounded-md bg-muted/40 px-2.5 py-2 text-xs text-muted-foreground">
        {config.candidates.length} {pointWord} · {config.num_voters} électeurs · {config.ideology}
      </div>

      <Field label="Dimensions de l’espace" htmlFor="pg-dims">
        <select
          id="pg-dims"
          className={selectCls}
          value={space.dims}
          onChange={(e) => setPlaygroundDeep('space.dims', Number(e.target.value))}
        >
          <option value={1}>1D — un seul axe</option>
          <option value={2}>2D — deux axes</option>
          <option value={3}>3D — trois axes</option>
        </select>
      </Field>

      <Field label="Source des préférences" htmlFor="pg-source">
        <select
          id="pg-source"
          className={selectCls}
          value={prefSource}
          onChange={(e) => setPlayground({ prefSource: e.target.value as typeof prefSource })}
        >
          <option value="spatial">Spatiale (carte)</option>
          <option value="impartial">Culture impartiale</option>
          <option value="mallows">Mallows</option>
          <option value="urn">Urne de Pólya</option>
          <option value="handcrafted">Matrice sur mesure</option>
        </select>
      </Field>

      <Field label="Comportement des électeurs" htmlFor="pg-behavior">
        <select
          id="pg-behavior"
          className={selectCls}
          value={behavior}
          onChange={(e) => setPlayground({ behavior: e.target.value as typeof behavior })}
        >
          <option value="sincere">Sincère</option>
          <option value="strategic">Stratégique</option>
          <option value="mixed">Mixte</option>
        </select>
      </Field>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={space.valenceEnabled}
          onChange={(e) => setPlaygroundDeep('space.valenceEnabled', e.target.checked)}
        />
        Valence (qualité hors-idéologie)
      </label>

      {/* ── Participation / abstention (réalisme électoral) ── */}
      <div className="flex flex-col gap-2 rounded-md border border-border p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Participation (abstention)
        </p>
        <Field label="Modèle d’abstention" htmlFor="pg-turnout">
          <select
            id="pg-turnout"
            data-testid="turnout-select"
            className={selectCls}
            value={turnout.model}
            onChange={(e) => setPlaygroundDeep('turnout.model', e.target.value)}
          >
            <option value="full">Participation totale</option>
            <option value="alienation">Aliénation (trop loin de tous)</option>
            <option value="indifference">Indifférence (départage trop serré)</option>
          </select>
        </Field>
        {turnout.model !== 'full' && (
          <>
            <Field
              label={`Intensité : ${Math.round(turnout.intensity * 100)} %`}
              htmlFor="pg-turnout-int"
            >
              <input
                id="pg-turnout-int"
                data-testid="turnout-intensity"
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={turnout.intensity}
                onChange={(e) => setPlaygroundDeep('turnout.intensity', Number(e.target.value))}
              />
            </Field>
            {mode === 'leader' && (
              <p data-testid="turnout-rate" className="text-[0.7rem] text-muted-foreground">
                Taux de participation :{' '}
                <strong>
                  {Math.round((votingVoters.length / Math.max(1, voters.length)) * 100)} %
                </strong>{' '}
                ({voters.length - votingVoters.length} abstentions)
              </p>
            )}
          </>
        )}
        <p className="text-[0.65rem] text-muted-foreground/70">
          Abstention de Downs : aliénation (même le meilleur choix est trop loin) ou indifférence
          (pas d’écart net entre les deux premiers).
        </p>
        <Collapsible
          title="🔬 Abstention différentielle (analyse)"
          subtitle="distribution complète"
          testid="anchor-abstention"
        >
          <React.Suspense fallback={<AnchorFallback />}>
            <AbstentionPanel />
          </React.Suspense>
        </Collapsible>
      </div>
    </>
  );
};

export default ElectorateMoment;
