import {
  INITIAL_PLAYER,
  PLAYER_SPEEDS,
  beatMs,
  keyTarget,
  nextBeat,
  playFrom,
  playerReducer,
} from './playerClock';

describe('polity player clock', () => {
  it('toggles, pauses and changes speed', () => {
    expect(INITIAL_PLAYER).toEqual({ playing: false, speed: 2 });
    const playing = playerReducer(INITIAL_PLAYER, { type: 'toggle' });
    expect(playing.playing).toBe(true);
    expect(playerReducer(playing, { type: 'toggle' }).playing).toBe(false);
    expect(playerReducer(playing, { type: 'pause' }).playing).toBe(false);
    expect(playerReducer(INITIAL_PLAYER, { type: 'pause' })).toBe(INITIAL_PLAYER);
    expect(playerReducer(INITIAL_PLAYER, { type: 'speed', speed: 8 }).speed).toBe(8);
  });

  it('beats faster at a higher speed and stops at the last tick', () => {
    expect(PLAYER_SPEEDS.map(beatMs)).toEqual([1000, 500, 250, 125]);
    expect(nextBeat(3, 12)).toBe(4);
    expect(nextBeat(12, 12)).toBeNull();
  });

  it('rewinds when playback would start at the end', () => {
    expect(playFrom(12, 12)).toBe(0);
    expect(playFrom(5, 12)).toBe(5);
  });

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
