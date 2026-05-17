import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import MethodGroupDonut from '../MethodGroupDonut';
import type { MethodGroup } from '../../../services/electionApi';

// Mock Recharts — expose Cell dataKey for assertions
jest.mock('recharts', () => ({
  PieChart: ({ children }: any) => <div data-testid="pie-chart">{children}</div>,
  Pie:      ({ children, data }: any) => (
    <div data-testid="pie" data-count={data?.length}>
      {/* Render children (Cell elements) */}
      {children}
    </div>
  ),
  Cell:    ({ fill }: any) => <div data-testid="pie-cell" data-fill={fill} />,
  Tooltip: () => null,
}));

const SINGLE_GROUP: MethodGroup[] = [
  { winner: 'Alice', methods: ['plurality', 'borda', 'irv', 'schulze'], pct: 1.0 },
];

const TWO_GROUPS: MethodGroup[] = [
  { winner: 'Alice', methods: ['borda', 'irv', 'schulze'],  pct: 0.64 },
  { winner: 'Bob',   methods: ['plurality', 'approval'],    pct: 0.36 },
];

const THREE_GROUPS: MethodGroup[] = [
  { winner: 'Alice', methods: ['borda'],     pct: 0.40 },
  { winner: 'Bob',   methods: ['plurality'], pct: 0.40 },
  { winner: 'Carol', methods: ['schulze'],   pct: 0.20 },
];

describe('MethodGroupDonut', () => {
  it('renders nothing when methodGroups is empty', () => {
    const { container } = render(<MethodGroupDonut methodGroups={[]} totalMethods={10} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders a PieChart when groups are provided', () => {
    render(<MethodGroupDonut methodGroups={TWO_GROUPS} totalMethods={5} />);
    expect(screen.getByTestId('pie-chart')).toBeInTheDocument();
  });

  // ── Single group (full consensus) ─────────────────────────────────────────

  it('single group → renders exactly 1 Cell', () => {
    render(<MethodGroupDonut methodGroups={SINGLE_GROUP} totalMethods={4} />);
    expect(screen.getAllByTestId('pie-cell')).toHaveLength(1);
  });

  it('single group → shows winner name', () => {
    render(<MethodGroupDonut methodGroups={SINGLE_GROUP} totalMethods={4} />);
    expect(screen.getByText('Alice')).toBeInTheDocument();
  });

  it('single group → shows consensus text', () => {
    render(<MethodGroupDonut methodGroups={SINGLE_GROUP} totalMethods={4} />);
    // donutSingle key or its translation
    expect(
      screen.queryByText(/accord total|full agreement|donutSingle/i)
    ).not.toBeNull();
  });

  // ── Two groups (divergence) ────────────────────────────────────────────────

  it('two groups → renders 2 Cells', () => {
    render(<MethodGroupDonut methodGroups={TWO_GROUPS} totalMethods={5} />);
    expect(screen.getAllByTestId('pie-cell')).toHaveLength(2);
  });

  it('two groups → legend shows both candidate names', () => {
    render(<MethodGroupDonut methodGroups={TWO_GROUPS} totalMethods={5} />);
    expect(screen.getByText('Alice')).toBeInTheDocument();
    expect(screen.getByText('Bob')).toBeInTheDocument();
  });

  it('two groups → legend shows method counts', () => {
    render(<MethodGroupDonut methodGroups={TWO_GROUPS} totalMethods={5} />);
    // "3/5" and "2/5"
    expect(screen.getByText('3/5')).toBeInTheDocument();
    expect(screen.getByText('2/5')).toBeInTheDocument();
  });

  // ── Three groups ───────────────────────────────────────────────────────────

  it('three groups → renders 3 Cells', () => {
    render(<MethodGroupDonut methodGroups={THREE_GROUPS} totalMethods={3} />);
    expect(screen.getAllByTestId('pie-cell')).toHaveLength(3);
  });

  // ── Legend click interaction ───────────────────────────────────────────────

  it('clicking legend row expands method badges for that group', () => {
    render(<MethodGroupDonut methodGroups={TWO_GROUPS} totalMethods={5} />);
    // Click "Alice" legend row
    fireEvent.click(screen.getByText('Alice'));
    // Method badges should appear
    expect(screen.getByText('borda')).toBeInTheDocument();
    expect(screen.getByText('irv')).toBeInTheDocument();
    expect(screen.getByText('schulze')).toBeInTheDocument();
  });

  it('clicking legend row again collapses method badges', () => {
    render(<MethodGroupDonut methodGroups={TWO_GROUPS} totalMethods={5} />);
    fireEvent.click(screen.getByText('Alice'));
    expect(screen.getByText('borda')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Alice'));
    expect(screen.queryByText('borda')).toBeNull();
  });

  it('does not render no-group case without crashing', () => {
    expect(() =>
      render(<MethodGroupDonut methodGroups={[]} totalMethods={0} />)
    ).not.toThrow();
  });
});
