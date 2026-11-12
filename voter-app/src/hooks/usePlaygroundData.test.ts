import { renderHook, act } from '@testing-library/react';

import { useAssembly, useProfileDiagnostics } from './usePlaygroundData';
import { DEFAULT_CONFIG, DEFAULT_PLAYGROUND } from '../stores/useElectionStore';
import type { ElectionConfig, PlaygroundState } from '../stores/useElectionStore';

const runProfileSimulate = vi.hoisted(() => vi.fn());
const runAssembly = vi.hoisted(() => vi.fn());
vi.mock('../services/profileApi', () => ({ runProfileSimulate }));
vi.mock('../services/assemblyApi', () => ({ runAssembly }));

// The live diagnostics (cycle rate, turnout, winner flips) must refetch whenever an input
// the request actually carries changes. The key used to be a hand-picked list that left
// out turnout, the composed electorate and a candidate's depth, so those edits left the
// numbers on screen stale. It is now the request body itself.

const DEBOUNCE = 350;

function mount(config: ElectionConfig, playground: PlaygroundState) {
  return renderHook(
    (p: { config: ElectionConfig; playground: PlaygroundState }) =>
      useProfileDiagnostics(p.config, p.playground),
    { initialProps: { config, playground } }
  );
}

async function settle() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(DEBOUNCE + 10);
  });
}

describe('useProfileDiagnostics', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    runProfileSimulate.mockReset();
    runProfileSimulate.mockResolvedValue({ cycle_rate: 0.1 });
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('fetches once on mount and exposes the result', async () => {
    const { result } = mount(DEFAULT_CONFIG, DEFAULT_PLAYGROUND);
    await settle();
    expect(runProfileSimulate).toHaveBeenCalledTimes(1);
    expect(result.current.result).toEqual({ cycle_rate: 0.1 });
    expect(result.current.loading).toBe(false);
  });

  it('does not refetch when the inputs are unchanged', async () => {
    const { rerender } = mount(DEFAULT_CONFIG, DEFAULT_PLAYGROUND);
    await settle();
    rerender({ config: { ...DEFAULT_CONFIG }, playground: { ...DEFAULT_PLAYGROUND } });
    await settle();
    expect(runProfileSimulate).toHaveBeenCalledTimes(1);
  });

  it('does not refetch for state the request does not carry', async () => {
    const { rerender } = mount(DEFAULT_CONFIG, DEFAULT_PLAYGROUND);
    await settle();
    const unrelated: PlaygroundState[] = [
      { ...DEFAULT_PLAYGROUND, assembly: { ...DEFAULT_PLAYGROUND.assembly, seats: 999 } },
      { ...DEFAULT_PLAYGROUND, stratShare: 0.9 },
      { ...DEFAULT_PLAYGROUND, blank: { ...DEFAULT_PLAYGROUND.blank, enabled: true } },
    ];
    for (const playground of unrelated) {
      rerender({ config: DEFAULT_CONFIG, playground });
      await settle();
    }
    expect(runProfileSimulate).toHaveBeenCalledTimes(1);
  });

  const composed = (
    p: PlaygroundState,
    edit: (c: PlaygroundState['electorate']['communities'][number]) => unknown = (c) => c
  ): PlaygroundState => ({
    ...p,
    electorate: {
      ...p.electorate,
      mode: 'composed',
      communities: p.electorate.communities.map((c, i) =>
        i === 0 ? { ...c, ...(edit(c) as object) } : c
      ),
    },
  });
  type Change = (c: ElectionConfig, p: PlaygroundState) => [ElectionConfig, PlaygroundState];
  const cases: [string, Change][] = [
    ['the preference source', (c, p) => [c, { ...p, prefSource: 'impartial' }]],
    ['the number of dimensions', (c, p) => [c, { ...p, space: { ...p.space, dims: 3 } }]],
    ['valence', (c, p) => [c, { ...p, space: { ...p.space, valenceEnabled: true } }]],
    ['the voter behaviour', (c, p) => [c, { ...p, behavior: 'strategic' }]],
    ['the preference parameters', (c, p) => [c, { ...p, prefParams: { alpha: 0.4 } }]],
    ['the ballot type', (c, p) => [c, { ...p, ballot: { ...p.ballot, type: 'rank_truncated' } }]],
    ['the score levels', (c, p) => [c, { ...p, ballot: { ...p.ballot, score_levels: 9 } }]],
    [
      'the turnout model',
      (c, p) => [c, { ...p, turnout: { model: 'alienation', intensity: p.turnout.intensity } }],
    ],
    [
      'the turnout intensity',
      (c, p) => [c, { ...p, turnout: { ...p.turnout, intensity: p.turnout.intensity + 0.2 } }],
    ],
    [
      "a candidate's depth",
      (c, p) => [
        { ...c, candidates: c.candidates.map((k, i) => (i === 0 ? { ...k, z: 0.7 } : k)) },
        p,
      ],
    ],
    [
      "a candidate's position",
      (c, p) => [
        { ...c, candidates: c.candidates.map((k, i) => (i === 0 ? { ...k, x: k.x + 0.3 } : k)) },
        p,
      ],
    ],
    ['the composed electorate switching on', (c, p) => [c, composed(p)]],
    [
      "a community's weight",
      (c, p) => [c, composed(composed(p), (k) => ({ weight: k.weight + 0.1 }))],
    ],
    ['the voter count', (c, p) => [{ ...c, num_voters: c.num_voters + 50 }, p]],
    ['the seed', (c, p) => [{ ...c, seed: (c.seed ?? 0) + 1 }, p]],
  ];

  it.each(cases)('refetches when %s changes', async (_name, change) => {
    const { rerender } = mount(DEFAULT_CONFIG, DEFAULT_PLAYGROUND);
    await settle();
    const [config, playground] = change(DEFAULT_CONFIG, DEFAULT_PLAYGROUND);
    rerender({ config, playground });
    await settle();
    expect(runProfileSimulate).toHaveBeenCalledTimes(2);
  });

  it('waits for the inputs to hold still, then fetches once', async () => {
    const { rerender } = mount(DEFAULT_CONFIG, DEFAULT_PLAYGROUND);
    await settle();
    runProfileSimulate.mockClear();
    for (const seed of [11, 12, 13]) {
      rerender({ config: { ...DEFAULT_CONFIG, seed }, playground: DEFAULT_PLAYGROUND });
      await act(async () => {
        await vi.advanceTimersByTimeAsync(DEBOUNCE - 100);
      });
    }
    expect(runProfileSimulate).not.toHaveBeenCalled();
    await settle();
    expect(runProfileSimulate).toHaveBeenCalledTimes(1);
    expect(runProfileSimulate.mock.calls[0][0]).toMatchObject({ seed: 13 });
  });

  it('drops a slow answer to inputs that have since changed', async () => {
    let answerOld!: (v: unknown) => void;
    runProfileSimulate.mockReset();
    runProfileSimulate
      .mockImplementationOnce(() => new Promise((res) => (answerOld = res)))
      .mockResolvedValueOnce({ cycle_rate: 0.9 });
    const { result, rerender } = mount(DEFAULT_CONFIG, DEFAULT_PLAYGROUND);
    await settle(); // the first request is in flight, unanswered
    rerender({ config: { ...DEFAULT_CONFIG, seed: 77 }, playground: DEFAULT_PLAYGROUND });
    await settle(); // the second one answers
    expect(result.current.result).toEqual({ cycle_rate: 0.9 });
    await act(async () => answerOld({ cycle_rate: 0.1 })); // the old one finally lands
    expect(result.current.result).toEqual({ cycle_rate: 0.9 });
  });

  it('shows no result when the call fails', async () => {
    runProfileSimulate.mockRejectedValue(new Error('backend down'));
    const { result } = mount(DEFAULT_CONFIG, DEFAULT_PLAYGROUND);
    await settle();
    expect(result.current.result).toBeNull();
    expect(result.current.loading).toBe(false);
  });
});

