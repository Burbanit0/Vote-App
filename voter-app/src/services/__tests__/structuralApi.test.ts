vi.mock('../../api/client', () => ({ apiPost: vi.fn() }));

import { runStructuralFairness } from '../structuralApi';
import { apiPost } from '../../api/client';
import { DEFAULT_CONFIG, DEFAULT_PLAYGROUND } from '../../stores/useElectionStore';

const apiPostMock = apiPost as unknown as ReturnType<typeof vi.fn>;

beforeEach(() => {
  apiPostMock.mockReset();
});

describe('runStructuralFairness', () => {
  it('posts the districting/malapportionment knobs with their defaults', async () => {
    const result = { districts: 20, malapportionment: {}, efficiency_gap: {} };
    apiPostMock.mockResolvedValueOnce(result);

    const out = await runStructuralFairness(DEFAULT_CONFIG, 2.0);

    expect(out).toBe(result);
    expect(apiPostMock).toHaveBeenCalledWith(
      '/api/v2/election/structural-fairness',
      expect.objectContaining({
        malapportionment: 2.0,
        districts: 20,
        at_large_seats: 5,
        electorate: null,
      })
    );
  });

  it('forwards explicit districts/at-large overrides and the shared electorate', async () => {
    apiPostMock.mockResolvedValueOnce({});

    await runStructuralFairness(DEFAULT_CONFIG, 1.5, 10, 3, DEFAULT_PLAYGROUND);

    expect(apiPostMock).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ districts: 10, at_large_seats: 3, electorate: null })
    );
  });
});
