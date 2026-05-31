/**
 * PerturbationsContext — compatibility shim over useLabStore (Phase 5.4).
 * The pinned-perturbations registry now lives in stores/useLabStore. This keeps
 * usePerturbations()/PerturbationsProvider + the PinnedPerturbation type working
 * until 5.5 deletes the shim.
 */
import React, { useEffect } from 'react';
import { useLabStore, type PinnedPerturbation } from '../stores/useLabStore';

export type { PinnedPerturbation };

interface PerturbationsContextValue {
  pinned:           PinnedPerturbation[];
  pinPerturbation:  (p: Omit<PinnedPerturbation, 'id' | 'pinnedAt'>) => void;
  unpinPerturbation:(typeOrId: string) => void;
  clearPinned:      () => void;
  isPinned:         (type: string) => boolean;
}

export const PerturbationsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const hydratePinned = useLabStore((s) => s.hydratePinned);
  useEffect(() => { hydratePinned(); }, [hydratePinned]);
  return <>{children}</>;
};

export function usePerturbations(): PerturbationsContextValue {
  const pinned = useLabStore((s) => s.pinned);
  const pinPerturbation = useLabStore((s) => s.pinPerturbation);
  const unpinPerturbation = useLabStore((s) => s.unpinPerturbation);
  const clearPinned = useLabStore((s) => s.clearPinned);
  const isPinned = useLabStore((s) => s.isPinned);
  return { pinned, pinPerturbation, unpinPerturbation, clearPinned, isPinned };
}
