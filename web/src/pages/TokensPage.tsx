import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';

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
  {
    label: 'Page title',
    className: 'font-serif text-page-title text-ink',
    sample: 'Twenty submissions waiting',
  },
  { label: 'Section', className: 'font-serif text-section text-ink', sample: 'Changes requested' },
  {
    label: 'Card title',
    className: 'text-card-title text-ink',
    sample: 'Rebuild the pricing page in responsive CSS',
  },
  {
    label: 'Body',
    className: 'text-body text-ink-body',
    sample: 'Submit a link, a file, or paste your text.',
  },
  {
    label: 'Meta',
    className: 'text-meta text-ink-meta',
    sample: 'Due Fri 3 Oct, 11:59 PM · in 4 days · 10 points',
  },
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
          <span
            key={s.label}
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-meta ${s.className}`}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
            {s.label}
          </span>
        ))}
      </div>

      <h3 className="mt-6 text-card-title">Buttons</h3>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <Button>Approve</Button>
        <Button variant="secondary">Request changes</Button>
        <Button variant="danger">Deactivate person</Button>
        <Button disabled>Publish</Button>
        <Button variant="ghost">Cancel</Button>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <Button size="sm">Approve</Button>
        <Button size="sm" variant="secondary">
          Skip
        </Button>
      </div>

      <h3 className="mt-6 text-card-title">Form fields</h3>
      <div className="mt-3 grid gap-4 md:grid-cols-3">
        <Input label="Email address" type="email" defaultValue="amara.okafor@gmail.com" />
        <Input
          label="Due date"
          defaultValue="3 Oct 2026, 11:59 PM"
          hint="Shown to each member in their own timezone"
        />
        <Input
          label="Pull request URL"
          defaultValue="https//github.com/emerson/site/pul/88"
          error="That does not look like a URL. Check it starts with https://"
        />
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <Select label="Track" defaultValue="web" hint="The five tracks from the internship program">
          <option value="web">Web design and development</option>
          <option value="uxui">UX/UI design</option>
          <option value="marketing">Digital marketing</option>
          <option value="social">Social media management</option>
          <option value="sales">Sales and marketing</option>
        </Select>
      </div>

      <h3 className="mt-6 text-card-title">Card</h3>
      <Card className="mt-3">
        <div className="flex items-start justify-between gap-3">
          <p className="text-card-title text-ink">Draft ten LinkedIn posts for October</p>
          <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-status-due-soon-fill px-3 py-1 text-meta text-status-due-soon-text">
            <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
            Due soon
          </span>
        </div>
        <p className="mt-2 text-body text-ink-body">Set by Marguerite Ellis · Digital marketing</p>
        <p className="mt-1 text-meta text-ink-meta">
          Due Fri 3 Oct, 11:59 PM · in 4 days · 10 points
        </p>
        <Button variant="secondary" size="sm" className="mt-4">
          Open assignment
        </Button>
      </Card>
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
