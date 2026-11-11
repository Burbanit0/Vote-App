import { renderHook, act } from '@testing-library/react';

import { useProfileDiagnostics } from './usePlaygroundData';
import { DEFAULT_CONFIG, DEFAULT_PLAYGROUND } from '../stores/useElectionStore';
import type { ElectionConfig, PlaygroundState } from '../stores/useElectionStore';

const runProfileSimulate = vi.hoisted(() => vi.fn());
vi.mock('../services/profileApi', () => ({ runProfileSimulate }));

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
    rerender({
      config: DEFAULT_CONFIG,
      playground: {
        ...DEFAULT_PLAYGROUND,
        assembly: { ...DEFAULT_PLAYGROUND.assembly, seats: 999 },
      },
    });
    await settle();
    expect(runProfileSimulate).toHaveBeenCalledTimes(1);
  });

  const cases: [
    string,
    (c: ElectionConfig, p: PlaygroundState) => [ElectionConfig, PlaygroundState],
  ][] = [
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
      'the composed electorate',
      (c, p) => [
        c,
        {
          ...p,
          electorate: {
            ...p.electorate,
            mode: p.electorate.mode === 'composed' ? 'simple' : 'composed',
          },
        },
      ],
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

  it('shows no result when the call fails', async () => {
    runProfileSimulate.mockRejectedValue(new Error('backend down'));
    const { result } = mount(DEFAULT_CONFIG, DEFAULT_PLAYGROUND);
    await settle();
    expect(result.current.result).toBeNull();
    expect(result.current.loading).toBe(false);
  });
});
