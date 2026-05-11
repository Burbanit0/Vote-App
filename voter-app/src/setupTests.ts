import '@testing-library/jest-dom';
import { TextEncoder, TextDecoder } from 'util';

Object.assign(global, { TextDecoder, TextEncoder });

// Initialize i18next so components using useTranslation() work in Jest.
// This mirrors the import in src/index.tsx.
import './i18n';
