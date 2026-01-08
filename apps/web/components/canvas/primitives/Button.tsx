import { forwardRef, type ReactNode, type MouseEvent } from 'react';

interface ButtonProps {
  label: string;
  variant?: 'primary' | 'secondary';
  onClick?: (e?: MouseEvent<HTMLButtonElement>) => void;
  children?: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ label, variant = 'primary', onClick, children }, ref) => {
    const className = variant === 'primary'
      ? 'action-button action-button-primary'
      : 'action-button action-button-secondary';

    return (
      <button ref={ref} className={className} onClick={onClick}>
        {children || label}
      </button>
    );
  }
);

Button.displayName = 'Button';
