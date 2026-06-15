/**
 * useDragTouch.test.ts
 *
 * Tests the unified drag hook via the makeDragHandlers helper, since the
 * hook itself uses ref-based SVG element access that requires a real DOM.
 * We also test useSwipe through the same test infrastructure.
 */
import { renderHook, act } from '@testing-library/react';

// ── useDragTouch helpers ──────────────────────────────────────────────────────

// Test the pure coordinate conversion helper by inspecting the default toDomain
describe('useDragTouch — coordinate normalisation', () => {
  // The default toDomain maps clientX/Y to [-1,1] based on bounding rect.
  // We reproduce it here to test the contract:
  function mockToDomain(clientX: number, clientY: number, rect: DOMRect) {
    return {
      x: Math.max(-1, Math.min(1, ((clientX - rect.left) / rect.width) * 2 - 1)),
      y: Math.max(-1, Math.min(1, 1 - ((clientY - rect.top) / rect.height) * 2)),
    };
  }

  it('maps top-left to (-1, +1)', () => {
    const rect = { left: 0, top: 0, width: 100, height: 100 } as DOMRect;
    const { x, y } = mockToDomain(0, 0, rect);
    expect(x).toBeCloseTo(-1, 2);
    expect(y).toBeCloseTo(1, 2);
  });

  it('maps centre to (0, 0)', () => {
    const rect = { left: 0, top: 0, width: 100, height: 100 } as DOMRect;
    const { x, y } = mockToDomain(50, 50, rect);
    expect(x).toBeCloseTo(0, 2);
    expect(y).toBeCloseTo(0, 2);
  });

  it('maps bottom-right to (+1, -1)', () => {
    const rect = { left: 0, top: 0, width: 100, height: 100 } as DOMRect;
    const { x, y } = mockToDomain(100, 100, rect);
    expect(x).toBeCloseTo(1, 2);
    expect(y).toBeCloseTo(-1, 2);
  });

  it('clamps values outside the bounding rect to [-1, 1]', () => {
    const rect = { left: 0, top: 0, width: 100, height: 100 } as DOMRect;
    const { x, y } = mockToDomain(200, -50, rect);
    expect(x).toBe(1);
    expect(y).toBe(1);
  });

  it('accounts for non-zero rect origin (translated SVG)', async () => {
    const rect = { left: 50, top: 50, width: 100, height: 100 } as DOMRect;
    const { x, y } = mockToDomain(100, 100, rect); // centre of the rect
    expect(x).toBeCloseTo(0, 2);
    expect(y).toBeCloseTo(0, 2);
  });
});

// ── makeDragHandlers contract ─────────────────────────────────────────────────

describe('makeDragHandlers', () => {
  function mockSvgRef(rect = { left: 0, top: 0, width: 200, height: 200 }) {
    return { current: { getBoundingClientRect: () => rect } } as any;
  }

  it('onMouseDown sets dragging to true and calls onStart', async () => {
    const { makeDragHandlers } = await import('../useDragTouch');
    const dragging = { current: false };
    const onStart = vi.fn();
    const { onMouseDown } = makeDragHandlers(mockSvgRef(), dragging, onStart);

    const e = { preventDefault: vi.fn(), clientX: 100, clientY: 100 } as any;
    onMouseDown(e);

    expect(e.preventDefault).toHaveBeenCalled();
    expect(dragging.current).toBe(true);
    expect(onStart).toHaveBeenCalledWith(0, 0); // centre of 200×200 rect
  });

  it('onTouchStart sets dragging to true and calls onStart', async () => {
    const { makeDragHandlers } = await import('../useDragTouch');
    const dragging = { current: false };
    const onStart = vi.fn();
    const { onTouchStart } = makeDragHandlers(mockSvgRef(), dragging, onStart);

    const e = {
      stopPropagation: vi.fn(),
      touches: [{ clientX: 50, clientY: 150 }],
    } as any;
    onTouchStart(e);

    expect(e.stopPropagation).toHaveBeenCalled();
    expect(dragging.current).toBe(true);
    expect(onStart).toHaveBeenCalled();
    const [x, y] = onStart.mock.calls[0];
    // x = (50/200)*2-1 = -0.5, y = 1-(150/200)*2 = -0.5
    expect(x).toBeCloseTo(-0.5, 2);
    expect(y).toBeCloseTo(-0.5, 2);
  });

  it('returns no-op handlers when svgRef.current is null', async () => {
    const { makeDragHandlers } = await import('../useDragTouch');
    const dragging = { current: false };
    const onStart = vi.fn();
    const nullRef = { current: null } as any;
    const { onMouseDown } = makeDragHandlers(nullRef, dragging, onStart);

    const e = { preventDefault: vi.fn(), clientX: 0, clientY: 0 } as any;
    // Should not throw
    expect(() => onMouseDown(e)).not.toThrow();
  });
});

