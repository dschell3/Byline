import { useEffect, useState, type ReactNode } from 'react';
import { Link, useParams } from 'react-router';
import { Badge } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import {
  audienceLine,
  criterionPoints,
  fetchAssignment,
  fileSize,
  isNotYours,
  nextAction,
  paragraphs,
  pointsAvailable,
  yourTime,
  type Assignment,
} from '../lib/assignment';
import { fetchHome } from '../lib/home';
import { describeLatePolicy } from '../lib/latePolicy';
import { dueLabel, formatInstant, viewerTimeZone } from '../lib/time';

// P12, "/a/:id" (X12 on phones): one assignment as the intern it was set for reads it. SCRUM-18.
// The assessment criteria are their own card, drawn as a checklist, because they are what the
// reviewer scores against (P20). They are never folded into the description.

type State =
  | { status: 'loading' }
  | { status: 'ready'; assignment: Assignment }
  | { status: 'forbidden' }
  | { status: 'error' };

const SECTION_TITLE = 'm-0 font-serif text-[18px] font-semibold leading-7 text-ink';
const ACTION =
  'inline-flex h-btn w-full items-center justify-center rounded-md px-4 text-button no-underline ' +
  'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary';

function LinkIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="mt-0.5 shrink-0"
    >
      <path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1" />
      <path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" />
    </svg>
  );
}

function FileIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinejoin="round"
      aria-hidden="true"
      className="mt-0.5 shrink-0"
    >
      <path d="M7 3h7l5 5v12a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zM14 3v5h5" />
    </svg>
  );
}

function DueCard({ assignment, timeZone }: { assignment: Assignment; timeZone: string }) {
  const due = dueLabel(assignment.due_at, timeZone);
  const action = nextAction(assignment);
  let button: ReactNode;
  let note: string;
  if (action.kind === 'view') {
    button = (
      <Link
        to={action.to}
        className={`${ACTION} border border-line bg-surface text-ink hover:bg-surface-recessed`}
      >
        View submission
      </Link>
    );
    note = 'You have handed this in. Open it for its versions, feedback and comments.';
  } else if (action.kind === 'submit') {
    button = (
      <Link to={action.to} className={`${ACTION} bg-primary text-primary-on hover:bg-primary/90`}>
        Submit my work
      </Link>
    );
    note = 'Text, a file, a link or a pull request.';
  } else {
    button = null;
    note = 'This can no longer be submitted.';
  }

  return (
    <Card className="order-2 flex flex-col gap-3 !p-5 lg:order-none">
      <div>
        <p className="m-0 text-meta text-ink-meta">Due</p>
        <p className="m-0 mt-0.5 text-[17px] font-semibold leading-6 text-ink">
          {assignment.due_at ? (
            <time dateTime={assignment.due_at} title={due.full}>
              {due.date}, {due.time}
            </time>
          ) : (
            due.date
          )}
        </p>
        {assignment.due_at && (
          <p className="m-0 mt-0.5 text-meta text-ink-meta">
            {due.relative} · {yourTime(timeZone, new Date(assignment.due_at))}
          </p>
        )}
      </div>
      {button}
      <p
        className={`m-0 text-meta ${action.kind === 'closed' ? 'font-semibold text-status-overdue-text' : 'text-ink-meta'}`}
      >
        {note}
      </p>
    </Card>
  );
}

