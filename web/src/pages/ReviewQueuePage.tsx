import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router';
import { When } from '../components/When';
import { Badge } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import { Select } from '../components/ui/Select';
import { Table, type Column } from '../components/ui/Table';
import { fetchHome } from '../lib/home';
import {
  DEFAULT_FILTERS,
  QueueError,
  STATUS_OPTIONS,
  emptyMessage,
  fetchQueue,
  isLate,
  waitingFor,
  type Filters,
  type Queue,
  type QueueRow,
  type StatusFilter,
} from '../lib/reviewQueue';
import { badgeStatus } from '../lib/submission';
import { viewerTimeZone } from '../lib/time';

// P19, "/review": everything waiting for a supervisor, oldest first (SCRUM-24).
// The order is fixed on purpose. There is no sort control to find: the oldest work is on top.

type State =
  | { status: 'loading' }
  | { status: 'ready'; queue: Queue }
  | { status: 'forbidden' }
  | { status: 'error' };

export default function ReviewQueuePage() {
  const [state, setState] = useState<State>({ status: 'loading' });
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [timeZone, setTimeZone] = useState(() => viewerTimeZone(null));
  // The page reads the clock once per load, so a row never changes under the reader.
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    let current = true;
    fetchHome()
      .then((home) => current && home && setTimeZone(viewerTimeZone(home.timezone)))
      .catch(() => undefined);
    return () => {
      current = false;
    };
  }, []);

  useEffect(() => {
    let current = true;
    fetchQueue(filters)
      .then((queue) => {
        if (!current) return;
        setNow(new Date());
        setState({ status: 'ready', queue });
      })
      .catch((error: unknown) => {
        if (!current) return;
        setState({
          status: error instanceof QueueError && error.status === 403 ? 'forbidden' : 'error',
        });
      });
    return () => {
      current = false;
    };
  }, [filters]);

  const columns = useMemo<Column<QueueRow>[]>(
    () => [
      {
        key: 'intern',
        header: 'Intern',
        render: (row) => (
          <div>
            <Link to={`/s/${row.submission_id}`} className="font-semibold text-ink hover:underline">
              {row.intern_name}
            </Link>
            <p className="m-0 text-meta text-ink-meta">
              {[row.team_name, row.cohort_name].filter(Boolean).join(' · ')}
            </p>
          </div>
        ),
      },
      { key: 'assignment', header: 'Assignment', render: (row) => row.assignment_title },
      { key: 'track', header: 'Track', render: (row) => row.track_name ?? '—' },
      {
        key: 'submitted',
        header: 'Handed in',
        render: (row) => (
          <span className="whitespace-nowrap">
            <When iso={row.submitted_at} timeZone={timeZone} />
          </span>
        ),
      },
      {
        key: 'waiting',
        header: 'Waiting',
        render: (row) =>
          row.status === 'submitted' ? (
            <span
              className={`whitespace-nowrap ${isLate(row.submitted_at, now) ? 'font-semibold text-status-overdue-text' : ''}`}
            >
              {waitingFor(row.submitted_at, now)}
              {isLate(row.submitted_at, now) && ' · long wait'}
            </span>
          ) : (
            <Badge status={badgeStatus(row.status)} />
          ),
      },
    ],
    [timeZone, now],
  );

  if (state.status === 'forbidden') {
    return (
      <main className="flex-1 px-4 py-10 lg:px-14">
        <h1 className="m-0 text-page-title">You do not have access to this</h1>
        <p className="m-0 mt-2 text-body text-ink-body">
          Only supervisors can open the review queue.{' '}
          <Link to="/" className="text-link">
            Back to My work
          </Link>
        </p>
      </main>
    );
  }
  if (state.status === 'error') {
    return (
      <p role="alert" className="p-8 text-body text-ink">
        The review queue could not be loaded. Reload the page to try again.
      </p>
    );
  }
  if (state.status === 'loading') return null;

  const { rows, filters: options } = state.queue;
  const empty = emptyMessage(filters);
  const set = (patch: Partial<Filters>) => setFilters((previous) => ({ ...previous, ...patch }));
  const waiting = filters.status === 'submitted';

  return (
    <main className="flex-1 px-4 py-8 lg:px-14">
      <h1 className="m-0 text-page-title">Review queue</h1>
      <p className="m-0 mt-1 text-body text-ink-body" aria-live="polite">
        {rows.length === 0
          ? 'Nothing here right now.'
          : `${rows.length} ${waiting ? 'waiting, oldest first' : rows.length === 1 ? 'submission' : 'submissions'}`}
      </p>

      <form
        aria-label="Filter the queue"
        className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
        onSubmit={(event) => event.preventDefault()}
      >
        <Select label="Team" value={filters.team} onChange={(e) => set({ team: e.target.value })}>
          <option value="">All teams</option>
          {options.teams.map((o) => (
            <option key={o.id} value={o.id}>
              {o.name}
            </option>
          ))}
        </Select>
        <Select
          label="Cohort"
          value={filters.cohort}
          onChange={(e) => set({ cohort: e.target.value })}
        >
          <option value="">All cohorts</option>
          {options.cohorts.map((o) => (
            <option key={o.id} value={o.id}>
              {o.name}
            </option>
          ))}
        </Select>
        <Select
          label="Assignment"
          value={filters.assignment}
          onChange={(e) => set({ assignment: e.target.value })}
        >
          <option value="">All assignments</option>
          {options.assignments.map((o) => (
            <option key={o.id} value={o.id}>
              {o.name}
            </option>
          ))}
        </Select>
        <Select
          label="Status"
          value={filters.status}
          onChange={(e) => set({ status: e.target.value as StatusFilter })}
        >
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </Select>
      </form>

      <div className="mt-6">
        {rows.length === 0 ? (
          <Card className="!py-12 text-center">
            <p className="m-0 text-card-title text-ink">{empty.title}</p>
            <p className="m-0 mx-auto mt-2 max-w-md text-body text-ink-body">{empty.detail}</p>
            {empty.title === 'Nothing matches these filters' && (
              <button
                type="button"
                onClick={() => setFilters(DEFAULT_FILTERS)}
                className="mt-4 bg-transparent p-0 text-body font-semibold text-link hover:underline"
              >
                Clear filters
              </button>
            )}
          </Card>
        ) : (
          <Table
            columns={columns}
            rows={rows}
            getRowKey={(row) => String(row.submission_id)}
            caption="Submissions, oldest first"
          />
        )}
      </div>
    </main>
  );
}
