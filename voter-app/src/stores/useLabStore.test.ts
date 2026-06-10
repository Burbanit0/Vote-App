import { useLabStore } from './useLabStore';

const LS_KEY = 'votelab_pinned_perturbations';

beforeEach(() => {
  localStorage.clear();
  useLabStore.setState({ pinned: [], frame: null });
});

describe('useLabStore — perturbations', () => {
  const pin = (over: { label?: string } = {}) =>
    useLabStore.getState().pinPerturbation({
      type: 'abstention',
      icon: '🗳',
      label: 'Abstention 30%',
      summary: 'stable',
      ...over,
    });

  it('pins, exposes via isPinned, and persists', () => {
    pin();
    expect(useLabStore.getState().pinned).toHaveLength(1);
    expect(useLabStore.getState().isPinned('abstention')).toBe(true);
    expect(JSON.parse(localStorage.getItem(LS_KEY)!)).toHaveLength(1);
  });

  it('upserts by type (re-pin replaces, not duplicates)', () => {
    pin({ label: 'v1' });
    pin({ label: 'v2' });
    expect(useLabStore.getState().pinned).toHaveLength(1);
    expect(useLabStore.getState().pinned[0].label).toBe('v2');
  });

  it('unpins by type and clears all', () => {
    pin();
    useLabStore.getState().unpinPerturbation('abstention');
    expect(useLabStore.getState().pinned).toHaveLength(0);
    pin();
    useLabStore.getState().clearPinned();
    expect(useLabStore.getState().pinned).toHaveLength(0);
  });

  it('hydratePinned drops malformed localStorage entries', () => {
    localStorage.setItem(
      LS_KEY,
      JSON.stringify([
        { type: 'a', label: 'ok', summary: 's', pinnedAt: 1, icon: '🗳', id: 'a' },
        { foo: 'bar' },
        null,
      ])
    );
    useLabStore.getState().hydratePinned();
    expect(useLabStore.getState().pinned).toHaveLength(1);
  });
});

describe('useLabStore — animation frame', () => {
  it('publishes and clears the frame', () => {
    useLabStore.getState().publishFrame({ method: 'irv', step: 2, totalSteps: 3 });
    expect(useLabStore.getState().frame?.method).toBe('irv');
    useLabStore.getState().clearFrame();
    expect(useLabStore.getState().frame).toBeNull();
  });
});
