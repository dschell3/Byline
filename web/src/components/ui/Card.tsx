import type { HTMLAttributes } from 'react';

// SCRUM-71: the white card from the Figma foundations page.
// Hairline border, 12px radius, 14px padding. Put anything inside it.
export type CardProps = HTMLAttributes<HTMLDivElement>;

export function Card({ className = '', ...props }: CardProps) {
  return (
    <div className={`rounded-xl border border-line bg-surface p-3.5 ${className}`} {...props} />
  );
}
