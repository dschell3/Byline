// SCRUM-72: the six status words from the Figma foundations page.
// Identical on every screen, so the label comes from the status, never typed by hand.
const badges = {
  'due-soon': { label: 'Due soon', className: 'bg-status-due-soon-fill text-status-due-soon-text' },
  optional: { label: 'Optional', className: 'bg-status-optional-fill text-status-optional-text' },
  submitted: {
    label: 'Submitted',
    className: 'bg-status-submitted-fill text-status-submitted-text',
  },
  changes: {
    label: 'Changes requested',
    className: 'bg-status-changes-fill text-status-changes-text',
  },
  overdue: { label: 'Overdue', className: 'bg-status-overdue-fill text-status-overdue-text' },
  approved: { label: 'Approved', className: 'bg-status-approved-fill text-status-approved-text' },
} as const;

export type Status = keyof typeof badges;

export function Badge({ status }: { status: Status }) {
  const { label, className } = badges[status];
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1 text-meta ${className}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
      {label}
    </span>
  );
}
