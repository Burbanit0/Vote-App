module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'],
  moduleNameMapper: {
    '\\.(css|less|sass|scss)$': 'identity-obj-proxy',
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
  // Minimum thresholds — increase progressively as test suite grows
  coverageThreshold: {
    global: {
      branches:   20,
      functions:  25,
      lines:      30,
      statements: 30,
    },
  },
};
