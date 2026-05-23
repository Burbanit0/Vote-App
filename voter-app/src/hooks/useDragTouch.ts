/**
 * useDragTouch — unified mouse + touch SVG drag hook.
 *
 * Attaches mouse events to `window` (captures fast movement) and
 * touch events to the SVG element itself (avoids blocking scroll when idle).
 * Calls `preventDefault()` on `touchmove` only while a drag is in progress.
 *
 * The hook normalises coordinates via the caller-supplied `toDomain` function
 * so each component keeps its own coordinate system.
 */
import { RefObject, useCallback, useEffect, useRef } from 'react';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface DragCallbacks {
  /** Called when a drag starts. Returns domain {x, y}. */
  onStart: (x: number, y: number) => void;
  /** Called on each move while dragging. */
  onMove:  (x: number, y: number) => void;
  /** Called when the drag ends. */
  onEnd:   () => void;
}

export interface UseDragTouchOptions extends DragCallbacks {
  /**
   * Converts (clientX, clientY, svgBoundingRect) to domain {x, y}.
   * Defaults to a generic [-1, 1] normalisation based on the bounding rect.
   */
  toDomain?: (clientX: number, clientY: number, rect: DOMRect) => { x: number; y: number };
}

// ── Default domain converter (generic [-1, 1] normalisation) ──────────────────

function defaultToDomain(clientX: number, clientY: number, rect: DOMRect) {
  return {
    x: Math.max(-1, Math.min(1, ((clientX - rect.left) / rect.width)  * 2 - 1)),
    y: Math.max(-1, Math.min(1, 1 - ((clientY - rect.top)  / rect.height) * 2)),
  };
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useDragTouch(
  svgRef:  RefObject<SVGSVGElement | null>,
  options: UseDragTouchOptions,
): void {
  const { onStart, onMove, onEnd, toDomain = defaultToDomain } = options;

  // Whether a drag is currently active (used to gate touchmove preventDefault)
  const draggingRef = useRef(false);

  // Keep callbacks stable so effects don't re-run on every render
  const cbRef = useRef({ onStart, onMove, onEnd, toDomain });
  useEffect(() => { cbRef.current = { onStart, onMove, onEnd, toDomain }; });

  // ── Mouse events (window-level to capture fast pointer movement) ───────────

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!draggingRef.current || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const { x, y } = cbRef.current.toDomain(e.clientX, e.clientY, rect);
    cbRef.current.onMove(x, y);
  }, [svgRef]);

  const handleMouseUp = useCallback(() => {
    if (!draggingRef.current) return;
    draggingRef.current = false;
    cbRef.current.onEnd();
  }, []);

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    window.addEventListener('mouseup',   handleMouseUp,   { passive: true });
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup',   handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  // ── Touch events (SVG-level to avoid blocking page scroll when idle) ────────

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;

    const handleTouchMove = (e: TouchEvent) => {
      if (!draggingRef.current) return;
      // Only block scroll when actually dragging
      e.preventDefault();
      const touch = e.touches[0];
      if (!touch) return;
      const rect = svg.getBoundingClientRect();
      const { x, y } = cbRef.current.toDomain(touch.clientX, touch.clientY, rect);
      cbRef.current.onMove(x, y);
    };

    const handleTouchEnd = () => {
      if (!draggingRef.current) return;
      draggingRef.current = false;
      cbRef.current.onEnd();
    };

    // passive: false so we can preventDefault() on touchmove during drag
    svg.addEventListener('touchmove', handleTouchMove, { passive: false });
    svg.addEventListener('touchend',  handleTouchEnd,  { passive: true });
    svg.addEventListener('touchcancel', handleTouchEnd, { passive: true });

    return () => {
      svg.removeEventListener('touchmove', handleTouchMove);
      svg.removeEventListener('touchend',  handleTouchEnd);
      svg.removeEventListener('touchcancel', handleTouchEnd);
    };
  }, [svgRef]);

  // ── Expose a startDrag helper on the ref so SVG elements can call it ────────

  // We attach it as a property so callers can trigger start from onMouseDown/onTouchStart
  // without knowing about internals. Access via useDragTouch.startDrag in same scope.
  // → Instead we return startDrag and let the caller wire it to their event handlers.

  // (startDrag is not returned here — callers call it from their own onMouseDown/onTouchStart
  //  handlers and then set draggingRef.current = true via the returned setter)

  // Actually: expose a `startDrag` function via a ref property pattern.
  // We use an effect to attach a named property to the SVG element.
  // → Simpler: export a separate `startDrag` factory function.
}

/**
 * Returns an onMouseDown / onTouchStart handler pair that starts a drag
 * managed by useDragTouch. Call this for each draggable child element.
 *
 * @param svgRef   The same ref passed to useDragTouch
 * @param dragging Mutable ref that useDragTouch reads — set to true on start
 * @param onStart  The same onStart callback
 * @param toDomain Optional domain converter
 */
export function makeDragHandlers(
  svgRef:   RefObject<SVGSVGElement | null>,
  dragging: { current: boolean },
  onStart:  (x: number, y: number) => void,
  toDomain: (clientX: number, clientY: number, rect: DOMRect) => { x: number; y: number } = defaultToDomain,
) {
  function getCoords(clientX: number, clientY: number) {
    if (!svgRef.current) return { x: 0, y: 0 };
    return toDomain(clientX, clientY, svgRef.current.getBoundingClientRect());
  }

  return {
    onMouseDown: (e: React.MouseEvent) => {
      e.preventDefault();
      dragging.current = true;
      const { x, y } = getCoords(e.clientX, e.clientY);
      onStart(x, y);
    },
    onTouchStart: (e: React.TouchEvent) => {
      e.stopPropagation();
      const touch = e.touches[0];
      if (!touch) return;
      dragging.current = true;
      const { x, y } = getCoords(touch.clientX, touch.clientY);
      onStart(x, y);
    },
  };
}

/**
 * Simplified version of useDragTouch that bundles the dragging-ref internally.
 * Returns { dragHandlers, draggingRef } — wire dragHandlers to draggable elements.
 */
export function useDragTouchWithHandlers(
  svgRef:   RefObject<SVGSVGElement | null>,
  callbacks: DragCallbacks,
  toDomain?: (clientX: number, clientY: number, rect: DOMRect) => { x: number; y: number },
): {
  draggingRef: { current: boolean };
  onMouseDown:  (e: React.MouseEvent) => void;
  onTouchStart: (e: React.TouchEvent) => void;
} {
  const draggingRef = useRef(false);

  useDragTouch(svgRef, {
    ...callbacks,
    toDomain,
    onStart: (x, y) => {
      draggingRef.current = true;
      callbacks.onStart(x, y);
    },
    onEnd: () => {
      draggingRef.current = false;
      callbacks.onEnd();
    },
  });

  const domainFn = toDomain ?? defaultToDomain;
  const handlers = makeDragHandlers(svgRef, draggingRef, callbacks.onStart, domainFn);

  return { draggingRef, ...handlers };
}
