import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import ScenarioIO, {
  buildScenarioBundle, validateScenarioBundle, SCENARIO_FORMAT_VERSION,
} from '../ScenarioIO';
import { ElectionProvider, useElection } from '../../../../stores/useElectionStore';
import { usePerturbations } from '../../../../stores/useLabStore';

// jsdom doesn't implement URL.createObjectURL / revokeObjectURL
beforeAll(() => {
  (URL as any).createObjectURL = vi.fn(() => 'blob:mock');
  (URL as any).revokeObjectURL = vi.fn();
  // jsdom's HTMLAnchorElement.click is a noop — that's fine, we don't actually
  // need a real download in tests, only to verify the path doesn't throw.
});

// Helper: build a File whose .text() definitely returns the given contents.
// Some jsdom versions don't implement File.prototype.text() reliably.
function makeFile(content: string, name = 'scenario.json'): File {
  const f = new File([content], name, { type: 'application/json' });
  Object.defineProperty(f, 'text', {
    value: () => Promise.resolve(content),
    configurable: true,
  });
  return f;
}

// Inspector that surfaces the current context state for assertions
const Inspector: React.FC = () => {
  const { config } = useElection();
  const { pinned } = usePerturbations();
  return (
    <div>
      <span data-testid="seed">{config.seed}</span>
      <span data-testid="num-voters">{config.num_voters}</span>
      <span data-testid="cand-count">{config.candidates.length}</span>
      <span data-testid="pinned-count">{pinned.length}</span>
      <span data-testid="pinned-labels">{pinned.map((p) => p.label).join('|')}</span>
    </div>
  );
};

function wrap(children: React.ReactNode) {
  return (
    <ElectionProvider>
      {children}
      <Inspector />
    </ElectionProvider>
  );
}

describe('buildScenarioBundle', () => {
  it('wraps config + pinned with version + timestamp', () => {
    const cfg: any = {
      candidates: [{ name: 'A', x: 0, y: 0 }],
      num_voters: 100,
      ideology:   'random',
      seed:       42,
      blank_vote:        { enabled: false, rule: 'symbolic', contagion: { enabled: false, beta: 0, gamma: 0, network: 'random' } },
      information_model: { enabled: false, media_bias: {}, voter_segments: { low_info: 0.3, medium_info: 0.5, high_info: 0.2 } },
      campaign:          { enabled: false, num_days: 30, polling_effect: 0.3 },
    };
    const pinned = [{ id: 'x', type: 't', icon: '🗳', label: 'L', summary: 'S', pinnedAt: 1 }];
    const b = buildScenarioBundle(cfg, pinned);
    expect(b.version).toBe(SCENARIO_FORMAT_VERSION);
    expect(b.config).toBe(cfg);
    expect(b.pinned).toBe(pinned);
    expect(typeof b.exportedAt).toBe('string');
    expect(() => new Date(b.exportedAt)).not.toThrow();
  });
});

describe('validateScenarioBundle', () => {
  const minimalCfg = {
    candidates: [{ name: 'A', x: 0, y: 0 }],
    num_voters: 100,
    ideology:   'random',
    seed:       1,
  };

  it('accepts a well-formed bundle', () => {
    expect(validateScenarioBundle({
      version: 1, exportedAt: 'now', config: minimalCfg, pinned: [],
    })).not.toBeNull();
  });

  it('rejects non-object input', () => {
    expect(validateScenarioBundle(null)).toBeNull();
    expect(validateScenarioBundle('foo')).toBeNull();
    expect(validateScenarioBundle(42)).toBeNull();
  });

  it('rejects missing version', () => {
    expect(validateScenarioBundle({ config: minimalCfg })).toBeNull();
  });

  it('rejects missing/invalid config', () => {
    expect(validateScenarioBundle({ version: 1 })).toBeNull();
    expect(validateScenarioBundle({ version: 1, config: 'nope' })).toBeNull();
  });

  it('rejects candidates with missing fields', () => {
    expect(validateScenarioBundle({
      version: 1, config: { ...minimalCfg, candidates: [{ name: 'A' }] },
    })).toBeNull();
  });

  it('defaults pinned to [] when absent', () => {
    const b = validateScenarioBundle({ version: 1, config: minimalCfg });
    expect(b?.pinned).toEqual([]);
  });

  it('preserves pinned when present', () => {
    const pinned = [{ id: 'a', type: 't', icon: 'i', label: 'l', summary: 's', pinnedAt: 0 }];
    const b = validateScenarioBundle({ version: 1, config: minimalCfg, pinned });
    expect(b?.pinned).toEqual(pinned);
  });
});

describe('ScenarioIO component', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders export and import buttons', () => {
    render(wrap(<ScenarioIO />));
    expect(screen.getByTestId('scenario-export-btn')).toBeInTheDocument();
    expect(screen.getByTestId('scenario-import-btn')).toBeInTheDocument();
  });

  it('export click shows a success toast', async () => {
    render(wrap(<ScenarioIO />));
    act(() => { fireEvent.click(screen.getByTestId('scenario-export-btn')); });
    await waitFor(() => expect(screen.getByTestId('scenario-toast-success')).toBeInTheDocument());
  });

  it('importing a valid bundle replaces config and restores pinned', async () => {
    render(wrap(<ScenarioIO />));
    expect(screen.getByTestId('seed').textContent).toBe('42');

    const bundle = {
      version:    1,
      exportedAt: '2026-05-23T00:00:00Z',
      config: {
        candidates: [
          { name: 'X', x: -0.1, y: 0.1 },
          { name: 'Y', x:  0.5, y: 0.0 },
        ],
        num_voters: 777,
        ideology:   'centrist',
        seed:       1337,
        blank_vote:        { enabled: false, rule: 'symbolic', contagion: { enabled: false, beta: 0, gamma: 0, network: 'random' } },
        information_model: { enabled: false, media_bias: {}, voter_segments: { low_info: 0.3, medium_info: 0.5, high_info: 0.2 } },
        campaign:          { enabled: false, num_days: 30, polling_effect: 0.3 },
      },
      pinned: [
        { id: 'old', type: 'abstention', icon: '🗳', label: 'Imported card', summary: 'sum', pinnedAt: 0 },
      ],
    };
    const file = makeFile(JSON.stringify(bundle));
    const input = screen.getByTestId('scenario-import-input') as HTMLInputElement;
    await act(async () => {
      fireEvent.change(input, { target: { files: [file] } });
    });

    await waitFor(() => expect(screen.getByTestId('seed').textContent).toBe('1337'));
    expect(screen.getByTestId('num-voters').textContent).toBe('777');
    expect(screen.getByTestId('cand-count').textContent).toBe('2');
    expect(screen.getByTestId('pinned-count').textContent).toBe('1');
    expect(screen.getByTestId('pinned-labels').textContent).toBe('Imported card');
    expect(screen.getByTestId('scenario-toast-success')).toBeInTheDocument();
  });

  it('importing an invalid bundle shows a danger toast and does not mutate state', async () => {
    render(wrap(<ScenarioIO />));
    const before = screen.getByTestId('seed').textContent;

    const file = makeFile('not json', 'bad.json');
    const input = screen.getByTestId('scenario-import-input') as HTMLInputElement;
    await act(async () => {
      fireEvent.change(input, { target: { files: [file] } });
    });

    await waitFor(() => expect(screen.getByTestId('scenario-toast-danger')).toBeInTheDocument());
    expect(screen.getByTestId('seed').textContent).toBe(before);
  });
});
