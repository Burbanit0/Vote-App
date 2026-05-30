import axios from 'axios';
import { Profile_, User } from '../types';

const API_BASE_URL = (process.env.VITE_API_URL) || 'http://localhost:4434';

// Phase 4.3.e: every route below now lives on /api/v2/* (fastapi-users).
//   - login is form-encoded (OAuth2 contract) with `username` carrying the email
//   - register requires an email field; if the caller doesn't supply one we
//     synthesise it from the legacy username so the existing Register form
//     keeps working until it grows an email field of its own
//   - profile reads through /api/v2/users/me; per-id reads through /users/{id}
//
// /api/v2/auth/jwt/login does NOT echo the user back in the response — only
// {access_token, token_type}. We fetch /users/me right after to populate the
// AuthContext, then merge token + profile into the user object the rest of
// the frontend already expects.

// Build a `User` object compatible with the existing AuthContext consumer.
// /users/me returns id + email + username + role; created_at is not echoed by
// fastapi-users so we leave it empty (callers don't use it for auth flow).
function profileToUser(profile: any, access_token: string): User {
  return {
    id:           profile.id,
    user_id:      profile.id,
    access_token,
    username:     profile.username,
    role:         profile.role,
    first_name:   profile.first_name || '',
    last_name:    profile.last_name  || '',
    created_at:   profile.created_at || '',
  };
}

const authHeaders = (token: string) => ({
  headers: { Authorization: `Bearer ${token}` },
});

const tokenFromStorage = (): string => {
  const raw = localStorage.getItem('user');
  if (!raw) throw new Error('No token found');
  const parsed = JSON.parse(raw) as { access_token?: string };
  if (!parsed.access_token) throw new Error('No token found');
  return parsed.access_token;
};

// ── Register ──────────────────────────────────────────────────────────────

export const registerUser = async (
  username: string,
  password: string,
  role: 'User' | 'Admin',
  first_name: string,
  last_name: string,
  email?: string,
): Promise<User> => {
  try {
    const effectiveEmail = email || `${username}@vote-app.local`;
    await axios.post(`${API_BASE_URL}/api/v2/auth/register`, {
      email: effectiveEmail,
      password,
      username,
      role,
      first_name,
      last_name,
    });
    // /register returns the UserRead — no token. Issue one immediately so
    // the existing UX (auto-login on register) keeps working.
    return await loginUser(effectiveEmail, password);
  } catch (error) {
    console.error('Error registering user:', error);
    throw error;
  }
};

// ── Login ─────────────────────────────────────────────────────────────────

export const loginUser = async (
  identifier: string,
  password: string,
): Promise<User> => {
  try {
    // fastapi-users JWT login expects application/x-www-form-urlencoded with
    // an OAuth2-shaped form (`username` field carries the email here).
    const form = new URLSearchParams();
    form.set('username', identifier);
    form.set('password', password);
    const tokenResp = await axios.post(
      `${API_BASE_URL}/api/v2/auth/jwt/login`,
      form,
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } },
    );
    const access_token: string = tokenResp.data.access_token;

    const me = await axios.get(`${API_BASE_URL}/api/v2/users/me`,
      authHeaders(access_token));
    return profileToUser(me.data, access_token);
  } catch (error) {
    console.error('Error logging in user:', error);
    throw error;
  }
};

// ── /users/me (own profile) ───────────────────────────────────────────────

export const fetchProfileData = async () => {
  const token = tokenFromStorage();   // surfaces "No token found" verbatim
  try {
    const response = await axios.get(
      `${API_BASE_URL}/api/v2/users/me`,
      authHeaders(token),
    );
    return response.data;
  } catch (error) {
    console.error('Error fetching the Profile:', error);
    throw new Error('Failed to fetch profile data. Please check your login status.');
  }
};

// ── /auth/google (ID-token exchange) ──────────────────────────────────────

export const googleLogin = async (credential: string): Promise<User> => {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/v2/auth/google`, {
      token: credential,
    });
    // Backend echoes {access_token, user_id, username, role, first_name, last_name}.
    // Coerce to the User shape the AuthContext expects.
    const data = response.data;
    return {
      id:           data.user_id,
      user_id:      data.user_id,
      access_token: data.access_token,
      username:     data.username,
      role:         data.role,
      first_name:   data.first_name || '',
      last_name:    data.last_name  || '',
      created_at:   '',
    };
  } catch (error) {
    console.error('Error logging in with Google:', error);
    throw error;
  }
};

// ── /users/{id} (admin / cross-user read) ─────────────────────────────────

export const fetchUserProfile = async (id: number): Promise<Profile_> => {
  const token = tokenFromStorage();   // surfaces "No token found" verbatim
  try {
    const response = await axios.get(
      `${API_BASE_URL}/api/v2/users/${id}`,
      authHeaders(token),
    );
    return response.data;
  } catch (error) {
    console.error('Error fetching the user profile', error);
    throw new Error('Failed to fetch profile data. Please check your login status.');
  }
};
