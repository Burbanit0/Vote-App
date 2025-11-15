import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import {
  createParty,
  fetchMembers,
  removeUserFromParty,
  addUserFromParty,
  fetchAllParties,
  fetchPartyById,
  fetchUserParty,
} from './partiesApi';

const mockAxios = new MockAdapter(axios);

describe('partiesApi', () => {
  beforeEach(() => {
    mockAxios.reset();
    Storage.prototype.getItem = jest.fn((key) => {
      if (key === 'user') {
        return JSON.stringify({ access_token: 'mock-token', user_id: 1, role: 'user' });
      }
      return null;
    });
  });

  describe('createParty', () => {
    it('should create a party successfully', async () => {
      const mockResponse = { id: 1, name: 'Test Party' };
      mockAxios.onPost('http://localhost:4433/parties').reply(200, mockResponse);
      const result = await createParty('Test Party', 'Description');
      expect(result).toEqual(mockResponse);
    });

    it('should throw an error if the request fails', async () => {
      mockAxios.onPost('http://localhost:4433/parties').reply(500);
      await expect(createParty('Test Party', 'Description')).rejects.toThrow();
    });
  });

  describe('fetchMembers', () => {
    it('should fetch members successfully', async () => {
      const mockResponse = [{ id: 1, name: 'Member 1' }];
      mockAxios.onGet('http://localhost:4433/parties/1/users').reply(200, mockResponse);
      const result = await fetchMembers(1);
      expect(result).toEqual(mockResponse);
    });
  });

  describe('removeUserFromParty', () => {
    it('should remove a user from a party successfully', async () => {
      const mockResponse = { success: true };
      mockAxios.onPost('http://localhost:4433/parties/1/remove-party').reply(200, mockResponse);
      const result = await removeUserFromParty(1, 1);
      expect(result).toEqual(mockResponse);
    });
  });

  describe('addUserFromParty', () => {
    it('should add a user to a party successfully', async () => {
      const mockResponse = { success: true };
      mockAxios.onPost('http://localhost:4433/parties/1/assign-party').reply(200, mockResponse);
      const result = await addUserFromParty(1, 1);
      expect(result).toEqual(mockResponse);
    });
  });

  describe('fetchAllParties', () => {
    it('should fetch all parties successfully', async () => {
      const mockResponse = [{ id: 1, name: 'Party 1' }];
      mockAxios.onGet('http://localhost:4433/parties').reply(200, mockResponse);
      const result = await fetchAllParties();
      expect(result).toEqual(mockResponse);
    });
  });

  describe('fetchPartyById', () => {
    it('should fetch a party by ID successfully', async () => {
      const mockResponse = { id: 1, name: 'Party 1' };
      mockAxios.onGet('http://localhost:4433/parties/1').reply(200, mockResponse);
      const result = await fetchPartyById(1);
      expect(result).toEqual(mockResponse);
    });
  });

  describe('fetchUserParty', () => {
    it('should fetch the user party successfully', async () => {
      const mockResponse = { id: 1, name: 'User Party' };
      mockAxios.onGet('http://localhost:4433/api/auth/users/me/party').reply(200, mockResponse);
      const result = await fetchUserParty();
      expect(result).toEqual(mockResponse);
    });
  });
});
