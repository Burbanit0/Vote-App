import React, { ReactNode } from 'react';
import { render, RenderOptions } from '@testing-library/react';

// Auth + other former contexts are now store-backed (Zustand, self-hydrating),
// so no provider wrapper is needed.
const AllTheProviders = ({ children }: { children: ReactNode }) => <>{children}</>;

const customRender = (ui: React.ReactElement, options?: Omit<RenderOptions, 'wrapper'>) =>
  render(ui, { wrapper: AllTheProviders, ...options });

// Re-export everything from @testing-library/react
export * from '@testing-library/react';

// Override the render method
export { customRender as render };
