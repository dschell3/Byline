import { useId, type SelectHTMLAttributes } from 'react';

// SCRUM-71: dropdown that matches Input: same label, height, border and error state.
export type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  hint?: string;
  error?: string;
};

export function Select({
  label,
  hint = '',
  error = '',
  id,
  className = '',
  children,
  ...props
}: SelectProps) {
  const generatedId = useId();
  const selectId = id ?? generatedId;
  const messageId = `${selectId}-message`;
  const message = error || hint;

  return (
    <div className={className}>
      <label htmlFor={selectId} className="mb-1.5 block text-meta font-semibold text-ink">
        {label}
      </label>
      <div className="relative">
        <select
          id={selectId}
          aria-invalid={error ? true : undefined}
          aria-describedby={message ? messageId : undefined}
          className={`h-btn w-full appearance-none rounded-md border bg-surface pl-3.5 pr-10 text-body text-ink focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:cursor-not-allowed disabled:bg-surface-recessed ${
            error ? 'border-status-overdue-text' : 'border-line focus:border-primary'
          }`}
          {...props}
        >
          {children}
        </select>
        <svg
          aria-hidden="true"
          viewBox="0 0 16 16"
          fill="none"
          className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-meta"
        >
          <path
            d="M4 6l4 4 4-4"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
      {message && (
        <p
          id={messageId}
          className={`mt-1.5 text-meta ${error ? 'text-status-overdue-text' : 'text-ink-meta'}`}
        >
          {message}
        </p>
      )}
    </div>
  );
}
