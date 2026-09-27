/**
 * useDragTouch — unified mouse + touch SVG drag hook.
 *
 * Attaches mouse events to `window` (captures fast movement) and
 * touch events to the SVG element itself (avoids blocking scroll when idle).
 * Calls `preventDefault()` on `touchmove` only while a drag is in progress.
 *
 * The caller owns the drag state: it arms a drag from its own onMouseDown /
 * onTouchStart, reports it through `isDragging`, and clears it in `onEnd`. The
 * hook normalises coordinates via the caller-supplied `toDomain` function so
 * each component keeps its own coordinate system.
 */
import { RefObject, useCallback, useEffect, useRef, type KeyboardEvent } from 'react';

// ── Types ─────────────────────────────────────────────────────────────────────

interface UseDragTouchOptions {
  /** True while the caller has a drag armed. Gates moves and touchmove's preventDefault. */
  isDragging: () => boolean;
  /** Called on each move while dragging, with domain {x, y}. */
  onMove: (x: number, y: number) => void;
  /** Called once when the pointer is released during a drag; clear the drag state here. */
  onEnd: () => void;
  /** Converts (clientX, clientY, svgBoundingRect) to domain {x, y}. */
  toDomain: (clientX: number, clientY: number, rect: DOMRect) => { x: number; y: number };
}

/**
 * Keyboard equivalent of a drag: arrow keys nudge a domain point (0.02 step,
 * 0.1 with Shift), clamped to [-1, 1]. Ignores every other key. Shared by
 * LeaderCanvas (candidates) and ParliamentCanvas (parties) — both call this
 * from a draggable element's onKeyDown, then apply any component-specific
 * rule to the result themselves (e.g. LeaderCanvas zeroes y in 1-D mode,
 * matching what its mouse/touch drag already does).
 */
export function arrowKeyNudge(
  e: KeyboardEvent,
  current: { x: number; y: number },
  onMove: (x: number, y: number) => void
): void {
  const step = e.shiftKey ? 0.1 : 0.02;
  let dx = 0;
  let dy = 0;
  switch (e.key) {
    case 'ArrowLeft':
      dx = -step;
      break;
    case 'ArrowRight':
      dx = step;
      break;
    case 'ArrowUp':
      dy = step;
      break;
    case 'ArrowDown':
      dy = -step;
      break;
    default:
      return;
  }
  e.preventDefault();
  onMove(Math.max(-1, Math.min(1, current.x + dx)), Math.max(-1, Math.min(1, current.y + dy)));
}

/**
 * Builds a toDomain converter for an SVG canvas with a fixed viewBox
 * (`width` × `height`) and a plot-area inset of `pad` on every side — the
 * shared shape behind every hand-rolled `svgToDomain` in the playground
 * canvases (LeaderCanvas/ParliamentCanvas pass width === height for the
 * square case, HistoricalReplay passes distinct width/height for the general
 * rect case).
 */
export function makeSvgToDomain(viewBox: { width: number; height: number; pad: number }) {
  const { width, height, pad } = viewBox;
  const plotW = width - 2 * pad;
  const plotH = height - 2 * pad;
  return (clientX: number, clientY: number, rect: DOMRect) => {
    const sx = ((clientX - rect.left) / rect.width) * width;
    const sy = ((clientY - rect.top) / rect.height) * height;
    return {
      x: Math.max(-1, Math.min(1, ((sx - pad) / plotW) * 2 - 1)),
      y: Math.max(-1, Math.min(1, 1 - ((sy - pad) / plotH) * 2)),
    };
  };
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useDragTouch(
  svgRef: RefObject<SVGSVGElement | null>,
  options: UseDragTouchOptions
): void {
  // Keep callbacks stable so effects don't re-run on every render
  const cbRef = useRef(options);
  useEffect(() => {
    cbRef.current = options;
  });

  // ── Mouse events (window-level to capture fast pointer movement) ───────────

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!cbRef.current.isDragging() || !svgRef.current) return;
      const rect = svgRef.current.getBoundingClientRect();
      const { x, y } = cbRef.current.toDomain(e.clientX, e.clientY, rect);
      cbRef.current.onMove(x, y);
    },
    [svgRef]
  );

  const handleMouseUp = useCallback(() => {
    if (cbRef.current.isDragging()) cbRef.current.onEnd();
  }, []);

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    window.addEventListener('mouseup', handleMouseUp, { passive: true });
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  // ── Touch events (SVG-level to avoid blocking page scroll when idle) ────────

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;

    const handleTouchMove = (e: TouchEvent) => {
      if (!cbRef.current.isDragging()) return;
      // Only block scroll when actually dragging
      e.preventDefault();
      const touch = e.touches[0];
      if (!touch) return;
      const rect = svg.getBoundingClientRect();
      const { x, y } = cbRef.current.toDomain(touch.clientX, touch.clientY, rect);
      cbRef.current.onMove(x, y);
    };

    const handleTouchEnd = () => {
      if (cbRef.current.isDragging()) cbRef.current.onEnd();
    };

    // passive: false so we can preventDefault() on touchmove during drag
    svg.addEventListener('touchmove', handleTouchMove, { passive: false });
    svg.addEventListener('touchend', handleTouchEnd, { passive: true });
    svg.addEventListener('touchcancel', handleTouchEnd, { passive: true });

    return () => {
      svg.removeEventListener('touchmove', handleTouchMove);
      svg.removeEventListener('touchend', handleTouchEnd);
      svg.removeEventListener('touchcancel', handleTouchEnd);
    };
  }, [svgRef]);
}
