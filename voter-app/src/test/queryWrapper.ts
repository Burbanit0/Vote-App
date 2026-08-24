/**
 * test/queryWrapper.tsx — QueryClient factory for components using the $api hooks.
 *
 * The $api hooks (openapi-react-query) need a QueryClientProvider. In tests we
 * mock the openapi-fetch client and let REAL react-query drive the
 * loading/success/error transitions — no MSW, no fetch polyfill. `retry: false`
 * makes errors surface on the first attempt; a fresh client per render keeps
 * tests isolated.
 *
 *   vi.mock('../../api/client');
 *   const { apiClient } = await vi.importMock('../../api/client');
 *   apiClient.POST.mockResolvedValue({ data: fixture });   // or { error: ... }
 *   render(<QueryClientProvider client={makeTestQueryClient()}><MyPanel /></QueryClientProvider>);
 *
 * This file also used to export a <QueryWrapper> component and a renderWithQuery()
 * helper wrapping it. All 45 call sites reach for makeTestQueryClient directly and
 * wrap the provider themselves, so both were dead — and their docstring still
 * described the jest API this repo left behind when it moved to Vitest.
 */
import { QueryClient } from '@tanstack/react-query';

export function makeTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
      mutations: { retry: false },
    },
  });
}
