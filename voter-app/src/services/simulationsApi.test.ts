import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import {
  simulateVote,
  simulateVoters,
  simulateCandidates,
  simulateUtility,
  getUtilityMatrix,
  getVoterSegments,
  closestCandidate,
} from './simulationsApi';

const mockAxios = new MockAdapter(axios);

describe('simulationsApi', () => {
  beforeEach(() => {
    mockAxios.reset();
  });

  describe('simulateVote', () => {
    it('should simulate a vote successfully', async () => {
      const mockResponse = { success: true };
      mockAxios.onPost('http://localhost:4433/simulations').reply(200, mockResponse);
      const result = await simulateVote({} as any);
      expect(result).toEqual(mockResponse);
    });
  });

  describe('simulateVoters', () => {
    it('should simulate voters successfully', async () => {
      const mockResponse = { success: true };
      mockAxios.onPost('http://localhost:4433/simulations/simulate_voters').reply(200, mockResponse);
      const result = await simulateVoters(10);
      expect(result).toEqual(mockResponse);
    });
  });

  describe('simulateCandidates', () => {
    it('should simulate candidates successfully', async () => {
      const mockResponse = { success: true };
      mockAxios.onPost('http://localhost:4433/simulations/simulate_candidates').reply(200, mockResponse);
      const result = await simulateCandidates(5, ['issue1'], ['party1']);
      expect(result).toEqual(mockResponse);
    });
  });

  describe('simulateUtility', () => {
    it('should simulate utility successfully', async () => {
      const mockResponse = { success: true };
      mockAxios.onPost('http://localhost:4433/simulations/simulate_utility').reply(200, mockResponse);
      const result = await simulateUtility(['issue1'], [], []);
      expect(result).toEqual(mockResponse);
    });
  });

  describe('getUtilityMatrix', () => {
    it('should get utility matrix successfully', async () => {
      const mockResponse = { matrix: [] };
      mockAxios.onPost('http://localhost:4433/simulations/get_utility_matrix').reply(200, mockResponse);
      const result = await getUtilityMatrix([], [], ['issue1']);
      expect(result).toEqual(mockResponse);
    });
  });

  describe('getVoterSegments', () => {
    it('should get voter segments successfully', async () => {
      const mockResponse = { segments: [] };
      mockAxios.onPost('http://localhost:4433/simulations/get_voter_segments').reply(200, mockResponse);
      const result = await getVoterSegments([], [], ['issue1']);
      expect(result).toEqual(mockResponse);
    });
  });

  describe('closestCandidate', () => {
    it('should get closest candidate successfully', async () => {
      const mockResponse = { result: { candidate_id: 1 } };
      mockAxios.onPost('http://localhost:4433/simulations/get_closest_candidate').reply(200, mockResponse);
      const result = await closestCandidate([1], [1]);
      expect(result).toEqual(mockResponse.result);
    });
  });
});
