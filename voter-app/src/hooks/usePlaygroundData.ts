import React from 'react';
import type { ElectionConfig, PlaygroundState } from '../stores/useElectionStore';
import { runProfileSimulate, type ProfileSimulateResult } from '../services/profileApi';
import { toProfilePayload } from '../services/profilePayload';
import { toAssemblyPayload } from '../services/assemblyPayload';
import { runAssembly, type AssemblyResult } from '../services/assemblyApi';

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
  // Keyed on the request body itself, so no input the backend reads can be left out of the
  // refetch: a hand-picked list went stale twice (turnout, the composed electorate and a
  // candidate's depth were all sent but not watched). Unrelated state leaves the body
  // unchanged, so it still does not refetch.
  const key = JSON.stringify(toProfilePayload(config, playground));

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
  // Keyed on the request body itself (see useProfileDiagnostics): the hand-picked list this
  // replaces went stale once already, and had to be kept in step with the payload by hand.
  const key = JSON.stringify({
    enabled,
    body: enabled ? toAssemblyPayload(config, playground) : null,
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
