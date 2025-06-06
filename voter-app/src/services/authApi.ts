import axios from 'axios';

const API_BASE_URL = 'http://localhost:4433';

// Function to register a new user
export const registerUser = async (username: string, password: string, role: 'Voter' | 'Admin', first_name: string, last_name: string) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/auth/register`, {
      username,
      password,
      role,
      first_name,
      last_name
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
  try {
    // Retrieve the JWT token from local storage
    const token = localStorage.getItem('access_token');

    if (!token) {
      throw new Error('No token found');
    }

    // Make a GET request to the /api/auth/profile endpoint with the JWT token
    const response = await axios.get(`${API_BASE_URL}/api/auth/profile`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    return response.data;
  } catch (error) {
    throw new Error('Failed to fetch profile data. Please check your login status.');
  }
};
