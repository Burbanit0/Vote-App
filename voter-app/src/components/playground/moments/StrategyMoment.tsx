import React from 'react';
import { usePlaygroundCtx } from '../PlaygroundController';
import Collapsible from '../Collapsible';
import StrategicModule from '../StrategicModule';
import SincerityModule from '../SincerityModule';
import { MANIP_COMPLEXITY } from '../../../lib/scorecard';

// Moment ③ Stratégie & vote blanc — sincere vs tactical voting, manipulation,
// strategic desertion. The manipulation lens is foregrounded on the instrument.
const StrategyMoment: React.FC = () => {
  const {
    config,
    playground,
    setPlaygroundDeep,
    mode,
    assembly,
    leaderRule,
    leaderCandidates,
    votingVoters,
    dims,
    youPos,
    setYouPos,
    manipDetail,
  } = usePlaygroundCtx();

  if (mode !== 'leader') {
    return (
      <div className="flex flex-col gap-3 rounded-md border border-border p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Stratégie d’assemblée
        </p>
        <label
          className="flex items-center gap-2 text-sm"
          title="Les électeurs désertent les partis non viables (FPTP : hors du top-2 de leur circonscription ; proportionnelle : sous le seuil) pour leur parti viable le plus proche — la loi de Duverger en mécanique."
        >
          <input
            data-testid="duverger-toggle"
            type="checkbox"
            checked={assembly.strategic_desertion}
            onChange={(e) => setPlaygroundDeep('assembly.strategic_desertion', e.target.checked)}
          />
          Désertion stratégique (Duverger)
        </label>
        <p className="text-[0.7rem] text-muted-foreground/80">
          La désertion comprime les partis non viables vers leur voisin viable : Duverger, en
          mécanique. L’effet se lit en direct sur la composition de l’assemblée →.
        </p>
      </div>
    );
  }

  return (
    <>
      <div className="flex flex-col gap-2 rounded-md border border-border p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          🗳️ Vote sincère ou vote utile ?
        </p>
        <p className="text-[0.7rem] text-muted-foreground/80">
          Votre conviction, méthode par méthode — glissez le losange « Vous » sur la carte.
        </p>
        <SincerityModule
          voters={votingVoters}
          candidates={leaderCandidates}
          dims={dims}
          you={youPos}
          onYouChange={setYouPos}
        />
      </div>

      <Collapsible
        title="⚡ Vulnérabilité stratégique (Gibbard–Satterthwaite)"
        subtitle="à la demande · lent"
        testid="module-strategic"
      >
        <StrategicModule config={config} playground={playground} />
      </Collapsible>

      {manipDetail && (
        <div
          data-testid="manip-hardness"
          className="rounded-md border border-border px-2.5 py-2 text-[0.7rem]"
        >
          <p className="font-semibold uppercase tracking-wide text-muted-foreground">
            Manipulation : principe vs pratique
          </p>
          <p className="mt-1">
            Jouable en principe (Gibbard–Satterthwaite) · calcul du bon mensonge :{' '}
            <strong
              className={
                MANIP_COMPLEXITY[leaderRule].hard
                  ? 'text-green-700 dark:text-green-400'
                  : 'text-amber-600 dark:text-amber-400'
              }
            >
              {MANIP_COMPLEXITY[leaderRule].label}
            </strong>{' '}
            <span className="text-muted-foreground">({MANIP_COMPLEXITY[leaderRule].ref})</span>
          </p>
          <p className="mt-0.5 text-muted-foreground">
            Sonde sur cet électorat :{' '}
            {manipDetail.probe.minCoalitionShare !== null ? (
              <>
                une coalition de{' '}
                <strong>{Math.round(manipDetail.probe.minCoalitionShare * 100)} %</strong> suffit
                (compromission naïve)
              </>
            ) : (
              <>aucune compromission naïve ≤ 40 % ne renverse le vainqueur ici</>
            )}
            {manipDetail.probe.backfired && ' · des tentatives se retournent contre la coalition'}.
          </p>
          <p className="mt-0.5 text-muted-foreground/80">
            Exemple :{' '}
            {manipDetail.easy.minCoalitionShare !== null
              ? `sous pluralité, ${Math.round(manipDetail.easy.minCoalitionShare * 100)} % suffisent`
              : 'sous pluralité, la compromission échoue ici'}
            {' ; la même stratégie sous IRV '}
            {manipDetail.hard.minCoalitionShare !== null
              ? `demande ${Math.round(manipDetail.hard.minCoalitionShare * 100)} %`
              : 'échoue'}
            {manipDetail.hard.backfired ? ' (et peut se retourner contre elle)' : ''}.
          </p>
        </div>
      )}
    </>
  );
};

export default StrategyMoment;
