/**
 * PerturbationsContext — shared registry of "pinned" perturbations.
 *
 * Each Perturber tab can publish its current result as a small self-describing
 * card (type / icon / label / summary). The LabCentralView reads this list and
 * displays the active perturbations alongside the baseline simulation, so the
 * user can SEE which effects are stacked on top of the configured election.
 *
 * No backend changes required — each panel computes its own perturbed result
 * and pushes a presentational summary into the context.
 */
import React, {
  createContext, useCallback, useContext, useMemo, useState,
} from 'react';

// ── Shape of one pinned perturbation entry ──────────────────────────────────

export interface PinnedPerturbation {
  /** Unique id (typically `${type}-${Date.now()}`). */
  id:        string;
  /** Type slug used to upsert (pinning twice from the same panel replaces). */
  type:      string;
  /** Single-character emoji icon, e.g. '🗳' '🎓' '🏳'. */
  icon:      string;
  /** Short human label, e.g. "Abstention 30% (démobilisation)". */
  label:     string;
  /** One-line outcome summary, e.g. "Vainqueur: Le Pen (4/5 méthodes)". */
  summary:   string;
  /**
   * Optional impact metric: how many methods changed winner vs the baseline.
   * Used by the central view to colour the card (green = stable, red = winner
   * changed under this perturbation).
   */
  methodsChanged?: number;
  /** Timestamp (ms) for stable ordering. */
  pinnedAt:  number;
}

// ── Context shape ───────────────────────────────────────────────────────────

interface PerturbationsContextValue {
  pinned:           PinnedPerturbation[];
  /** Insert or replace by `type`. */
  pinPerturbation:  (p: Omit<PinnedPerturbation, 'id' | 'pinnedAt'>) => void;
  unpinPerturbation:(typeOrId: string) => void;
  clearPinned:      () => void;
  /** Quick predicate to render a different button state. */
  isPinned:         (type: string) => boolean;
}

const PerturbationsContext = createContext<PerturbationsContextValue | null>(null);

// ── Provider ─────────────────────────────────────────────────────────────────

export const PerturbationsProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [pinned, setPinned] = useState<PinnedPerturbation[]>([]);

  const pinPerturbation = useCallback(
    (p: Omit<PinnedPerturbation, 'id' | 'pinnedAt'>) => {
      setPinned((prev) => {
        // Upsert by type — re-pinning the same panel replaces its previous entry
        const next = prev.filter((x) => x.type !== p.type);
        next.push({ ...p, id: `${p.type}-${Date.now()}`, pinnedAt: Date.now() });
        return next;
      });
    },
    []
  );

  const unpinPerturbation = useCallback((typeOrId: string) => {
    setPinned((prev) => prev.filter((x) => x.type !== typeOrId && x.id !== typeOrId));
  }, []);

  const clearPinned = useCallback(() => setPinned([]), []);

  const isPinned = useCallback(
    (type: string) => pinned.some((x) => x.type === type),
    [pinned]
  );

  const value = useMemo<PerturbationsContextValue>(
    () => ({ pinned, pinPerturbation, unpinPerturbation, clearPinned, isPinned }),
    [pinned, pinPerturbation, unpinPerturbation, clearPinned, isPinned]
  );

  return (
    <PerturbationsContext.Provider value={value}>
      {children}
    </PerturbationsContext.Provider>
  );
};

// ── Hook (returns inert fallback if not wrapped — Perturber panels can be
// used standalone in TheoryPage without crashing) ───────────────────────────

const INERT_VALUE: PerturbationsContextValue = {
  pinned:            [],
  pinPerturbation:   () => {},
  unpinPerturbation: () => {},
  clearPinned:       () => {},
  isPinned:          () => false,
};

export function usePerturbations(): PerturbationsContextValue {
  return useContext(PerturbationsContext) ?? INERT_VALUE;
}
