import * as React from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { X } from 'lucide-react';

import { cn } from '@/lib/utils';

/**
 * Bootstrap-compatible <Modal> over radix Dialog, so react-bootstrap modals
 * migrate by import-swap only (show/onHide + Modal.Header/Title/Body/Footer).
 */
const SIZE: Record<string, string> = { sm: 'max-w-sm', lg: 'max-w-2xl', xl: 'max-w-4xl' };

export interface ModalProps extends React.HTMLAttributes<HTMLDivElement> {
  show?: boolean;
  onHide?: () => void;
  size?: 'sm' | 'lg' | 'xl';
  centered?: boolean;
  backdrop?: boolean | 'static';
  scrollable?: boolean;
  fullscreen?: boolean | string;
  keyboard?: boolean;
  animation?: boolean;
}

const ModalBase: React.FC<ModalProps> = ({
  show,
  onHide,
  size,
  backdrop,
  className,
  children,
  centered,
  scrollable,
  fullscreen,
  keyboard,
  animation,
  ...rest
}) => (
  <DialogPrimitive.Root
    open={!!show}
    onOpenChange={(o) => {
      if (!o) onHide?.();
    }}
  >
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-[1050] bg-black/50" />
      <DialogPrimitive.Content
        className={cn(
          'fixed left-1/2 top-1/2 z-[1051] flex max-h-[90vh] w-full -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-lg border border-border bg-background shadow-lg',
          SIZE[size ?? ''] ?? 'max-w-lg',
          className
        )}
        onInteractOutside={(e) => {
          if (backdrop === 'static') e.preventDefault();
        }}
        aria-describedby={undefined}
        {...rest}
      >
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  </DialogPrimitive.Root>
);

const Header: React.FC<React.HTMLAttributes<HTMLDivElement> & { closeButton?: boolean }> = ({
  className,
  children,
  closeButton,
  ...props
}) => (
  <div
    className={cn('flex items-center justify-between border-b border-border px-4 py-3', className)}
    {...props}
  >
    {children}
    {closeButton && (
      <DialogPrimitive.Close
        aria-label="Close"
        className="rounded-sm opacity-70 transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring"
      >
        <X className="h-4 w-4" />
        <span className="sr-only">Close</span>
      </DialogPrimitive.Close>
    )}
  </div>
);

const Title = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Title
    ref={ref}
    className={cn('text-lg font-semibold leading-none tracking-tight', className)}
    {...props}
  />
));
Title.displayName = 'Modal.Title';

const Body: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ className, ...props }) => (
  <div className={cn('overflow-y-auto p-4', className)} {...props} />
);

const Footer: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ className, ...props }) => (
  <div
    className={cn(
      'flex flex-wrap items-center justify-end gap-2 border-t border-border px-4 py-3',
      className
    )}
    {...props}
  />
);

export const Modal = Object.assign(ModalBase, { Header, Title, Body, Footer });
