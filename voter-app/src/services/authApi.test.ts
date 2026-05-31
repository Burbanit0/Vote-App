import { registerUser, loginUser, googleLogin, fetchProfileData, fetchUserProfile } from './authApi';

// JSON calls go through apiGet/apiPost; the form-encoded login + its /users/me
// read use raw fetch — so we mock both transports.
jest.mock('../api/client', () => ({ apiGet: jest.fn(), apiPost: jest.fn(), apiDelete: jest.fn() }));
const { apiGet, apiPost } = jest.requireMock('../api/client') as {
  apiGet: jest.Mock; apiPost: jest.Mock;
};

const mockToken = 'test-jwt-token';

const v2Profile = {
  id: 1, username: 'alice', email: 'alice@vote-app.local',
  role: 'User', first_name: 'Alice', last_name: 'Smith',
  is_active: true, is_superuser: false, is_verified: true,
};

/** Build a minimal Response-like object for the global.fetch mock. */
function fetchOk(body: unknown, ok = true, status = 200): Response {
  return { ok, status, json: async () => body } as unknown as Response;
}

const fetchMock = jest.fn();

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  global.fetch = fetchMock as unknown as typeof fetch;
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe('authApi', () => {
  describe('registerUser', () => {
    it('calls register then login, returning merged user data', async () => {
      apiPost.mockResolvedValueOnce(v2Profile);                 // /auth/register
      fetchMock
        .mockResolvedValueOnce(fetchOk({ access_token: mockToken, token_type: 'bearer' })) // jwt/login
        .mockResolvedValueOnce(fetchOk(v2Profile));                                          // /users/me

      const result = await registerUser('alice', 'Strong-1!', 'User', 'Alice', 'Smith');
      expect(result.access_token).toBe(mockToken);
      expect(result.username).toBe('alice');
      expect(result.user_id).toBe(1);
      expect(apiPost).toHaveBeenCalledWith('/api/v2/auth/register', expect.objectContaining({ username: 'alice' }));
    });

    it('throws when register endpoint fails', async () => {
      jest.spyOn(console, 'error').mockImplementation(() => {});
      apiPost.mockRejectedValueOnce(new Error('400'));
      await expect(
        registerUser('alice', 'Strong-1!', 'User', 'A', 'S'),
      ).rejects.toThrow();
    });
  });

  describe('loginUser', () => {
    it('issues form-encoded login then hydrates /users/me', async () => {
      fetchMock
        .mockResolvedValueOnce(fetchOk({ access_token: mockToken, token_type: 'bearer' }))
        .mockResolvedValueOnce(fetchOk(v2Profile));

      const result = await loginUser('alice@vote-app.local', 'Strong-1!');
      expect(result.access_token).toBe(mockToken);
      expect(result.user_id).toBe(1);
      expect(result.role).toBe('User');

      // login POST is form-encoded
      const [, loginInit] = fetchMock.mock.calls[0];
      expect(loginInit.headers['Content-Type']).toBe('application/x-www-form-urlencoded');
      // /users/me carries the freshly-issued token explicitly
      const [, meInit] = fetchMock.mock.calls[1];
      expect(meInit.headers.Authorization).toBe(`Bearer ${mockToken}`);
    });

    it('throws on wrong password (400 from fastapi-users)', async () => {
      jest.spyOn(console, 'error').mockImplementation(() => {});
      fetchMock.mockResolvedValueOnce(fetchOk({}, false, 400));
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
      apiPost.mockResolvedValueOnce(backendResp);
      const result = await googleLogin('google-credential-token');
      expect(result.id).toBe(1);
      expect(result.user_id).toBe(1);
      expect(result.access_token).toBe('jwt');
      expect(result.username).toBe('googler');
      expect(result.first_name).toBe('Goo');
      expect(apiPost).toHaveBeenCalledWith('/api/v2/auth/google', { token: 'google-credential-token' });
    });

    it('throws on Google login error', async () => {
      jest.spyOn(console, 'error').mockImplementation(() => {});
      apiPost.mockRejectedValueOnce(new Error('401'));
      await expect(googleLogin('bad-token')).rejects.toThrow();
    });
  });

  describe('fetchProfileData', () => {
    it('returns profile through apiGet', async () => {
      localStorage.setItem('user', JSON.stringify({ access_token: mockToken }));
      apiGet.mockResolvedValueOnce(v2Profile);
      const result = await fetchProfileData();
      expect(result).toEqual(v2Profile);
      expect(apiGet).toHaveBeenCalledWith('/api/v2/users/me');
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
      apiGet.mockResolvedValueOnce(profile);
      const result = await fetchUserProfile(2);
      expect(result).toEqual(profile);
      expect(apiGet).toHaveBeenCalledWith('/api/v2/users/2');
    });

    it('throws when no token in localStorage', async () => {
      jest.spyOn(console, 'error').mockImplementation(() => {});
      localStorage.removeItem('user');
      await expect(fetchUserProfile(1)).rejects.toThrow('No token found');
    });
  });
});
