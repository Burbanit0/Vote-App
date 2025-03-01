import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface AuthContextType {
  user: { id: number; role: 'Voter' | 'Admin' } | null;
  login: (userData: { token: string; role: 'Voter' | 'Admin' }) => void;
  logout: () => void;
  loading: boolean; // Add a loading state
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<{ id: number; role: 'Voter' | 'Admin' } | null>(null);
  const [loading, setLoading] = useState(true); // Initialize loading state

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      try {
        const role = extractRoleFromToken(token);
        setUser({ id: 1, role }); // Assuming you have a way to get the user ID
      } catch (error) {
        console.error('Error extracting role from token:', error);
      } finally {
        setLoading(false); // Set loading to false after attempting to fetch user data
      }
    } else {
      setLoading(false); // Set loading to false if no token is found
    }
  }, []);

  const login = (userData: { token: string; role: 'Voter' | 'Admin' }) => {
    localStorage.setItem('token', userData.token);
    setUser({ id: 1, role: userData.role }); // Assuming you have a way to get the user ID
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Function to extract role from JWT token
const extractRoleFromToken = (token: string): 'Voter' | 'Admin' => {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    console.log('Token payload:', payload); // Debugging information
    if (payload.sub.role === 'Voter' || payload.sub.role === 'Admin') {
      return payload.sub.role;
    } else {
      throw new Error('Invalid role in token');
    }
  } catch (error) {
    console.error('Error extracting role from token:', error);
    throw error;
  }
};
