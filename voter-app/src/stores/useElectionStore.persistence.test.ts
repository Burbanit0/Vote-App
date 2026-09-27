import { useElectionStore, DEFAULT_CONFIG, DEFAULT_PLAYGROUND } from './useElectionStore';

// Regression coverage for the debounced-persistence fix (perf/leader-canvas-
// drag-and-memo): a candidate drag (LeaderCanvas's mousemove -> moveCandidate
// -> setConfig) or a slider drag (ElectorateComposer's onChange -> setConfig/
// setElectorate) used to call `localStorage.setItem` synchronously on EVERY
// frame/tick — real, unthrottled I/O with no coalescing (verified by a
// throwaway test: 20 simulated frames -> 20 renders + 20 setItem calls, 1:1).
// `debouncedWriter` in useElectionStore.tsx now defers the actual write by
// DEBOUNCE_MS so a whole gesture produces exactly one write, carrying only the
// FINAL value. This file is a separate test file (not appended to
// useElectionStore.test.ts) so it gets its own fresh module registry/jsdom
// environment -- fake timers here can't race a real setTimeout left pending
// by an unrelated test sharing the same module-level writer singleton.

const LS_CONFIG_KEY = 'votelab_election_config';
const LS_PLAYGROUND_KEY = 'votelab_playground';

beforeEach(() => {
  localStorage.clear();
  useElectionStore.setState({
    config: { ...DEFAULT_CONFIG },
    playground: { ...DEFAULT_PLAYGROUND },
    scenarioMeta: null,
  });
  vi.useFakeTimers();
});

afterEach(() => {
  // Drain anything still pending so it can't leak a real/fake timer into the
  // next test.
  vi.runOnlyPendingTimers();
  vi.useRealTimers();
  // vi.spyOn(Storage.prototype, 'setItem') patches a SHARED prototype, so
  // without this its mock.calls would accumulate across every `it` in this
  // file (each test re-spying on the same already-spied method).
  vi.restoreAllMocks();
});

describe('useElectionStore — debounced localStorage persistence (config)', () => {
  it('coalesces a rapid sequence of setConfig calls (a drag/slider gesture) into ONE write', () => {
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem');

    // 20 simulated drag frames -- the exact shape LeaderCanvas's window
    // mousemove listener produces via moveCandidate -> setConfig({candidates})
    // on every native mousemove while dragging, unthrottled.
    for (let i = 0; i < 20; i++) {
      useElectionStore.getState().setConfig({ num_voters: 300 + i });
    }

    // In-memory state updates synchronously on every call, same as before...
    expect(useElectionStore.getState().config.num_voters).toBe(319);
    // ...but nothing has reached localStorage yet -- still inside the
    // debounce window, unlike the old synchronous-on-every-call behaviour.
    expect(setItemSpy).not.toHaveBeenCalled();

    vi.advanceTimersByTime(300);

    // Exactly one write for the whole 20-frame gesture, carrying the FINAL
    // value (not any of the 19 intermediate ones).
    const configWrites = setItemSpy.mock.calls.filter(([key]) => key === LS_CONFIG_KEY);
    expect(configWrites).toHaveLength(1);
    expect(JSON.parse(configWrites[0][1] as string).num_voters).toBe(319);
  });

  it('a single explicit setConfig call still eventually persists (debounce does not drop it)', () => {
    useElectionStore.getState().setConfig({ seed: 12345 });
    expect(localStorage.getItem(LS_CONFIG_KEY)).toBeNull();

    vi.advanceTimersByTime(300);

    expect(JSON.parse(localStorage.getItem(LS_CONFIG_KEY) as string).seed).toBe(12345);
  });

  it('flushes immediately on beforeunload, so a tab closed mid-gesture does not lose the final value', () => {
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem');
    useElectionStore.getState().setConfig({ num_voters: 777 });
    expect(setItemSpy).not.toHaveBeenCalled();

    // Simulates the tab closing/navigating away mid-debounce-window.
    window.dispatchEvent(new Event('beforeunload'));

    expect(setItemSpy).toHaveBeenCalledTimes(1);
    expect(JSON.parse(setItemSpy.mock.calls[0][1] as string).num_voters).toBe(777);

    // The debounce timer that would otherwise fire later must not double-write.
    vi.advanceTimersByTime(300);
    expect(setItemSpy).toHaveBeenCalledTimes(1);
  });

  it('flushes immediately on pagehide (mobile Safari does not reliably fire beforeunload)', () => {
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem');
    useElectionStore.getState().setConfig({ num_voters: 42 });

    window.dispatchEvent(new Event('pagehide'));

    expect(setItemSpy).toHaveBeenCalledTimes(1);
    expect(JSON.parse(setItemSpy.mock.calls[0][1] as string).num_voters).toBe(42);
  });
});

describe('useElectionStore — debounced localStorage persistence (playground)', () => {
  it('coalesces a rapid sequence of setElectorate calls (an ElectorateComposer slider drag) into ONE write', () => {
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem');

    // Same shape as dragging the correlation/noise range input: onChange fires
    // on every native `input` event while the thumb moves.
    for (let i = 0; i < 15; i++) {
      useElectionStore.getState().setElectorate({ noise: i / 15 });
    }

    expect(useElectionStore.getState().playground.electorate.noise).toBeCloseTo(14 / 15);
    expect(setItemSpy).not.toHaveBeenCalled();

    vi.advanceTimersByTime(300);

    const playgroundWrites = setItemSpy.mock.calls.filter(([key]) => key === LS_PLAYGROUND_KEY);
    expect(playgroundWrites).toHaveLength(1);
    expect(JSON.parse(playgroundWrites[0][1] as string).electorate.noise).toBeCloseTo(14 / 15);
  });
});
