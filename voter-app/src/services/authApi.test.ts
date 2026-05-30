import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import { registerUser, loginUser, googleLogin, fetchProfileData, fetchUserProfile } from './authApi';

const mockAxios = new MockAdapter(axios);
const BASE = 'http://localhost:4434';

const mockToken = 'test-jwt-token';

// Phase 4.3.e: all auth endpoints moved under /api/v2/*.
//   - register   POST /api/v2/auth/register    → UserRead (no token)
//   - login      POST /api/v2/auth/jwt/login   form-encoded → {access_token}
//   - me         GET  /api/v2/users/me         needs Bearer header
//   - google     POST /api/v2/auth/google      JSON {token}
//   - by id      GET  /api/v2/users/{id}       needs Bearer header

const v2Profile = {
  id: 1, username: 'alice', email: 'alice@vote-app.local',
  role: 'User', first_name: 'Alice', last_name: 'Smith',
  is_active: true, is_superuser: false, is_verified: true,
};

describe('authApi', () => {
  beforeEach(() => {
    mockAxios.reset();
    localStorage.clear();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('registerUser', () => {
    it('calls register then login, returning merged user data', async () => {
      mockAxios.onPost(`${BASE}/api/v2/auth/register`).reply(201, v2Profile);
      mockAxios.onPost(`${BASE}/api/v2/auth/jwt/login`).reply(200, {
        access_token: mockToken, token_type: 'bearer',
      });
      mockAxios.onGet(`${BASE}/api/v2/users/me`).reply(200, v2Profile);

      const result = await registerUser('alice', 'Strong-1!', 'User', 'Alice', 'Smith');
      expect(result.access_token).toBe(mockToken);
      expect(result.username).toBe('alice');
      expect(result.user_id).toBe(1);
    });

    it('throws when register endpoint fails', async () => {
      jest.spyOn(console, 'error').mockImplementation(() => {});
      mockAxios.onPost(`${BASE}/api/v2/auth/register`).reply(400);
      await expect(
        registerUser('alice', 'Strong-1!', 'User', 'A', 'S'),
      ).rejects.toThrow();
    });
  });

  describe('loginUser', () => {
    it('issues form-encoded login then hydrates /users/me', async () => {
      mockAxios.onPost(`${BASE}/api/v2/auth/jwt/login`).reply((config: any) => {
        const ct = config.headers?.['Content-Type'];
        expect(ct).toBe('application/x-www-form-urlencoded');
        return [200, { access_token: mockToken, token_type: 'bearer' }];
      });
      mockAxios.onGet(`${BASE}/api/v2/users/me`).reply(200, v2Profile);

      const result = await loginUser('alice@vote-app.local', 'Strong-1!');
      expect(result.access_token).toBe(mockToken);
      expect(result.user_id).toBe(1);
      expect(result.role).toBe('User');
    });

    it('throws on wrong password (400 from fastapi-users)', async () => {
      jest.spyOn(console, 'error').mockImplementation(() => {});
      mockAxios.onPost(`${BASE}/api/v2/auth/jwt/login`).reply(400);
      await expect(
        loginUser('alice@vote-app.local', 'wrong'),
      ).rejects.toThrow();
    });
  });

  describe('googleLogin', () => {
    it('returns user data on successful Google login', async () => {
      const backendResp = { access_token: 'jwt', user_id: 1,
                            username: 'googler', role: 'User',
                            first_name: 'Goo', last_name: 'Gler' };
      mockAxios.onPost(`${BASE}/api/v2/auth/google`).reply(200, backendResp);
      const result = await googleLogin('google-credential-token');
      expect(result.id).toBe(1);
      expect(result.user_id).toBe(1);
      expect(result.access_token).toBe('jwt');
      expect(result.username).toBe('googler');
      expect(result.first_name).toBe('Goo');
    });

    it('throws on Google login error', async () => {
      jest.spyOn(console, 'error').mockImplementation(() => {});
      mockAxios.onPost(`${BASE}/api/v2/auth/google`).reply(401);
      await expect(googleLogin('bad-token')).rejects.toThrow();
    });
  });

  describe('fetchProfileData', () => {
    it('returns profile with auth header', async () => {
      localStorage.setItem('user', JSON.stringify({ access_token: mockToken }));
      mockAxios.onGet(`${BASE}/api/v2/users/me`).reply((config: any) => {
        const auth = config.headers?.Authorization;
        if (auth === `Bearer ${mockToken}`) return [200, v2Profile];
        return [401, {}];
      });
      const result = await fetchProfileData();
      expect(result).toEqual(v2Profile);
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
      const profile = { ...v2Profile, id: 2, username: 'bob', role: 'Admin' };
      mockAxios.onGet(`${BASE}/api/v2/users/2`).reply((config: any) => {
        const auth = config.headers?.Authorization;
        if (auth === `Bearer ${mockToken}`) return [200, profile];
        return [401, {}];
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
