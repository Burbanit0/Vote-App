module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'],
  moduleNameMapper: {
    '\\.(css|less|sass|scss)$': 'identity-obj-proxy',
    '\\.(jpg|jpeg|png|gif|webp|svg)$': '<rootDir>/src/__mocks__/fileMock.ts',
    '^virtual:pwa-register/react$': '<rootDir>/src/__mocks__/pwa-register.ts',
    // The real useSimulationWorker uses `new Worker(new URL(..., import.meta.url))`
    // which Jest's TS config doesn't support. Replace it project-wide with the
    // no-op mock so every component test that touches a chart/heatmap just works.
    '^.*hooks/useSimulationWorker$': '<rootDir>/src/__mocks__/useSimulationWorker.ts',
  },
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx'],
  transform: {
    '^.+\\.(ts|tsx)$': 'ts-jest',
    '^.+\\.(js|jsx)$': 'babel-jest',
  },
  transformIgnorePatterns: [
    'node_modules/(?!d3|some-other-es-module)/',
  ],
  testMatch: ['**/src/**/*.test.(ts|tsx)'],

  // ── Coverage ──────────────────────────────────────────────────────────────
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/index.tsx',
    '!src/reportWebVitals.ts',
    '!src/declarations.d.ts',
    '!src/**/*.test.{ts,tsx}',
    '!src/**/*.stories.{ts,tsx}',
  ],
  coverageReporters: ['text', 'lcov', 'html'],
  // Minimum thresholds
  coverageThreshold: {
    global: {
      branches:   20,
      functions:  25,
      lines:      50,
      statements: 50,
    },
  },
};
