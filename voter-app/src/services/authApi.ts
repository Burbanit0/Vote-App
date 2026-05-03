import axios from 'axios';
import { ParticipationData, Profile_, UserPermissions } from '../types';

const API_BASE_URL = 'http://localhost:4433';

// Function to register a new user
export const registerUser = async (
  username: string,
  password: string,
  role: 'User' | 'Admin',
  first_name: string,
  last_name: string
) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/auth/register`, {
      username,
      password,
      role,
      first_name,
      last_name,
    });
    return response.data;
  } catch (error) {
    console.error('Error registering user:', error);
    throw error;
  }
};

// Function to log in a user
export const loginUser = async (username: string, password: string) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/auth/login`, {
      username,
      password,
    });
    // Extract the token and role from the response
    const user = response.data;
    return user;
  } catch (error) {
    console.error('Error logging in user:', error);
    throw error;
  }
};

export const fetchProfileData = async () => {
  const storedUserJSON = localStorage.getItem('user');
  let token = '';
  let storedUser: { access_token: string } | null = null;

  if (storedUserJSON !== null) {
    storedUser = JSON.parse(storedUserJSON);
  }

  if (storedUser !== null) {
    token = storedUser.access_token;
  } else {
    console.error('User data not found in localStorage.');
  }

  if (!token) {
    throw new Error('No token found');
  }

  try {
    // Make a GET request to the /api/auth/profile endpoint with the JWT token
    const response = await axios.get(`${API_BASE_URL}/api/auth/profile`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching the Profile:', error);
    throw new Error('Failed to fetch profile data. Please check your login status.');
  }
};

export const fetchUserProfile = async (id: number): Promise<Profile_> => {
  const storedUserJSON = localStorage.getItem('user');
  let token = '';
  let storedUser: { access_token: string } | null = null;

  if (storedUserJSON !== null) {
    storedUser = JSON.parse(storedUserJSON);
  }

  if (storedUser !== null) {
    token = storedUser.access_token;
  } else {
    console.error('User data not found in localStorage.');
  }

  if (!token) {
    throw new Error('No token found');
  }

  try {
    const response = await axios.get(`${API_BASE_URL}/api/auth/${id}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching the user profile', error);
    throw new Error('Failed to fetch profile data. Please check your login status.');
  }
};

export const checkPermissions = async (): Promise<UserPermissions> => {
  const storedUserJSON = localStorage.getItem('user');
  let token = '';
  let storedUser: { access_token: string } | null = null;

  if (storedUserJSON !== null) {
    storedUser = JSON.parse(storedUserJSON);
  }

  if (storedUser !== null) {
    token = storedUser.access_token;
  } else {
    console.error('User data not found in localStorage.');
  }

  if (!token) {
    throw new Error('No token found');
  }

  try {
    const response = await axios.get(`${API_BASE_URL}/api/auth/users/me/permissions`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching the user permission', error);
    throw error;
  }
};

export const getParticipation = async (): Promise<ParticipationData> => {
  const storedUserJSON = localStorage.getItem('user');
  let token = '';
  let storedUser: { access_token: string } | null = null;

  if (storedUserJSON !== null) {
    storedUser = JSON.parse(storedUserJSON);
  }

  if (storedUser !== null) {
    token = storedUser.access_token;
  } else {
    console.error('User data not found in localStorage.');
  }

  if (!token) {
    throw new Error('No token found');
  }

  try {
    const response = await axios.get(`${API_BASE_URL}/api/auth/users/me/participation`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching the user participation', error);
    throw error;
  }
};
