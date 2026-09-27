import { getMonteCarlo, getVoteSteps } from './simulationCompareApi';

vi.mock('../api/client', () => ({ apiPost: vi.fn() }));
const { apiPost } = (await import('../api/client')) as unknown as { apiPost: jest.Mock };

beforeEach(() => {
  vi.clearAllMocks();
});

describe('simulationCompareApi', () => {
  it('getMonteCarlo posts to /monte-carlo and resolves the result', async () => {
    const response = { num_runs: 100, methods: {} };
    apiPost.mockResolvedValueOnce(response);
    const result = await getMonteCarlo({ num_runs: 100 });
    expect(result).toEqual(response);
    expect(apiPost).toHaveBeenCalledWith('/api/v2/simulations/monte-carlo', expect.any(Object));
  });

  it('getVoteSteps posts to /vote-steps and resolves the result', async () => {
    const response = { method: 'irv' };
    apiPost.mockResolvedValueOnce(response);
    const result = await getVoteSteps({
      method: 'irv',
      num_voters: 100,
      candidates: ['A', 'B'],
      ideology: 'random',
      seed: 1,
    });
    expect(result).toEqual(response);
    expect(apiPost).toHaveBeenCalledWith('/api/v2/simulations/vote-steps', expect.any(Object));
  });
});
