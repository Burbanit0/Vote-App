import { keyTarget } from './playerClock';

// Playback itself (a tick per beat, the stop at the last tick, the rewind from the end) is
// TickPlayer's, and TickPlayer.test.tsx drives it through the page.
describe('polity player clock', () => {
  it('maps keys to ticks inside the run', () => {
    expect(keyTarget(' ', 5, 12, 4)).toBe('toggle');
    expect(keyTarget('ArrowRight', 12, 12, 4)).toBe(12);
    expect(keyTarget('ArrowLeft', 0, 12, 4)).toBe(0);
    expect(keyTarget('ArrowLeft', 5, 12, 4)).toBe(4);
    expect(keyTarget('PageDown', 10, 12, 4)).toBe(12);
    expect(keyTarget('PageUp', 5, 12, 4)).toBe(1);
    expect(keyTarget('Home', 5, 12, 4)).toBe(0);
    expect(keyTarget('End', 5, 12, 4)).toBe(12);
    expect(keyTarget('x', 5, 12, 4)).toBeNull();
  });
});
