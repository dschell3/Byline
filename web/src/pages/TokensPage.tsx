import { useState } from 'react';
import { Badge, type Status } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Dialog } from '../components/ui/Dialog';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Table } from '../components/ui/Table';

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

const statuses: Status[] = ['due-soon', 'optional', 'submitted', 'changes', 'overdue', 'approved'];

type QueueRow = {
  id: string;
  member: string;
  detail: string;
  assignment: string;
  waiting: string;
  status: Status;
};

const queueRows: QueueRow[] = [
  {
    id: 'pm',
    member: 'Priya Menon',
    detail: 'UX/UI · Cohort 7',
    assignment: 'Competitor audit: five UX portfolios',
    waiting: '2 days 4 hrs',
    status: 'submitted',
  },
  {
    id: 'ds',
    member: 'Diego Salazar',
    detail: 'Web development · Cohort 7',
    assignment: 'Rebuild the pricing page in responsive CSS',
    waiting: '9 hrs',
    status: 'changes',
  },
];

function ThemePanel({ theme }: { theme: Theme }) {
  const [dialogOpen, setDialogOpen] = useState(false);

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
          <Badge key={s} status={s} />
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
        <Button size="sm" loading>
          Saving
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
          <Badge status="due-soon" />
        </div>
        <p className="mt-2 text-body text-ink-body">Set by Marguerite Ellis · Digital marketing</p>
        <p className="mt-1 text-meta text-ink-meta">
          Due Fri 3 Oct, 11:59 PM · in 4 days · 10 points
        </p>
        <Button variant="secondary" size="sm" className="mt-4">
          Open assignment
        </Button>
      </Card>

      <h3 className="mt-6 text-card-title">Table</h3>
      <div className="mt-3">
        <Table
          caption="Submissions waiting for review"
          rows={queueRows}
          getRowKey={(r) => r.id}
          columns={[
            {
              key: 'member',
              header: 'Member',
              render: (r) => (
                <div>
                  <p className="text-card-title text-ink">{r.member}</p>
                  <p className="text-meta text-ink-meta">{r.detail}</p>
                </div>
              ),
            },
            { key: 'assignment', header: 'Assignment', render: (r) => r.assignment },
            {
              key: 'waiting',
              header: 'Waiting',
              render: (r) => <span className="text-ink-meta">{r.waiting}</span>,
            },
            { key: 'status', header: 'Status', render: (r) => <Badge status={r.status} /> },
          ]}
        />
      </div>

      <h3 className="mt-6 text-card-title">Dialog</h3>
      <Button variant="secondary" className="mt-3" onClick={() => setDialogOpen(true)}>
        Open dialog
      </Button>
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        title="Create twelve weekly assignments"
        actions={
          <>
            <Button variant="secondary" size="sm" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={() => setDialogOpen(false)}>
              Create 12 drafts
            </Button>
          </>
        }
      >
        One per week, starting the week the cohort starts. You can edit any of them afterwards.
      </Dialog>
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
