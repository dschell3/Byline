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
  danger: 'bg-danger text-primary-on hover:bg-danger/90 disabled:bg-line disabled:text-ink-meta',
  ghost: 'bg-transparent text-link hover:underline disabled:text-ink-meta disabled:no-underline',
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
  // Shows a spinner, keeps the button's colour, and ignores clicks until the action finishes.
  // eslint-disable-next-line react/require-default-props
  loading?: boolean;
};

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  type,
  className = '',
  onClick,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      type={type === 'submit' && !loading ? 'submit' : 'button'}
      aria-busy={loading || undefined}
      aria-disabled={loading || undefined}
      onClick={loading ? undefined : onClick}
      className={`${base} ${variants[variant]} ${sizes[size]} ${loading ? 'cursor-wait' : ''} ${className}`}
      {...props}
    >
      {loading && (
        <svg aria-hidden="true" viewBox="0 0 16 16" fill="none" className="h-4 w-4 animate-spin">
          <circle cx="8" cy="8" r="6" stroke="currentColor" strokeOpacity="0.3" strokeWidth="2" />
          <path
            d="M14 8a6 6 0 0 0-6-6"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      )}
      {children}
    </button>
  );
}
