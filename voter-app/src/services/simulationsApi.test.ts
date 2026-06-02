import {
  simulateVote,
  simulateVoters,
  simulateCandidates,
  simulateUtility,
  getUtilityMatrix,
  getVoterSegments,
  closestCandidate,
} from './simulationsApi';

vi.mock('../api/client', () => ({ apiPost: vi.fn(), apiGet: vi.fn() }));
const { apiPost } = (await import('../api/client')) as unknown as { apiPost: jest.Mock };

describe('simulationsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('simulateVote', () => {
    it('should simulate a vote successfully', async () => {
      const mockResponse = { success: true };
      apiPost.mockResolvedValueOnce(mockResponse);
      const result = await simulateVote({} as any);
      expect(result).toEqual(mockResponse);
      expect(apiPost).toHaveBeenCalledWith('/api/v2/simulations', expect.any(Object));
    });
  });

  describe('simulateVoters', () => {
    it('should simulate voters successfully', async () => {
      const mockResponse = { voters: [] };
      apiPost.mockResolvedValueOnce(mockResponse);
      const result = await simulateVoters(10);
      expect(result).toEqual(mockResponse);
      expect(apiPost).toHaveBeenCalledWith(
        '/api/v2/simulations/simulate_voters',
        expect.objectContaining({ num_voters: 10 }),
      );
    });
  });

  describe('simulateCandidates', () => {
    it('should simulate candidates successfully', async () => {
      const mockResponse = { candidates: [] };
      apiPost.mockResolvedValueOnce(mockResponse);
      const result = await simulateCandidates(5, ['issue1'], ['party1']);
      expect(result).toEqual(mockResponse);
      expect(apiPost).toHaveBeenCalledWith(
        '/api/v2/simulations/simulate_candidates',
        expect.objectContaining({ num_candidates: 5 }),
      );
    });
  });

  describe('simulateUtility', () => {
    it('should simulate utility successfully', async () => {
      const mockResponse = { success: true };
      apiPost.mockResolvedValueOnce(mockResponse);
      const result = await simulateUtility(['issue1'], [], []);
      expect(result).toEqual(mockResponse);
      expect(apiPost).toHaveBeenCalledWith('/api/v2/simulations/simulate_utility', expect.any(Object));
    });
  });

  describe('getUtilityMatrix', () => {
    it('should get utility matrix successfully', async () => {
      const mockResponse = { matrix: [] };
      apiPost.mockResolvedValueOnce(mockResponse);
      const result = await getUtilityMatrix([], [], ['issue1']);
      expect(result).toEqual(mockResponse);
      expect(apiPost).toHaveBeenCalledWith('/api/v2/simulations/get_utility_matrix', expect.any(Object));
    });
  });

  describe('getVoterSegments', () => {
    it('should get voter segments successfully', async () => {
      const mockResponse = { segments: [] };
      apiPost.mockResolvedValueOnce(mockResponse);
      const result = await getVoterSegments([], [], ['issue1']);
      expect(result).toEqual(mockResponse);
      expect(apiPost).toHaveBeenCalledWith('/api/v2/simulations/get_voter_segments', expect.any(Object));
    });
  });

  describe('closestCandidate', () => {
    it('should get closest candidate successfully', async () => {
      const mockResponse = { result: { candidate_id: 1 } };
      apiPost.mockResolvedValueOnce(mockResponse);
      const result = await closestCandidate([1], [1]);
      expect(result).toEqual(mockResponse.result);
      expect(apiPost).toHaveBeenCalledWith('/api/v2/simulations/get_closest_candidate', expect.any(Object));
    });
  });
});
