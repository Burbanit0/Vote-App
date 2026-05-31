/**
 * test/queryWrapper.tsx — render helper for components that use the $api hooks.
 *
 * The $api hooks (openapi-react-query) need a QueryClientProvider. In tests we
 * mock the openapi-fetch client (`jest.mock('../api/client')`) and let REAL
 * react-query drive the loading/success/error transitions — no MSW, no fetch
 * polyfill. `retry: false` makes errors surface on the first attempt; a fresh
 * client per render keeps tests isolated.
 *
 *   jest.mock('../../api/client');
 *   const { apiClient } = jest.requireMock('../../api/client');
 *   apiClient.POST.mockResolvedValue({ data: fixture });   // or { error: ... }
 *   renderWithQuery(<MyPanel />);
 */
import React from 'react';
import { render, type RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

export function makeTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
      mutations: { retry: false },
    },
  });
}

export function QueryWrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={makeTestQueryClient()}>
      {children}
    </QueryClientProvider>
  );
}

export function renderWithQuery(ui: React.ReactElement, options?: RenderOptions) {
  return render(ui, { wrapper: QueryWrapper, ...options });
}