// ── useSwipe ─────────────────────────────────────────────────────────────────

describe('useSwipe', () => {
  function makeSwipeEvent(startX: number, endX: number, deltaY = 0) {
    return {
      touchstart: new TouchEvent('touchstart', {
        touches: [{ clientX: startX, clientY: 0 } as Touch],
      }),
      touchend: new TouchEvent('touchend', {
        changedTouches: [{ clientX: endX, clientY: deltaY } as Touch],
      }),
    };
  }

  function setup() {
    const el = document.createElement('div');
    document.body.appendChild(el);
    return { el, cleanup: () => document.body.removeChild(el) };
  }

  it('calls onSwipeLeft when swiping left (|deltaX| > 40)', async () => {
    const { useSwipe } = await import('../useSwipe');
    const { el, cleanup } = setup();
    const ref = { current: el };
    const onSwipeLeft = vi.fn();
    const onSwipeRight = vi.fn();

    renderHook(() => useSwipe(ref, { onSwipeLeft, onSwipeRight, threshold: 40, maxDuration: 400 }));

    act(() => {
      el.dispatchEvent(
        new TouchEvent('touchstart', { touches: [{ clientX: 200, clientY: 0 } as Touch] })
      );
      el.dispatchEvent(
        new TouchEvent('touchend', { changedTouches: [{ clientX: 100, clientY: 0 } as Touch] })
      );
    });

    expect(onSwipeLeft).toHaveBeenCalledTimes(1);
    expect(onSwipeRight).not.toHaveBeenCalled();
    cleanup();
  });

  it('calls onSwipeRight when swiping right (|deltaX| > 40)', async () => {
    const { useSwipe } = await import('../useSwipe');
    const { el, cleanup } = setup();
    const ref = { current: el };
    const onSwipeLeft = vi.fn();
    const onSwipeRight = vi.fn();

    renderHook(() => useSwipe(ref, { onSwipeLeft, onSwipeRight, threshold: 40, maxDuration: 400 }));

    act(() => {
      el.dispatchEvent(
        new TouchEvent('touchstart', { touches: [{ clientX: 100, clientY: 0 } as Touch] })
      );
      el.dispatchEvent(
        new TouchEvent('touchend', { changedTouches: [{ clientX: 200, clientY: 0 } as Touch] })
      );
    });

    expect(onSwipeRight).toHaveBeenCalledTimes(1);
    expect(onSwipeLeft).not.toHaveBeenCalled();
    cleanup();
  });

  it('does NOT trigger swipe when movement < threshold', async () => {
    const { useSwipe } = await import('../useSwipe');
    const { el, cleanup } = setup();
    const ref = { current: el };
    const onSwipeLeft = vi.fn();

    renderHook(() => useSwipe(ref, { onSwipeLeft, threshold: 40 }));

    act(() => {
      el.dispatchEvent(
        new TouchEvent('touchstart', { touches: [{ clientX: 100, clientY: 0 } as Touch] })
      );
      el.dispatchEvent(
        new TouchEvent('touchend', { changedTouches: [{ clientX: 85, clientY: 0 } as Touch] })
      );
    });

    expect(onSwipeLeft).not.toHaveBeenCalled();
    cleanup();
  });

  it('does NOT trigger swipe when mostly vertical', async () => {
    const { useSwipe } = await import('../useSwipe');
    const { el, cleanup } = setup();
    const ref = { current: el };
    const onSwipeLeft = vi.fn();

    renderHook(() => useSwipe(ref, { onSwipeLeft, threshold: 40 }));

    act(() => {
      el.dispatchEvent(
        new TouchEvent('touchstart', { touches: [{ clientX: 100, clientY: 0 } as Touch] })
      );
      // deltaX = 50, deltaY = 80 → mostly vertical
      el.dispatchEvent(
        new TouchEvent('touchend', { changedTouches: [{ clientX: 50, clientY: 80 } as Touch] })
      );
    });

    expect(onSwipeLeft).not.toHaveBeenCalled();
    cleanup();
  });
});
