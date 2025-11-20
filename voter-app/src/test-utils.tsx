import React, { ReactNode } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { AuthProvider } from './context/AuthContext'; // Adjust the import path as needed

const AllTheProviders = ({ children }: { children: ReactNode }) => {
  return <AuthProvider>{children}</AuthProvider>;
};

const customRender = (ui: React.ReactElement, options?: Omit<RenderOptions, 'wrapper'>) =>
  render(ui, { wrapper: AllTheProviders, ...options });

// Re-export everything from @testing-library/react
export * from '@testing-library/react';

// Override the render method
export { customRender as render };
