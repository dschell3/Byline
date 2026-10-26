import { useEffect, useState } from 'react';
import { Badge } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import { dueLabel, fetchWork, pointsLabel, type WorkGroup, type WorkItem } from '../lib/work';

// P10, "/" for a member who has work (X10 on phones). SCRUM-14.
// Six groups in the order the API sends them; empty ones are left out.

type State = { status: 'loading' } | { status: 'ready'; groups: WorkGroup[] } | { status: 'error' };

function Row({ item, timeZone }: { item: WorkItem; timeZone: string }) {
  const due = dueLabel(item.due_at, timeZone);
  // Changes requested: a heavy edge and a tinted card as well as the badge's icon and colour,
  // so it is the one row nobody scrolls past, and it still reads without colour.
  const changes = item.status === 'changes';
  return (
    <Card
      className={`flex flex-col gap-2 !p-4 sm:flex-row sm:items-center sm:justify-between sm:gap-4 ${
        changes ? 'border-l-4 border-l-status-changes-text bg-status-changes-fill' : ''
      }`}
    >
      <div className="min-w-0">
        <p className="m-0 text-card-title text-ink">{item.title}</p>
        <p className="m-0 mt-0.5 text-meta text-ink-meta">
          Set by {item.set_by} · {due.date}
          {due.relative && ` (${due.relative})`} · {pointsLabel(item.points)}
        </p>
      </div>
      <Badge status={item.status} />
    </Card>
  );
}

export default function MyWork({ timeZone }: { timeZone: string }) {
  const [state, setState] = useState<State>({ status: 'loading' });

  useEffect(() => {
    let current = true;
    fetchWork()
      .then((groups) => current && setState({ status: 'ready', groups }))
      .catch(() => current && setState({ status: 'error' }));
    return () => {
      current = false;
    };
  }, []);

  if (state.status === 'loading') return null;
  if (state.status === 'error') {
    return (
      <p role="alert" className="p-8 text-body text-ink">
        Your work could not be loaded. Reload the page to try again.
      </p>
    );
  }

  const groups = state.groups.filter((group) => group.items.length > 0);
  return (
    <main className="flex-1 px-4 pb-12 pt-6 lg:px-14 lg:pt-14">
      <h1 className="m-0 text-page-title tracking-[-0.01em]">My work</h1>
      {groups.length === 0 && (
        <p className="m-0 mt-2 text-body text-ink-body">Nothing to show right now.</p>
      )}
      <div className="mt-6 flex max-w-[960px] flex-col gap-8">
        {groups.map((group) => (
          <section key={group.key} aria-labelledby={`group-${group.key}`}>
            <h2 id={`group-${group.key}`} className="m-0 mb-3 text-section">
              {group.label}{' '}
              <span className="text-meta font-medium text-ink-meta">{group.items.length}</span>
            </h2>
            <ul className="m-0 flex list-none flex-col gap-3 p-0">
              {group.items.map((item) => (
                <li key={item.id}>
                  <Row item={item} timeZone={timeZone} />
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </main>
  );
}
