import React from 'react';
import { render, screen } from '@testing-library/react';
import ResponsiveTable from '../ResponsiveTable';

vi.mock('../../../../hooks/useIsMobile', () => ({
  useIsMobile: () => false,
}));

describe('ResponsiveTable', () => {
  it('renders children inside rsp-table wrapper', () => {
    render(
      <ResponsiveTable>
        <table>
          <tbody>
            <tr>
              <td>cell content</td>
            </tr>
          </tbody>
        </table>
      </ResponsiveTable>
    );
    expect(screen.getByText('cell content')).toBeInTheDocument();
  });

  it('carries the rsp-table hook the stylesheet targets', () => {
    // The sticky first column and the phone padding are plain CSS in
    // src/styles/tailwind.css (they select descendants of the wrapper, which
    // arrive as children), so what this component owns is the class that
    // selects them. They used to be injected into <head> on first render.
    const { container } = render(
      <ResponsiveTable>
        <table>
          <tbody>
            <tr>
              <td>test</td>
            </tr>
          </tbody>
        </table>
      </ResponsiveTable>
    );
    expect(container.querySelector('.rsp-table')).not.toBeNull();
    expect(document.getElementById('responsive-table-styles')).toBeNull();
  });

  it('applies custom className', () => {
    const { container } = render(
      <ResponsiveTable className="my-custom-class">
        <table>
          <tbody>
            <tr>
              <td>test</td>
            </tr>
          </tbody>
        </table>
      </ResponsiveTable>
    );
    const outer = container.firstChild as HTMLElement;
    expect(outer.className).toContain('my-custom-class');
  });
});
