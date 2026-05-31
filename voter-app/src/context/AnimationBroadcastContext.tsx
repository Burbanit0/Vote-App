/**
 * AnimationBroadcastContext — compatibility shim over useLabStore (Phase 5.4).
 * The animation-step bus now lives in stores/useLabStore. Keeps
 * useAnimationBroadcast()/AnimationBroadcastProvider + the AnimationFrame type
 * working until 5.5 deletes the shim.
 */
import React from 'react';
import { useLabStore, type AnimationFrame } from '../stores/useLabStore';

export type { AnimationFrame };

interface AnimationBroadcastValue {
  frame:   AnimationFrame | null;
  publish: (f: AnimationFrame | null) => void;
  clear:   () => void;
}

export const AnimationBroadcastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <>{children}</>;
};

export function useAnimationBroadcast(): AnimationBroadcastValue {
  const frame = useLabStore((s) => s.frame);
  const publish = useLabStore((s) => s.publishFrame);
  const clear = useLabStore((s) => s.clearFrame);
  return { frame, publish, clear };
}
