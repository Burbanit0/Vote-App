import React from 'react';
import { render, screen } from '@testing-library/react';
import { Tooltip } from '../Tooltip';

describe('Tooltip', () => {
  it('renders null when interactionData is null', () => {
    const { container } = render(<Tooltip interactionData={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders tooltip with name when interactionData provided', () => {
    render(<Tooltip interactionData={{ xPos: 100, yPos: 200, name: 'Candidate A' }} />);
    expect(screen.getByText('Candidate A')).toBeInTheDocument();
  });
});
