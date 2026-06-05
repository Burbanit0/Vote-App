import * as React from 'react';

import { cn } from '@/lib/utils';

/**
 * Bootstrap-compatible <ToastContainer>/<Toast> (+ .Header/.Body). Minimal:
 * `show`/`onClose`/`bg`; `autohide`+`delay` close after the delay.
 */
const POSITION: Record<string, string> = {
  'top-start': 'top-0 left-0',
  'top-center': 'top-0 left-1/2 -translate-x-1/2',
  'top-end': 'top-0 right-0',
  'bottom-start': 'bottom-0 left-0',
  'bottom-center': 'bottom-0 left-1/2 -translate-x-1/2',
  'bottom-end': 'bottom-0 right-0',
  'middle-center': 'top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2',
};

export interface ToastContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  position?: keyof typeof POSITION;
}
export const ToastContainer: React.FC<ToastContainerProps> = ({
  position,
  className,
  style,
  ...props
}) => (
  <div
    className={cn(
      'z-[1090] flex flex-col gap-2 p-3',
      position && 'fixed',
      position && POSITION[position],
      className
    )}
    style={style}
    {...props}
  />
);

const BG: Record<string, string> = {
  success: 'bg-[#198754] text-white',
  danger: 'bg-[#dc3545] text-white',
  warning: 'bg-[#ffc107] text-black',
  info: 'bg-[#0dcaf0] text-black',
  primary: 'bg-primary text-primary-foreground',
  dark: 'bg-slate-800 text-white',
  light: 'bg-slate-100 text-slate-900',
};

export interface ToastProps extends React.HTMLAttributes<HTMLDivElement> {
  show?: boolean;
  onClose?: () => void;
  bg?: keyof typeof BG;
  autohide?: boolean;
  delay?: number;
}

const ToastBase: React.FC<ToastProps> = ({
  show = true,
  onClose,
  bg,
  autohide,
  delay = 3000,
  className,
  children,
  ...props
}) => {
  React.useEffect(() => {
    if (!show || !autohide || !onClose) return;
    const id = setTimeout(onClose, delay);
    return () => clearTimeout(id);
  }, [show, autohide, delay, onClose]);
  if (!show) return null;
  return (
    <div
      role="alert"
      aria-live="assertive"
      className={cn(
        'min-w-[14rem] overflow-hidden rounded-md border border-border shadow-md',
        bg && BG[bg],
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};

const Header: React.FC<React.HTMLAttributes<HTMLDivElement> & { closeButton?: boolean }> = ({
  className,
  children,
  closeButton = true,
  ...props
}) => (
  <div
    className={cn(
      'flex items-center justify-between gap-2 border-b border-border/40 px-3 py-2 text-sm font-medium',
      className
    )}
    {...props}
  >
    {children}
  </div>
);

const Body: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ className, ...props }) => (
  <div className={cn('px-3 py-2 text-sm', className)} {...props} />
);

export const Toast = Object.assign(ToastBase, { Header, Body });
