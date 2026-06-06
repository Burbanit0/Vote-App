import React from 'react';
import { render, screen } from '@testing-library/react';
import ResponsiveTable from '../ResponsiveTable';

vi.mock('../../../hooks/useIsMobile', () => ({
  useIsMobile: () => false,
}));

// Clean up the injected style tag between tests
afterEach(() => {
  const style = document.getElementById('responsive-table-styles');
  if (style) style.remove();
});

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

  it('injects style tag on mount', () => {
    render(
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
    const style = document.getElementById('responsive-table-styles');
    expect(style).toBeInTheDocument();
    expect(style?.tagName).toBe('STYLE');
  });

  it('does not inject duplicate style tag', () => {
    render(
      <ResponsiveTable>
        <table>
          <tbody>
            <tr>
              <td>first</td>
            </tr>
          </tbody>
        </table>
      </ResponsiveTable>
    );
    render(
      <ResponsiveTable>
        <table>
          <tbody>
            <tr>
              <td>second</td>
            </tr>
          </tbody>
        </table>
      </ResponsiveTable>
    );
    const styles = document.querySelectorAll('#responsive-table-styles');
    expect(styles.length).toBe(1);
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