describe('useAssembly', () => {
  type AsmInput = { enabled: boolean; config: ElectionConfig; playground: PlaygroundState };
  const mountAsm = (i: AsmInput) =>
    renderHook((p: AsmInput) => useAssembly(p.config, p.playground, p.enabled), {
      initialProps: i,
    });
  const base: AsmInput = { enabled: true, config: DEFAULT_CONFIG, playground: DEFAULT_PLAYGROUND };

  beforeEach(() => {
    vi.useFakeTimers();
    runAssembly.mockReset();
    runAssembly.mockResolvedValue({ seats: [] });
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('does nothing while the parliament is not shown', async () => {
    mountAsm({ ...base, enabled: false });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    expect(runAssembly).not.toHaveBeenCalled();
  });

  it('fetches once when shown, and again when an input of the request changes', async () => {
    const { result, rerender } = mountAsm(base);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(400);
    });
    expect(runAssembly).toHaveBeenCalledTimes(1);
    expect(result.current.assembly).toEqual({ seats: [] });
    const changes: AsmInput[] = [
      {
        ...base,
        playground: {
          ...base.playground,
          assembly: { ...base.playground.assembly, threshold: 0.1 },
        },
      },
      {
        ...base,
        playground: { ...base.playground, turnout: { model: 'indifference', intensity: 0.5 } },
      },
      { ...base, config: { ...base.config, ideology: 'polarized' as ElectionConfig['ideology'] } },
    ];
    for (const next of changes) {
      runAssembly.mockClear();
      rerender(next);
      await act(async () => {
        await vi.advanceTimersByTimeAsync(400);
      });
      expect(runAssembly).toHaveBeenCalledTimes(1);
      rerender(base);
      await act(async () => {
        await vi.advanceTimersByTimeAsync(400);
      });
    }
  });

  it('does not refetch for state the request does not carry', async () => {
    const { rerender } = mountAsm(base);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(400);
    });
    rerender({
      ...base,
      playground: { ...base.playground, behavior: 'strategic', prefSource: 'impartial' },
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(400);
    });
    expect(runAssembly).toHaveBeenCalledTimes(1);
  });
});
