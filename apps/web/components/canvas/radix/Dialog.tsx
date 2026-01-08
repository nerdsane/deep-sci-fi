import * as Dialog from '@radix-ui/react-dialog';
import type { ReactNode } from 'react';

interface DSFDialogProps {
  trigger?: ReactNode;
  title?: string;
  description?: string;
  children: ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

/**
 * Dialog component styled with DSF's neon cyberpunk aesthetic
 * Wraps Radix UI Dialog primitive
 */
export function DSFDialog({
  trigger,
  title,
  description,
  children,
  open,
  onOpenChange
}: DSFDialogProps) {
  // Only pass open/onOpenChange if explicitly provided (controlled)
  // Otherwise, let Radix manage state internally (uncontrolled)
  const rootProps = open !== undefined && onOpenChange !== undefined
    ? { open, onOpenChange }
    : {};

  return (
    <Dialog.Root {...rootProps}>
      {trigger && (
        <Dialog.Trigger asChild>
          {trigger}
        </Dialog.Trigger>
      )}
      <Dialog.Portal>
        <Dialog.Overlay className="dsf-dialog-overlay" />
        <Dialog.Content className="dsf-dialog-content">
          {title && (
            <Dialog.Title className="dsf-dialog-title">
              {title}
            </Dialog.Title>
          )}
          {description && (
            <Dialog.Description className="dsf-dialog-description">
              {description}
            </Dialog.Description>
          )}
          <div className="dsf-dialog-body">
            {children}
          </div>
          <Dialog.Close asChild>
            <button className="dsf-dialog-close" aria-label="Close">
              ×
            </button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
