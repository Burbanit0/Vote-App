vi.mock('../../api/client', () => ({ apiPost: vi.fn() }));

import { runProfileSimulate } from '../profileApi';
import { apiPost } from '../../api/client';
import { DEFAULT_CONFIG, DEFAULT_PLAYGROUND } from '../../stores/useElectionStore';

const apiPostMock = apiPost as unknown as ReturnType<typeof vi.fn>;

beforeEach(() => {
  apiPostMock.mockReset();
});

describe('runProfileSimulate', () => {
  it('defaults compute_strategic to false (the live, debounced call)', async () => {
    apiPostMock.mockResolvedValueOnce({ methods: {}, cycle_rate: 0 });

    await runProfileSimulate(DEFAULT_CONFIG, DEFAULT_PLAYGROUND);

    expect(apiPostMock).toHaveBeenCalledWith(
      '/api/v2/election/profile-simulate',
      expect.objectContaining({ compute_strategic: false, electorate: null })
    );
  });

  it('opts into the slow manipulability pass when computeStrategic is true', async () => {
    apiPostMock.mockResolvedValueOnce({ methods: {}, cycle_rate: 0 });

    await runProfileSimulate(DEFAULT_CONFIG, DEFAULT_PLAYGROUND, true);

    expect(apiPostMock).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ compute_strategic: true })
    );
  });

  it('serialises the composed-electorate community mixture when active', async () => {
    apiPostMock.mockResolvedValueOnce({ methods: {}, cycle_rate: 0 });
    const pg = {
      ...DEFAULT_PLAYGROUND,
      electorate: {
        ...DEFAULT_PLAYGROUND.electorate,
        mode: 'composed' as const,
        communities: [
          { id: 'a', label: 'A', x: 0.1, y: 0.2, spread: 0.1, weight: 1, turnout: 0.9 },
        ],
      },
    };

    await runProfileSimulate(DEFAULT_CONFIG, pg);

    const [, body] = apiPostMock.mock.calls[0];
    expect(body.electorate).toMatchObject({ mode: 'composed', communities: [{ id: 'a', z: 0 }] });
  });

  it('resolves to the backend result', async () => {
    const result = { methods: { plurality: { winner: 'A' } }, cycle_rate: 0.1 };
    apiPostMock.mockResolvedValueOnce(result);
    const out = await runProfileSimulate(DEFAULT_CONFIG, DEFAULT_PLAYGROUND);
    expect(out).toBe(result);
  });
});
