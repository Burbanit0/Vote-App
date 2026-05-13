import { render, screen } from '@testing-library/react';
import { Heatmap } from '../Heatmap';

describe('Heatmap', () => {
  const mockData = [
    { x: 1, y: 1, value: 10 },
    { x: 1, y: 2, value: 20 },
    { x: 2, y: 1, value: 30 },
    { x: 2, y: 2, value: 40 },
  ];

  it('renders SVG with rectangles', () => {
    const { container } = render(<Heatmap width={400} height={300} data={mockData} />);
    expect(container.querySelectorAll('rect').length).toBe(4);
  });

  it('renders axis labels', () => {
    render(<Heatmap width={400} height={300} data={mockData} />);
    expect(screen.getAllByText('1').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('2').length).toBeGreaterThanOrEqual(1);
  });

  it('returns null for empty data', () => {
    const { container } = render(<Heatmap width={400} height={300} data={[]} />);
    expect(container.innerHTML).toBe('');
  });
});
