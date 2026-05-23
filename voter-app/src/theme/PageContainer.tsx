/**
 * PageContainer — opinionated wrapper around <Container> that picks the
 * page-wide max-width from the design tokens. Use this in every page so
 * the layout stays consistent.
 *
 *   <PageContainer variant="full">   ← Lab, simulators
 *   <PageContainer variant="wide">   ← dashboards
 *   <PageContainer variant="medium"> ← articles, theory pages
 *   <PageContainer variant="narrow"> ← forms, quiz
 *
 * Renders a Bootstrap <Container fluid> with `maxWidth` from LAYOUT.
 */
import React from 'react';
import { Container } from 'react-bootstrap';
import { LAYOUT, LayoutVariant } from './tokens';

const VARIANT_MAP: Record<'narrow' | 'medium' | 'wide' | 'full', LayoutVariant> = {
  narrow: 'pageNarrow',
  medium: 'pageMedium',
  wide:   'pageWide',
  full:   'pageFull',
};

interface Props {
  variant?:   'narrow' | 'medium' | 'wide' | 'full';
  className?: string;
  /** Extra inline style merged onto the container. */
  style?:     React.CSSProperties;
  children:   React.ReactNode;
  /** Default vertical padding class. Override with eg "py-3". */
  padding?:   string;
  /** Data-testid hook for tests. */
  'data-testid'?: string;
}

const PageContainer: React.FC<Props> = ({
  variant = 'medium',
  className = '',
  style,
  children,
  padding = 'py-4',
  ...rest
}) => {
  const maxWidth = LAYOUT[VARIANT_MAP[variant]];
  return (
    <Container
      fluid
      className={`${padding} ${className}`.trim()}
      style={{ maxWidth, ...style }}
      data-testid={rest['data-testid']}
    >
      {children}
    </Container>
  );
};

export default PageContainer;
