import type { ReactNode } from 'react';

// SCRUM-72: the six status words from the Figma foundations page.
// Identical on every screen, so the label comes from the status, never typed by hand.
// Each status has its own icon, so colour is never the only signal.
const iconProps = {
  viewBox: '0 0 16 16',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.75,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  className: 'h-3 w-3 shrink-0',
  'aria-hidden': true,
};

const icons: Record<string, ReactNode> = {
  clock: (
    <svg {...iconProps}>
      <circle cx="8" cy="8" r="6" />
      <path d="M8 5v3l2 1.5" />
    </svg>
  ),
  dashed: (
    <svg {...iconProps}>
      <circle cx="8" cy="8" r="6" strokeDasharray="2.5 2.5" />
    </svg>
  ),
  arrowUp: (
    <svg {...iconProps}>
      <path d="M8 12.5V3.5M4.5 7L8 3.5 11.5 7" />
    </svg>
  ),
  pencil: (
    <svg {...iconProps}>
      <path d="M10.5 3l2.5 2.5L6 12.5H3.5V10z" />
    </svg>
  ),
  alert: (
    <svg {...iconProps}>
      <circle cx="8" cy="8" r="6" />
      <path d="M8 5v3.5M8 11h.01" />
    </svg>
  ),
  check: (
    <svg {...iconProps}>
      <path d="M3.5 8.5l3 3 6-7" />
    </svg>
  ),
};

const badges = {
  'due-soon': {
    label: 'Due soon',
    icon: 'clock',
    className: 'bg-status-due-soon-fill text-status-due-soon-text',
  },
  optional: {
    label: 'Optional',
    icon: 'dashed',
    className: 'bg-status-optional-fill text-status-optional-text',
  },
  submitted: {
    label: 'Submitted',
    icon: 'arrowUp',
    className: 'bg-status-submitted-fill text-status-submitted-text',
  },
  changes: {
    label: 'Changes requested',
    icon: 'pencil',
    className: 'bg-status-changes-fill text-status-changes-text',
  },
  overdue: {
    label: 'Overdue',
    icon: 'alert',
    className: 'bg-status-overdue-fill text-status-overdue-text',
  },
  approved: {
    label: 'Approved',
    icon: 'check',
    className: 'bg-status-approved-fill text-status-approved-text',
  },
} as const;

export type Status = keyof typeof badges;

export function Badge({ status }: { status: Status }) {
  const { label, icon, className } = badges[status];
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1 text-meta ${className}`}
    >
      {icons[icon]}
      {label}
    </span>
  );
}
