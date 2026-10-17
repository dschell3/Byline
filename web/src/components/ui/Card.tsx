import type { HTMLAttributes } from 'react';

// SCRUM-71: the white card from the Figma foundations page.
// Hairline border, rounded corners, comfortable padding. Put anything inside it.
export type CardProps = HTMLAttributes<HTMLDivElement>;

export function Card({ className = '', ...props }: CardProps) {
  return <div className={`rounded-lg border border-line bg-surface p-5 ${className}`} {...props} />;
}
