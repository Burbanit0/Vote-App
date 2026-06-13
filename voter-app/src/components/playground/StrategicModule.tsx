import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import type { ElectionConfig, PlaygroundState } from '../../stores/useElectionStore';
import { runProfileSimulate } from '../../services/profileApi';
import { RULE_LABELS, type Rule } from '../../lib/playgroundVoting';

// StrategicModule (on-demand) — the rigorous Gibbard–Satterthwaite individual
// manipulability rate per method: the share of voters who can improve their
// outcome by submitting an insincere ballot (brute-force ballot perturbation on
// the backend). Lower = more strategy-resistant. Kept OUT of the live read-out
// (it's O(voters × methods × perms), ~seconds); computed only when asked, so the
// rest of the playground stays at ~15 ms.

const StrategicModule: React.FC<{ config: ElectionConfig; playground: PlaygroundState }> = ({
  config,
  playground,
}) => {
  const [rows, setRows] = useState<{ name: string; sv: number }[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const run = async () => {
    setLoading(true);
    setError(false);
    try {
      const res = await runProfileSimulate(config, playground, true);
      const out = Object.entries(res.methods)
        .map(([name, m]) => ({ name, sv: m.strategic_vulnerability ?? -1 }))
        .filter((r) => r.sv >= 0)
        .sort((a, b) => a.sv - b.sv); // most resistant first
      setRows(out);
    } catch {
      setError(true);
      setRows(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="strategic-module" className="flex flex-col gap-2">
      <p className="text-[0.7rem] text-muted-foreground/80">
        Part des électeurs qui pourraient améliorer leur résultat en votant insincèrement
        (Gibbard–Satterthwaite, par force brute). Plus c’est bas, plus la méthode résiste.
        Calcul lourd — à la demande, hors lecture temps-réel.
      </p>
      <Button
        data-testid="strategic-run"
        variant="outline"
        size="sm"
        className="self-start"
        onClick={run}
        disabled={loading}
      >
        {loading ? 'Calcul… (quelques secondes)' : '▶ Calculer la vulnérabilité stratégique'}
      </Button>

      {error && (
        <p className="text-xs text-amber-600 dark:text-amber-400">
          Calcul indisponible (backend). Réessayez après redémarrage.
        </p>
      )}

      {rows && (
        <div data-testid="strategic-rows" className="flex flex-col gap-1">
          {rows.map(({ name, sv }) => (
            <div key={name} className="flex items-center gap-2 text-xs">
              <span className="w-40 shrink-0 truncate text-muted-foreground">
                {RULE_LABELS[name as Rule] ?? name}
              </span>
              <div className="h-2.5 flex-1 overflow-hidden rounded bg-muted/50">
                <div
                  className="h-full rounded bg-amber-500/70"
                  style={{ width: `${sv * 100}%`, transition: 'width 300ms ease' }}
                />
              </div>
              <span className="w-10 text-right tabular-nums text-muted-foreground">
                {Math.round(sv * 100)} %
              </span>
            </div>
          ))}
          <p className="text-[0.65rem] text-muted-foreground/70">
            Barre = part d’électeurs avec un mensonge profitable (0 % = aucun n’y gagne).
          </p>
        </div>
      )}
    </div>
  );
};

export default StrategicModule;
