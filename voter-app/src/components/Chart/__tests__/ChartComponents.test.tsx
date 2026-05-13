import React from 'react';
import { render } from '@testing-library/react';
import { Tooltip } from '../Tooltip';

jest.mock('../tooltip.module.css', () => ({ tooltip: 'tooltip' }));

describe('Tooltip', () => {
  it('renders null when interactionData is null', () => {
    const { container } = render(<Tooltip interactionData={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders with interaction data', () => {
    const { container } = render(<Tooltip interactionData={{ xPos: 100, yPos: 200, name: 'Test' }} />);
    expect(container.textContent).toBe('Test');
  });
});
