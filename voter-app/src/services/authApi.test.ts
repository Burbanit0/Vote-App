import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import { registerUser, loginUser, googleLogin, fetchProfileData, fetchUserProfile } from './authApi';

const mockAxios = new MockAdapter(axios);
const BASE = 'http://localhost:4433';

const mockToken = 'test-jwt-token';
const mockUser = { id: 1, username: 'alice', role: 'User', access_token: mockToken };

describe('authApi', () => {
  beforeEach(() => {
    mockAxios.reset();
    localStorage.clear();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('registerUser', () => {
    it('returns user data on successful registration', async () => {
      mockAxios.onPost(`${BASE}/api/auth/register`).reply(200, mockUser);
      const result = await registerUser('alice', 'secret', 'User', 'Alice', 'Smith');
      expect(result).toEqual(mockUser);
    });

    it('throws on registration error', async () => {
      jest.spyOn(console, 'error').mockImplementation(() => {});
      mockAxios.onPost(`${BASE}/api/auth/register`).reply(400, { message: 'Username taken' });
      await expect(registerUser('alice', 'secret', 'User', 'A', 'S')).rejects.toThrow();
    });
  });

  describe('loginUser', () => {
    it('returns user data on successful login', async () => {
      mockAxios.onPost(`${BASE}/api/auth/login`).reply(200, mockUser);
      const result = await loginUser('alice', 'secret');
      expect(result).toEqual(mockUser);
    });

    it('throws on wrong password (401)', async () => {
      jest.spyOn(console, 'error').mockImplementation(() => {});
      mockAxios.onPost(`${BASE}/api/auth/login`).reply(401, { message: 'Invalid credentials' });
      await expect(loginUser('alice', 'wrong')).rejects.toThrow();
    });
  });

  describe('googleLogin', () => {
    it('returns user data on successful Google login', async () => {
      const mockUser = { access_token: 'jwt', username: 'googler', role: 'User' };
      mockAxios.onPost(`${BASE}/api/auth/google`).reply(200, mockUser);
      const result = await googleLogin('google-credential-token');
      expect(result).toEqual(mockUser);
    });

    it('throws on Google login error', async () => {
      jest.spyOn(console, 'error').mockImplementation(() => {});
      mockAxios.onPost(`${BASE}/api/auth/google`).reply(401, { message: 'Invalid token' });
      await expect(googleLogin('bad-token')).rejects.toThrow();
    });
  });

  describe('fetchProfileData', () => {
    it('returns profile with auth header', async () => {
      localStorage.setItem('user', JSON.stringify({ access_token: mockToken }));
      const profile = { id: 1, username: 'alice', role: 'User' };
      mockAxios.onGet(`${BASE}/api/auth/profile`).reply((config: any) => {
        const auth = config.headers?.Authorization;
        if (auth === `Bearer ${mockToken}`) return [200, profile];
        return [401, { message: 'Unauthorized' }];
      });
      const result = await fetchProfileData();
      expect(result).toEqual(profile);
    });

    it('throws when no token in localStorage', async () => {
      jest.spyOn(console, 'error').mockImplementation(() => {});
      localStorage.removeItem('user');
      await expect(fetchProfileData()).rejects.toThrow('No token found');
    });
  });

  describe('fetchUserProfile', () => {
    it('returns profile for given user id', async () => {
      localStorage.setItem('user', JSON.stringify({ access_token: mockToken }));
      const profile = { id: 2, username: 'bob', role: 'Admin' };
      mockAxios.onGet(`${BASE}/api/auth/2`).reply((config: any) => {
        const auth = config.headers?.Authorization;
        if (auth === `Bearer ${mockToken}`) return [200, profile];
        return [401, { message: 'Unauthorized' }];
      });
      const result = await fetchUserProfile(2);
      expect(result).toEqual(profile);
    });

    it('throws when no token in localStorage', async () => {
      jest.spyOn(console, 'error').mockImplementation(() => {});
      localStorage.removeItem('user');
      await expect(fetchUserProfile(1)).rejects.toThrow('No token found');
    });
  });
});
