import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { Dropdown, NavDropdown } from '../dropdown';

describe('Dropdown', () => {
  it('opens the menu on toggle click and shows items', () => {
    render(
      <Dropdown>
        <Dropdown.Toggle>Menu</Dropdown.Toggle>
        <Dropdown.Menu>
          <Dropdown.Item href="/quiz">Quiz</Dropdown.Item>
        </Dropdown.Menu>
      </Dropdown>
    );
    // Closed initially
    expect(screen.queryByText('Quiz')).not.toBeInTheDocument();
    fireEvent.click(screen.getByText('Menu'));
    expect(screen.getByText('Quiz')).toBeInTheDocument();
  });

  it('renders an href Item as a navigating <a>', () => {
    render(
      <Dropdown>
        <Dropdown.Toggle>Menu</Dropdown.Toggle>
        <Dropdown.Menu>
          <Dropdown.Item href="/quiz">Quiz</Dropdown.Item>
        </Dropdown.Menu>
      </Dropdown>
    );
    fireEvent.click(screen.getByText('Menu'));
    const link = screen.getByText('Quiz');
    expect(link.tagName).toBe('A');
    expect(link).toHaveAttribute('href', '/quiz');
  });

  it('fires onClick for a button Item', () => {
    const onClick = vi.fn();
    render(
      <Dropdown>
        <Dropdown.Toggle>Menu</Dropdown.Toggle>
        <Dropdown.Menu>
          <Dropdown.Item onClick={onClick}>Logout</Dropdown.Item>
        </Dropdown.Menu>
      </Dropdown>
    );
    fireEvent.click(screen.getByText('Menu'));
    fireEvent.click(screen.getByText('Logout'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('NavDropdown opens and its href items are links', () => {
    render(
      <NavDropdown title="Apprendre">
        <NavDropdown.Item href="/quiz">Quiz</NavDropdown.Item>
        <NavDropdown.Item href="/regimes-internationaux">Regimes</NavDropdown.Item>
      </NavDropdown>
    );
    fireEvent.click(screen.getByText('Apprendre'));
    const quiz = screen.getByText('Quiz');
    expect(quiz.tagName).toBe('A');
    expect(quiz).toHaveAttribute('href', '/quiz');
    expect(screen.getByText('Regimes')).toHaveAttribute('href', '/regimes-internationaux');
  });
});
