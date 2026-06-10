/**
 * useSwipe — horizontal swipe detection for touch devices.
 *
 * Detects swipe left/right on a container element.
 * Only triggers when: |deltaX| > threshold AND duration < maxDuration.
 * Does NOT prevent scroll (vertical swipes pass through).
 */
import { RefObject, useEffect } from 'react';

export interface UseSwipeOptions {
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  /** Minimum horizontal distance in px to register as a swipe. Default: 40. */
  threshold?: number;
  /** Maximum gesture duration in ms. Default: 400. */
  maxDuration?: number;
}

export function useSwipe(
  ref: RefObject<HTMLElement>,
  { onSwipeLeft, onSwipeRight, threshold = 40, maxDuration = 400 }: UseSwipeOptions
): void {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    let startX = 0;
    let startY = 0;
    let startTime = 0;
    let active = false;

    const handleTouchStart = (e: TouchEvent) => {
      const touch = e.touches[0];
      if (!touch) return;
      startX = touch.clientX;
      startY = touch.clientY;
      startTime = Date.now();
      active = true;
    };

    const handleTouchEnd = (e: TouchEvent) => {
      if (!active) return;
      active = false;
      const touch = e.changedTouches[0];
      if (!touch) return;

      const deltaX = touch.clientX - startX;
      const deltaY = touch.clientY - startY;
      const elapsed = Date.now() - startTime;

      // Ignore if mostly vertical or too slow
      if (Math.abs(deltaY) > Math.abs(deltaX)) return;
      if (Math.abs(deltaX) < threshold) return;
      if (elapsed > maxDuration) return;

      if (deltaX < 0) onSwipeLeft?.();
      else onSwipeRight?.();
    };

    const handleTouchCancel = () => {
      active = false;
    };

    el.addEventListener('touchstart', handleTouchStart, { passive: true });
    el.addEventListener('touchend', handleTouchEnd, { passive: true });
    el.addEventListener('touchcancel', handleTouchCancel, { passive: true });

    return () => {
      el.removeEventListener('touchstart', handleTouchStart);
      el.removeEventListener('touchend', handleTouchEnd);
      el.removeEventListener('touchcancel', handleTouchCancel);
    };
  }, [ref, onSwipeLeft, onSwipeRight, threshold, maxDuration]);
}
