import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from './../context/AuthContext';
import { loginUser } from './../services/api';

const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const userData = await loginUser(username, password);
      console.log(userData);
      login(userData);
      alert('Login successful!');
      navigate('/'); // Redirect to home or another page after login
    } catch (error) {
      alert('Login failed. Please check your credentials.');
    }
  };

  const handleRegisterClick = () => {
    navigate('/register');
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Username"
          required
        />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          required
        />
        <button type="submit">Login</button>
      </form>
      <button onClick={handleRegisterClick}>Don't have an account? Register</button>
    </div>
  );
};

export default Login;
