import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import {
  fetchCandidateResults,
  fetchAllResults,
  fetchCondorcetWinner,
  fetchTwoRoundWinner,
} from './resultsApi';

const mockAxios = new MockAdapter(axios);

describe('resultsApi', () => {
  beforeEach(() => {
    mockAxios.reset();
  });

  describe('fetchCandidateResults', () => {
    it('should fetch candidate results successfully', async () => {
      const mockResponse = [{ id: 1, candidate_id: 1, votes: 100 }];
      mockAxios.onGet('http://localhost:4433/candidates/1/results').reply(200, mockResponse);
      const result = await fetchCandidateResults(1);
      expect(result).toEqual(mockResponse);
    });
  });

  describe('fetchAllResults', () => {
    it('should fetch all results successfully', async () => {
      const mockResponse = [{ id: 1, candidate_id: 1, votes: 100 }];
      mockAxios.onGet('http://localhost:4433/results').reply(200, mockResponse);
      const result = await fetchAllResults();
      expect(result).toEqual(mockResponse);
    });
  });

  describe('fetchCondorcetWinner', () => {
    it('should fetch Condorcet winner successfully', async () => {
      const mockResponse = { id: 1, name: 'Winner' };
      mockAxios.onGet('http://localhost:4433/results/condorcet').reply(200, mockResponse);
      const result = await fetchCondorcetWinner();
      expect(result).toEqual(mockResponse);
    });
  });

  describe('fetchTwoRoundWinner', () => {
    it('should fetch two-round winner successfully', async () => {
      const mockResponse = { id: 1, name: 'Winner' };
      mockAxios.onGet('http://localhost:4433/results/two-round').reply(200, mockResponse);
      const result = await fetchTwoRoundWinner();
      expect(result).toEqual(mockResponse);
    });
  });
});
