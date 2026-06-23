import React, { useEffect, useRef, useState } from 'react';

// FlipReveal (Lab reshape P4) — the flip centerpiece. When `modeKey` changes,
// the canvas cross-fades/scales in and a one-line caption ("same voters,
// opposite character") floats over it for a moment. Replayable: every mode
// switch re-runs the animation, in both directions.

const CAPTION_MS = 2600;

export interface FlipRevealProps {
  modeKey: string;
  caption: string;
  children: React.ReactNode;
}

const FlipReveal: React.FC<FlipRevealProps> = ({ modeKey, caption, children }) => {
  const [entered, setEntered] = useState(false);
  const [showCaption, setShowCaption] = useState(false);
  const first = useRef(true);

  useEffect(() => {
    // Restart the enter animation on every mode change (skip the caption on
    // first mount — nothing flipped yet).
    setEntered(false);
    const raf = requestAnimationFrame(() => setEntered(true));
    let t: ReturnType<typeof setTimeout> | undefined;
    if (first.current) {
      first.current = false;
    } else {
      setShowCaption(true);
      t = setTimeout(() => setShowCaption(false), CAPTION_MS);
    }
    return () => {
      cancelAnimationFrame(raf);
      if (t) clearTimeout(t);
    };
  }, [modeKey]);

  return (
    <div data-testid="flip-reveal" className="relative">
      <div
        key={modeKey}
        data-testid="flip-stage"
        className="transition-all duration-500 ease-out"
        style={{
          opacity: entered ? 1 : 0,
          transform: entered ? 'scale(1)' : 'scale(0.96)',
        }}
      >
        {children}
      </div>
      {showCaption && (
        <div
          data-testid="flip-caption"
          className="pointer-events-none absolute inset-x-0 top-3 z-10 flex justify-center"
        >
          <span className="rounded-full bg-foreground/85 px-4 py-1.5 text-sm font-medium text-background shadow-lg">
            {caption}
          </span>
        </div>
      )}
    </div>
  );
};

export default FlipReveal;