function Criteria({ assignment }: { assignment: Assignment }) {
  return (
    <Card className="order-4 !p-[22px] lg:order-none">
      <section aria-labelledby="criteria-title">
        <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
          <h2 id="criteria-title" className={SECTION_TITLE}>
            What you will be scored against
          </h2>
          <p className="m-0 text-meta text-ink-meta">{pointsAvailable(assignment.points)}</p>
        </div>
        {assignment.criteria.length === 0 ? (
          <p className="m-0 mt-2 text-body text-ink-body">
            No assessment criteria have been set for this assignment. Ask {assignment.set_by} what
            they will look for.
          </p>
        ) : (
          <>
            <p className="m-0 mt-2 text-body text-ink-body">
              These are the exact criteria your reviewer sees beside your work.
            </p>
            <ul className="m-0 mt-3 flex list-none flex-col gap-[9px] p-0">
              {assignment.criteria.map((criterion) => (
                <li
                  key={criterion.id}
                  className="flex items-start gap-3 rounded-[10px] border border-line bg-surface-recessed px-3.5 py-3"
                >
                  {/* An empty box, not a control: the reviewer fills this list in, on P20. */}
                  <span
                    aria-hidden="true"
                    className="mt-px h-[18px] w-[18px] shrink-0 rounded-[5px] border-[1.5px] border-primary bg-surface"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="m-0 text-[14px] font-semibold leading-5 text-ink">
                      {criterion.text}
                    </p>
                    {criterion.detail && (
                      <p className="m-0 mt-0.5 text-meta text-ink-meta">{criterion.detail}</p>
                    )}
                  </div>
                  <p className="m-0 whitespace-nowrap text-meta text-ink-meta">
                    {criterionPoints(criterion.max_points)}
                  </p>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </Card>
  );
}

function Reference({ assignment }: { assignment: Assignment }) {
  const { reference_links: links, attachments } = assignment;
  if (links.length === 0 && attachments.length === 0) return null;
  return (
    <Card className="order-6 !p-5 lg:order-none">
      <section aria-labelledby="reference-title">
        <h2 id="reference-title" className="m-0 text-card-title text-ink">
          Reference
        </h2>
        <ul className="m-0 mt-3 flex list-none flex-col gap-2.5 p-0">
          {links.map((link) => (
            <li key={link.url} className="flex items-start gap-2.5 text-link">
              <LinkIcon />
              <a
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                className="min-w-0 break-words text-[14px] font-semibold leading-5 text-link"
              >
                {link.label}
                <span className="sr-only"> (opens in a new tab)</span>
              </a>
            </li>
          ))}
          {attachments.map((file) => (
            <li key={file.name} className="flex items-start gap-2.5 text-ink-body">
              <FileIcon />
              <span className="min-w-0 break-words text-[14px] font-semibold leading-5 text-ink">
                {file.name}
                {file.size_bytes !== null && (
                  <span className="font-medium text-ink-meta"> · {fileSize(file.size_bytes)}</span>
                )}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </Card>
  );
}

export default function AssignmentPage() {
  const { id = '' } = useParams();
  const [state, setState] = useState<State>({ status: 'loading' });
  // The profile's zone first, then the browser's (SCRUM-15), the same source P10 and P14 use.
  const [timeZone, setTimeZone] = useState(() => viewerTimeZone(null));

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
    fetchAssignment(id)
      .then((assignment) => current && setState({ status: 'ready', assignment }))
      .catch((error: unknown) => {
        if (current) setState({ status: isNotYours(error) ? 'forbidden' : 'error' });
      });
    return () => {
      current = false;
    };
  }, [id]);

  if (state.status === 'loading') return null;
  if (state.status === 'forbidden') {
    return (
      <main className="flex-1 px-4 py-10 lg:px-14">
        <h1 className="m-0 text-page-title">You do not have access to this</h1>
        <p className="m-0 mt-2 text-body text-ink-body">
          Only the people an assignment was set for can open it.{' '}
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
        This assignment could not be loaded. Reload the page to try again.
      </p>
    );
  }

  const { assignment } = state;
  const brief = paragraphs(assignment.description);
  const latePolicy = describeLatePolicy(assignment, timeZone);
  const setAt = formatInstant(assignment.set_at, timeZone);
  // On phones everything is one column in X12's order: heading, due and the button, the brief,
  // the checklist, then late policy and reference. From lg up it is the P12 two-column grid.
  const column = 'contents lg:flex lg:flex-col lg:gap-[18px]';

  return (
    <main className="flex-1 px-4 pb-12 pt-6 lg:px-10 lg:pt-8">
      <div className="flex max-w-[1360px] flex-col gap-3.5 lg:grid lg:grid-cols-[1.6fr_0.8fr] lg:items-start lg:gap-6">
        <div className={column}>
          <header className="order-1 flex flex-col gap-2.5 lg:order-none">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
              <Badge status={assignment.status} />
              <p className="m-0 text-meta text-ink-meta">{audienceLine(assignment)}</p>
            </div>
            <h1 className="m-0 text-[22px] font-semibold leading-[29px] tracking-[-0.01em] lg:text-page-title">
              {assignment.title}
            </h1>
            <p className="m-0 text-body text-ink-body">
              Set by {assignment.set_by} on{' '}
              <time dateTime={assignment.set_at} title={setAt.full}>
                {setAt.date}
              </time>
            </p>
          </header>

          <Card className="order-3 !p-[22px] lg:order-none">
            <section aria-labelledby="brief-title" className="flex flex-col gap-[11px]">
              <h2 id="brief-title" className={SECTION_TITLE}>
                What to do
              </h2>
              {brief.length === 0 ? (
                <p className="m-0 text-body text-ink-body">
                  No description was written for this assignment.
                </p>
              ) : (
                brief.map((paragraph) => (
                  <p
                    key={paragraph}
                    className="m-0 whitespace-pre-line break-words text-body text-ink-body"
                  >
                    {paragraph}
                  </p>
                ))
              )}
            </section>
          </Card>

          <Criteria assignment={assignment} />
        </div>

        <div className={column}>
          <DueCard assignment={assignment} timeZone={timeZone} />

          {latePolicy && (
            <Card className="order-5 !p-5 lg:order-none">
              <section aria-labelledby="late-title">
                <h2 id="late-title" className="m-0 text-card-title text-ink">
                  Late policy
                </h2>
                <p className="m-0 mt-2 text-body text-ink-body">{latePolicy}</p>
              </section>
            </Card>
          )}

          <Reference assignment={assignment} />
        </div>
      </div>
    </main>
  );
}
