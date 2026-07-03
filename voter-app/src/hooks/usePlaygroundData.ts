import React from 'react';
import type { ElectionConfig, PlaygroundState } from '../stores/useElectionStore';
import { runProfileSimulate, type ProfileSimulateResult } from '../services/profileApi';
import { runAssembly, type AssemblyResult } from '../services/assemblyApi';

// The minimal set of fields that change the profile (avoids re-fetch on unrelated state).
function toProfileKey(config: ElectionConfig, pg: PlaygroundState) {
  return {
    source: pg.prefSource,
    dims: pg.space.dims,
    valence: pg.space.valenceEnabled,
    behavior: pg.behavior,
    prefParams: pg.prefParams,
    ballot: pg.ballot,
    num_voters: config.num_voters,
    seed: config.seed,
    candidates: config.candidates.map((c) => [c.name, c.x, c.y]),
  };
}

// ── Live profile diagnostics (P1) ───────────────────────────────────────────
// Debounced call to the profile engine on every assumption change, surfacing the
// paradox/cycle rate. The number visibly moves as the source/dims change — the
// meta-lesson that conclusions are conditional on the model.
export function useProfileDiagnostics(
  config: ElectionConfig,
  playground: PlaygroundState
): { result: ProfileSimulateResult | null; loading: boolean } {
  const [result, setResult] = React.useState<ProfileSimulateResult | null>(null);
  const [loading, setLoading] = React.useState(false);
  const key = JSON.stringify(toProfileKey(config, playground));

  React.useEffect(() => {
    let alive = true;
    setLoading(true);
    const t = setTimeout(() => {
      runProfileSimulate(config, playground)
        .then((r) => {
          if (alive) setResult(r);
        })
        .catch(() => {
          if (alive) setResult(null);
        })
        .finally(() => {
          if (alive) setLoading(false);
        });
    }, 350);
    return () => {
      alive = false;
      clearTimeout(t);
    };
  }, [key]);

  return { result, loading };
}

// Debounced call to /assembly (P3) — only while in parliament mode.
export function useAssembly(
  config: ElectionConfig,
  playground: PlaygroundState,
  enabled: boolean
): { assembly: AssemblyResult | null; loading: boolean } {
  const [assembly, setAssembly] = React.useState<AssemblyResult | null>(null);
  const [loading, setLoading] = React.useState(false);
  // Key on every input the /assembly payload actually depends on, so a change to
  // the electorate mixture, turnout, assembly knobs or parties triggers a refetch.
  // The old key dropped electorate + turnout → the hemicycle went stale.
  const key = JSON.stringify({
    enabled,
    a: playground.assembly,
    turnout: playground.turnout,
    electorate: playground.electorate,
    num_voters: config.num_voters,
    ideology: config.ideology,
    seed: config.seed,
    parties: config.candidates.map((c) => [c.name, c.x, c.y]),
  });

  React.useEffect(() => {
    if (!enabled) return;
    let alive = true;
    setLoading(true);
    const t = setTimeout(() => {
      runAssembly(config, playground)
        .then((r) => {
          if (alive) setAssembly(r);
        })
        .catch(() => {
          if (alive) setAssembly(null);
        })
        .finally(() => {
          if (alive) setLoading(false);
        });
    }, 300);
    return () => {
      alive = false;
      clearTimeout(t);
    };
  }, [key]);

  return { assembly, loading };
}
