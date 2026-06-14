import React from 'react';
import { render } from '@testing-library/react';
import BarChart from './BarChart';

describe('BarChart', () => {
  it('renders an SVG element when data is provided', () => {
    const data = [
      { label: 'A', value: 10 },
      { label: 'B', value: 20 },
    ];
    const { container } = render(<BarChart data={data} />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveAttribute('width', '800');
    expect(svg).toHaveAttribute('height', '400');
  });
});
