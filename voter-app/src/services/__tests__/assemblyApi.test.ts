vi.mock('../../api/client', () => ({ apiPost: vi.fn() }));

import { runAssembly, runAssemblyScorecard, electoratePayload } from '../assemblyApi';
import { apiPost } from '../../api/client';
import { DEFAULT_CONFIG, DEFAULT_PLAYGROUND } from '../../stores/useElectionStore';

const apiPostMock = apiPost as unknown as ReturnType<typeof vi.fn>;

beforeEach(() => {
  apiPostMock.mockReset();
});

describe('electoratePayload', () => {
  it('returns null for a simple (non-composed) electorate', () => {
    expect(electoratePayload(DEFAULT_PLAYGROUND)).toBeNull();
  });

  it('serialises the community mixture when composed', () => {
    const pg = {
      ...DEFAULT_PLAYGROUND,
      electorate: {
        ...DEFAULT_PLAYGROUND.electorate,
        mode: 'composed' as const,
        communities: [
          { id: 'a', label: 'A', x: 0.2, y: -0.1, spread: 0.1, weight: 1, turnout: 0.9 },
        ],
      },
    };
    const payload = electoratePayload(pg);
    expect(payload).toMatchObject({ mode: 'composed', communities: [{ id: 'a', z: 0 }] });
  });
});

describe('runAssembly', () => {
  it('posts the shared electorate + assembly knobs and resolves the backend result', async () => {
    const result = { structure: 'pr', parties: [], assembly_size: 100 };
    apiPostMock.mockResolvedValueOnce(result);

    const out = await runAssembly(DEFAULT_CONFIG, DEFAULT_PLAYGROUND);

    expect(out).toBe(result);
    expect(apiPostMock).toHaveBeenCalledWith(
      '/api/v2/election/assembly',
      expect.objectContaining({
        parties: DEFAULT_CONFIG.candidates.map((c) => ({ name: c.name, x: c.x, y: c.y })),
        num_voters: DEFAULT_CONFIG.num_voters,
        structure: DEFAULT_PLAYGROUND.assembly.structure,
        electorate: null,
      })
    );
  });
});

describe('runAssemblyScorecard', () => {
  it('posts all three structures at once (no `structure` field) with 24 replications', async () => {
    const result = { replications: 24, structures: {} };
    apiPostMock.mockResolvedValueOnce(result);

    const out = await runAssemblyScorecard(DEFAULT_CONFIG, DEFAULT_PLAYGROUND);

    expect(out).toBe(result);
    const [path, body] = apiPostMock.mock.calls[0];
    expect(path).toBe('/api/v2/election/assembly-scorecard');
    expect(body).not.toHaveProperty('structure');
    expect(body).toMatchObject({ replications: 24 });
  });
});
