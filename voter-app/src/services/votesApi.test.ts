import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import { castVote, updateVote, deleteVote } from './votesApi';

const mockAxios = new MockAdapter(axios);

describe('votesApi', () => {
  beforeEach(() => {
    mockAxios.reset();
    Storage.prototype.getItem = jest.fn((key) => {
      if (key === 'user') {
        return JSON.stringify({ access_token: 'mock-token', user_id: 1 });
      }
      return null;
    });
  });

  describe('castVote', () => {
    it('should cast a vote successfully', async () => {
      const mockResponse = { id: 1, candidate_id: 1, election_id: 1 };
      mockAxios.onPost('http://localhost:4433/votes/elections/1').reply(200, mockResponse);
      const result = await castVote(1, 1);
      expect(result).toEqual(mockResponse);
    });
  });

  describe('updateVote', () => {
    it('should update a vote successfully', async () => {
      const mockResponse = { id: 1, candidate_id: 2 };
      mockAxios.onPut('http://localhost:4433/votes/1').reply(200, mockResponse);
      const result = await updateVote(1, { candidate_id: 2 });
      expect(result).toEqual(mockResponse);
    });
  });

  describe('deleteVote', () => {
    it('should delete a vote successfully', async () => {
      const mockResponse = { success: true };
      mockAxios.onDelete('http://localhost:4433/votes/1').reply(200, mockResponse);
      const result = await deleteVote(1);
      expect(result).toEqual(mockResponse);
    });
  });
});
