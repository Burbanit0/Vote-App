/**
 * AnimationBroadcastContext — small bus so an animation panel (e.g.
 * VoteStepAnimator) can publish its currently displayed step so the central
 * view can highlight the corresponding method/round/candidate.
 *
 * Why a context and not a callback prop? The animator lives inside a tab
 * whose content is mounted/unmounted as the user navigates. The central
 * view always lives at the page level. A context bridges them without
 * either being aware of the other's lifecycle.
 */
import React, {
  createContext, useCallback, useContext, useMemo, useState,
} from 'react';

export interface AnimationFrame {
  /** Voting method being animated ("irv" | "borda" | ... ). */
  method:           string;
  /** 1-indexed round / step inside the animation. */
  step:             number;
  /** Total number of steps in this animation. */
  totalSteps:       number;
  /** Eliminated candidate for this step (may be multiple via " + "). */
  eliminated?:      string | null;
  /** Current standing winner (or null if not yet decided). */
  currentWinner?:   string | null;
  /** True when the animator is on the final step (winner declared). */
  final?:           boolean;
}

interface AnimationBroadcastValue {
  frame:      AnimationFrame | null;
  publish:    (f: AnimationFrame | null) => void;
  clear:      () => void;
}

const AnimationBroadcastContext = createContext<AnimationBroadcastValue | null>(null);

export const AnimationBroadcastProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [frame, setFrame] = useState<AnimationFrame | null>(null);

  const publish = useCallback((f: AnimationFrame | null) => setFrame(f), []);
  const clear   = useCallback(() => setFrame(null), []);

  const value = useMemo(() => ({ frame, publish, clear }), [frame, publish, clear]);
  return (
    <AnimationBroadcastContext.Provider value={value}>
      {children}
    </AnimationBroadcastContext.Provider>
  );
};

const INERT: AnimationBroadcastValue = {
  frame: null,
  publish: () => {},
  clear:   () => {},
};

export function useAnimationBroadcast(): AnimationBroadcastValue {
  return useContext(AnimationBroadcastContext) ?? INERT;
}
