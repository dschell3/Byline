import type { ButtonHTMLAttributes } from 'react';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';
type Size = 'md' | 'sm';

// SCRUM-71: buttons from the Figma foundations page.
// md is 44px (the phone tap target), sm is 36px.
const base =
  'inline-flex items-center justify-center gap-2 rounded-md px-4 text-card-title transition-colors ' +
  'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ' +
  'disabled:cursor-not-allowed';

const variants: Record<Variant, string> = {
  primary: 'bg-primary text-primary-on hover:bg-primary/90 disabled:bg-line disabled:text-ink-meta',
  secondary:
    'border border-line bg-surface text-ink hover:bg-surface-recessed disabled:text-ink-meta',
  danger:
    'bg-status-overdue-text text-primary-on hover:bg-status-overdue-text/90 disabled:bg-line disabled:text-ink-meta',
  ghost: 'bg-transparent text-primary hover:underline disabled:text-ink-meta disabled:no-underline',
};

const sizes: Record<Size, string> = {
  md: 'h-btn',
  sm: 'h-btn-sm px-3',
};

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  // React 19 removed defaultProps for function components, so defaults live in the parameters below.
  // eslint-disable-next-line react/require-default-props
  variant?: Variant;
  // eslint-disable-next-line react/require-default-props
  size?: Size;
};

export function Button({
  variant = 'primary',
  size = 'md',
  type,
  className = '',
  ...props
}: ButtonProps) {
  return (
    <button
      type={type === 'submit' ? 'submit' : 'button'}
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    />
  );
}
