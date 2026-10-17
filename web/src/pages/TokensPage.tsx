type Theme = 'light' | 'dark';

const swatches = [
  { label: 'Page background', className: 'bg-page' },
  { label: 'Surface', className: 'bg-surface' },
  { label: 'Surface recessed', className: 'bg-surface-recessed' },
  { label: 'Border', className: 'bg-line' },
  { label: 'Text strong', className: 'bg-ink' },
  { label: 'Text body', className: 'bg-ink-body' },
  { label: 'Text meta', className: 'bg-ink-meta' },
  { label: 'Primary action', className: 'bg-primary' },
  { label: 'Brand accent', className: 'bg-accent' },
];

const typeScale = [
  { label: 'Page title', className: 'font-serif text-page-title text-ink', sample: 'Twenty submissions waiting' },
  { label: 'Section', className: 'font-serif text-section text-ink', sample: 'Changes requested' },
  { label: 'Card title', className: 'text-card-title text-ink', sample: 'Rebuild the pricing page in responsive CSS' },
  { label: 'Body', className: 'text-body text-ink-body', sample: 'Submit a link, a file, or paste your text.' },
  { label: 'Meta', className: 'text-meta text-ink-meta', sample: 'Due Fri 3 Oct, 11:59 PM · in 4 days · 10 points' },
];

const statuses = [
  { label: 'Due soon', className: 'bg-status-due-soon-fill text-status-due-soon-text' },
  { label: 'Optional', className: 'bg-status-optional-fill text-status-optional-text' },
  { label: 'Submitted', className: 'bg-status-submitted-fill text-status-submitted-text' },
  { label: 'Changes requested', className: 'bg-status-changes-fill text-status-changes-text' },
  { label: 'Overdue', className: 'bg-status-overdue-fill text-status-overdue-text' },
  { label: 'Approved', className: 'bg-status-approved-fill text-status-approved-text' },
];

function ThemePanel({ theme }: { theme: Theme }) {
  return (
    <section data-theme={theme} className="rounded-lg border border-line bg-page p-6 text-ink-body">
      <h2 className="text-section">{theme === 'light' ? 'Light' : 'Dark'}</h2>

      <h3 className="mt-6 text-card-title">Colour</h3>
      <div className="mt-3 grid grid-cols-3 gap-3">
        {swatches.map((s) => (
          <div key={s.label}>
            <div className={`h-12 rounded-md border border-line ${s.className}`} />
            <p className="mt-1 text-meta text-ink-meta">{s.label}</p>
          </div>
        ))}
      </div>

      <h3 className="mt-6 text-card-title">Type scale</h3>
      <div className="mt-3 space-y-3 rounded-md border border-line bg-surface p-4">
        {typeScale.map((t) => (
          <div key={t.label}>
            <p className="text-meta text-ink-meta">{t.label}</p>
            <p className={t.className}>{t.sample}</p>
          </div>
        ))}
      </div>

      <h3 className="mt-6 text-card-title">Status words</h3>
      <div className="mt-3 flex flex-wrap gap-2">
        {statuses.map((s) => (
          <span key={s.label} className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-meta ${s.className}`}>
            <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
            {s.label}
          </span>
        ))}
      </div>

      <h3 className="mt-6 text-card-title">Buttons</h3>
      <div className="mt-3 flex gap-3">
        <button type="button" className="h-btn rounded-md bg-primary px-4 text-card-title text-primary-on">
          Approve
        </button>
        <button type="button" className="h-btn rounded-md border border-line bg-surface px-4 text-card-title text-ink">
          Request changes
        </button>
      </div>
    </section>
  );
}

export default function TokensPage() {
  return (
    <main className="min-h-screen bg-page p-6 md:p-10">
      <h1 className="text-page-title">Design tokens</h1>
      <p className="mt-1 text-ink-meta">
        Every colour, type size and status word from the Figma foundations, in light and dark.
      </p>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <ThemePanel theme="light" />
        <ThemePanel theme="dark" />
      </div>
    </main>
  );
}