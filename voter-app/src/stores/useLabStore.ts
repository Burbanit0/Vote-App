/**
 * useLabStore — Election Lab cross-panel slice (Phase 5.4).
 *
 * Consolidates two former contexts:
 *   - PerturbationsContext     → pinned[] (persisted as votelab_pinned_perturbations)
 *   - AnimationBroadcastContext → frame (ephemeral animation step bus)
 *
 * PerturbationsContext / AnimationBroadcastContext are now thin shims over this
 * store. Both former hooks had an inert no-provider fallback; the store-backed
 * hooks need no provider at all, so that behaviour is preserved for free.
 */
import { create } from 'zustand';

// ── Perturbations ───────────────────────────────────────────────────────────

const LS_KEY = 'votelab_pinned_perturbations';

export interface PinnedPerturbation {
  id: string;
  type: string;
  icon: string;
  label: string;
  summary: string;
  methodsChanged?: number;
  winnersByMethod?: Record<string, string | null>;
  pinnedAt: number;
}

function loadFromStorage(): PinnedPerturbation[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(LS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (x: unknown): x is PinnedPerturbation =>
        typeof x === 'object' &&
        x !== null &&
        typeof (x as PinnedPerturbation).type === 'string' &&
        typeof (x as PinnedPerturbation).label === 'string' &&
        typeof (x as PinnedPerturbation).summary === 'string'
    );
  } catch {
    return [];
  }
}

function saveToStorage(pinned: PinnedPerturbation[]): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(LS_KEY, JSON.stringify(pinned));
  } catch {
    // quota / disabled — silent
  }
}

// ── Animation broadcast ─────────────────────────────────────────────────────

export interface AnimationFrame {
  method: string;
  step: number;
  totalSteps: number;
  eliminated?: string | null;
  eliminatedSet?: string[];
  transfers?: Record<string, number>;
  currentWinner?: string | null;
  final?: boolean;
}

// ── Store ─────────────────────────────────────────────────────────────────

interface LabState {
  // Perturbations
  pinned: PinnedPerturbation[];
  pinPerturbation: (p: Omit<PinnedPerturbation, 'id' | 'pinnedAt'>) => void;
  unpinPerturbation: (typeOrId: string) => void;
  clearPinned: () => void;
  isPinned: (type: string) => boolean;
  hydratePinned: () => void;
  // Animation broadcast
  frame: AnimationFrame | null;
  publishFrame: (f: AnimationFrame | null) => void;
  clearFrame: () => void;
}

export const useLabStore = create<LabState>((set, get) => ({
  pinned: loadFromStorage(),
  pinPerturbation: (p) => {
    const next = get().pinned.filter((x) => x.type !== p.type);
    next.push({ ...p, id: `${p.type}-${Date.now()}`, pinnedAt: Date.now() });
    saveToStorage(next);
    set({ pinned: next });
  },
  unpinPerturbation: (typeOrId) => {
    const next = get().pinned.filter((x) => x.type !== typeOrId && x.id !== typeOrId);
    saveToStorage(next);
    set({ pinned: next });
  },
  clearPinned: () => {
    saveToStorage([]);
    set({ pinned: [] });
  },
  isPinned: (type) => get().pinned.some((x) => x.type === type),
  hydratePinned: () => set({ pinned: loadFromStorage() }),

  frame: null,
  publishFrame: (f) => set({ frame: f }),
  clearFrame: () => set({ frame: null }),
}));

// ── Convenience hooks (former context APIs) ───────────────────────────────────

export function usePerturbations() {
  const pinned = useLabStore((s) => s.pinned);
  const pinPerturbation = useLabStore((s) => s.pinPerturbation);
  const unpinPerturbation = useLabStore((s) => s.unpinPerturbation);
  const clearPinned = useLabStore((s) => s.clearPinned);
  const isPinned = useLabStore((s) => s.isPinned);
  return { pinned, pinPerturbation, unpinPerturbation, clearPinned, isPinned };
}

export function useAnimationBroadcast() {
  const frame = useLabStore((s) => s.frame);
  const publish = useLabStore((s) => s.publishFrame);
  const clear = useLabStore((s) => s.clearFrame);
  return { frame, publish, clear };
}
