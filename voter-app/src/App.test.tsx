import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';
import '@testing-library/jest-dom';

// Mock the AuthGuard component
jest.mock('./context/AuthGuard', () => ({
  __esModule: true,
   default: ({ component: Component }: { component: React.ComponentType<any> }) => <Component />,
}));

// Mock the Navbar component
jest.mock('./components/Navbar', () => ({
  __esModule: true,
  default: () => <div>Navbar</div>,
}));

// Mock other components as needed
jest.mock('./pages/HomePage', () => () => <div>HomePage</div>);
jest.mock('./pages/Login', () => () => <div>Login</div>);

describe('App Component', () => {
  it('renders the Navbar on non-login and non-register routes', () => {
    render(<App />);
    expect(screen.getByText('Navbar')).toBeInTheDocument();
  });

  it('does not render the Navbar on login and register routes', () => {
    // Use MemoryRouter to simulate route changes
    window.history.pushState({}, 'Test page', '/login');
    render(<App />);
    expect(screen.queryByText('Navbar')).not.toBeInTheDocument();
  });

  it('renders the Login component on the /login route', () => {
    window.history.pushState({}, 'Test page', '/login');
    render(<App />);
    expect(screen.getByText('Login')).toBeInTheDocument();
  });

  it('renders the HomePage component on the / route', () => {
    window.history.pushState({}, 'Test page', '/');
    render(<App />);
    expect(screen.getByText('HomePage')).toBeInTheDocument();
  });
});
