import { useId, type InputHTMLAttributes } from 'react';

// SCRUM-71: text field from the Figma foundations page.
// Label above, 44px field, optional hint below, red border and message when there's an error.
export type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  // eslint-disable-next-line react/require-default-props
  hint?: string;
  // eslint-disable-next-line react/require-default-props
  error?: string;
};

export function Input({ label, hint, error, id, className = '', ...props }: InputProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const messageId = `${inputId}-message`;
  const message = error ?? hint;

  return (
    <div className={className}>
      <label htmlFor={inputId} className="mb-1.5 block text-meta font-semibold text-ink">
        {label}
      </label>
      <input
        id={inputId}
        aria-invalid={error ? true : undefined}
        aria-describedby={message ? messageId : undefined}
        className={`h-btn w-full rounded-md border bg-surface px-3.5 text-body text-ink placeholder:text-ink-meta focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:cursor-not-allowed disabled:bg-surface-recessed ${
          error ? 'border-status-overdue-text' : 'border-line focus:border-primary'
        }`}
        {...props}
      />
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
