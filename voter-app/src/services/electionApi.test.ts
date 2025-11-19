import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import {
  createElection,
  fetchAllElections,
  fetchElectionById,
  fetchParticipants,
  addVoterToElection,
  addCandidateToElection,
  fetchUserElectionList,
  isParticipating,
  cancelElectionParticipation,
  fetchElectionResults,
  updateElection,
  deleteElection,
} from './electionsApi';

const mockAxios = new MockAdapter(axios);

describe('electionsApi', () => {
  beforeEach(() => {
    mockAxios.reset();
    // Mock localStorage
    Storage.prototype.getItem = jest.fn((key) => {
      if (key === 'user') {
        return JSON.stringify({ access_token: 'mock-token', user_id: 1, role: 'user' });
      }
      return null;
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('createElection', () => {
    it('should create an election successfully', async () => {
      const mockResponse = { id: 1, name: 'Test Election' };
      mockAxios.onPost('http://localhost:4433/elections').reply(200, mockResponse);

      const result = await createElection('Test Election', 'Description', '2025-12-01', '2025-12-31');
      expect(result).toEqual(mockResponse);
    });

    it('should throw an error if the request fails', async () => {
      mockAxios.onPost('http://localhost:4433/elections').reply(500);

      await expect(createElection('Test Election', 'Description', '2025-12-01', '2025-12-31')).rejects.toThrow();
    });
  });

  describe('fetchAllElections', () => {
    it('should fetch all elections successfully', async () => {
      const mockResponse = { data: [], total: 0, page: 1, totalPages: 1 };
      mockAxios.onGet('http://localhost:4433/elections').reply(200, mockResponse);

      const result = await fetchAllElections(1, '', '', '', '');
      expect(result).toEqual(mockResponse);
    });

    it('should throw an error if the request fails', async () => {
      mockAxios.onGet('http://localhost:4433/elections').reply(500);

      await expect(fetchAllElections(1, '', '', '', '')).rejects.toThrow();
    });
  });

  describe('fetchElectionById', () => {
    it('should fetch an election by ID successfully', async () => {
      const mockResponse = { id: 1, name: 'Test Election' };
      mockAxios.onGet('http://localhost:4433/elections/1').reply(200, mockResponse);

      const result = await fetchElectionById(1);
      expect(result).toEqual(mockResponse);
    });

    it('should throw an error if the request fails', async () => {
      mockAxios.onGet('http://localhost:4433/elections/1').reply(500);

      await expect(fetchElectionById(1)).rejects.toThrow();
    });
  });

  describe('fetchParticipants', () => {
    it('should fetch participants successfully', async () => {
      const mockResponse = [{ id: 1, name: 'Participant 1' }];
      mockAxios.onGet('http://localhost:4433/elections/1/participants').reply(200, mockResponse);

      const result = await fetchParticipants(1);
      expect(result).toEqual(mockResponse);
    });

    it('should throw an error if the request fails', async () => {
      mockAxios.onGet('http://localhost:4433/elections/1/participants').reply(500);

      await expect(fetchParticipants(1)).rejects.toThrow();
    });
  });

  describe('addVoterToElection', () => {
    it('should add a voter to an election successfully', async () => {
      const mockResponse = { success: true };
      mockAxios.onPost('http://localhost:4433/elections/1/participate').reply(200, mockResponse);

      const result = await addVoterToElection(1);
      expect(result).toEqual(mockResponse);
    });

    it('should throw an error if the request fails', async () => {
      mockAxios.onPost('http://localhost:4433/elections/1/participate').reply(500);

      await expect(addVoterToElection(1)).rejects.toThrow();
    });
  });

  describe('addCandidateToElection', () => {
    it('should add a candidate to an election successfully', async () => {
      const mockResponse = { success: true };
      mockAxios.onPost('http://localhost:4433/elections/1/register-candidate').reply(200, mockResponse);

      const result = await addCandidateToElection(1);
      expect(result).toEqual(mockResponse);
    });

    it('should throw an error if the request fails', async () => {
      mockAxios.onPost('http://localhost:4433/elections/1/register-candidate').reply(500);

      await expect(addCandidateToElection(1)).rejects.toThrow();
    });
  });

  describe('fetchUserElectionList', () => {
    it('should fetch user election list successfully', async () => {
      const mockResponse = [{ id: 1, name: 'Test Election' }];
      mockAxios.onGet('http://localhost:4433/elections/users/1/elections').reply(200, mockResponse);

      const result = await fetchUserElectionList(1);
      expect(result).toEqual(mockResponse);
    });

    it('should throw an error if the request fails', async () => {
      mockAxios.onGet('http://localhost:4433/elections/users/1/elections').reply(500);

      await expect(fetchUserElectionList(1)).rejects.toThrow();
    });
  });

  describe('isParticipating', () => {
    it('should check participation status successfully', async () => {
      const mockResponse = { isParticipating: true };
      mockAxios.onGet('http://localhost:4433/elections/1/participation').reply(200, mockResponse);

      const result = await isParticipating(1);
      expect(result).toEqual(mockResponse);
    });

    it('should throw an error if the request fails', async () => {
      mockAxios.onGet('http://localhost:4433/elections/1/participation').reply(500);

      await expect(isParticipating(1)).rejects.toThrow();
    });
  });

  describe('cancelElectionParticipation', () => {
    it('should cancel participation successfully', async () => {
      const mockResponse = { success: true };
      mockAxios.onPost('http://localhost:4433/elections/1/cancel-participation').reply(200, mockResponse);

      const result = await cancelElectionParticipation(1);
      expect(result).toEqual(mockResponse);
    });

    it('should throw an error if the request fails', async () => {
      mockAxios.onPost('http://localhost:4433/elections/1/cancel-participation').reply(500);

      await expect(cancelElectionParticipation(1)).rejects.toThrow();
    });
  });

  describe('fetchElectionResults', () => {
    it('should fetch election results successfully', async () => {
      const mockResponse = { results: [] };
      mockAxios.onGet('http://localhost:4433/elections/1/results').reply(200, mockResponse);

      const result = await fetchElectionResults(1);
      expect(result).toEqual(mockResponse);
    });

    it('should throw an error if the request fails', async () => {
      mockAxios.onGet('http://localhost:4433/elections/1/results').reply(500);

      await expect(fetchElectionResults(1)).rejects.toThrow();
    });
  });

  describe('updateElection', () => {
    it('should update an election successfully', async () => {
      const mockResponse = { election: { id: 1, name: 'Updated Election' } };
      mockAxios.onPut('http://localhost:4433/elections/1').reply(200, mockResponse);

      const result = await updateElection(1, { name: 'Updated Election' });
      expect(result).toEqual(mockResponse.election);
    });

    it('should throw an error if the request fails', async () => {
      mockAxios.onPut('http://localhost:4433/elections/1').reply(500);

      await expect(updateElection(1, { name: 'Updated Election' })).rejects.toThrow();
    });
  });

  describe('deleteElection', () => {
    it('should delete an election successfully', async () => {
      const mockResponse = { success: true };
      mockAxios.onDelete('http://localhost:4433/elections/1').reply(200, mockResponse);

      const result = await deleteElection(1);
      expect(result).toEqual(mockResponse);
    });

    it('should throw an error if the request fails', async () => {
      mockAxios.onDelete('http://localhost:4433/elections/1').reply(500);

      await expect(deleteElection(1)).rejects.toThrow();
    });
  });
});
