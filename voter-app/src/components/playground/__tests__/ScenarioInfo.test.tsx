import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import ScenarioInfo from '../ScenarioInfo';

describe('ScenarioInfo', () => {
  it('ships collapsed and reveals the scenario explanation on click', () => {
    render(<ScenarioInfo scenario="france2002_like" />);
    expect(screen.queryByTestId('pop-scenario-france2002_like')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('info-scenario-france2002_like'));
    const pop = screen.getByTestId('pop-scenario-france2002_like');
    expect(pop).toHaveTextContent(/France 2002/);
    expect(pop).toHaveTextContent(/spoiler/i);
    expect(pop).toHaveTextContent(/observer|Try/);
  });

  it('renders nothing for an unknown scenario id', () => {
    const { container } = render(<ScenarioInfo scenario="nope" />);
    expect(container).toBeEmptyDOMElement();
  });
});
