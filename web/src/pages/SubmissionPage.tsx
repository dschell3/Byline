import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Table, type Column } from '../components/ui/Table';
import { fetchHome } from '../lib/home';
import { pointsLabel } from '../lib/work';
import { formatInstant, viewerTimeZone } from '../lib/time';
import {
  badgeStatus,
  decisionLabel,
  fetchSubmission,
  fileName,
  postComment,
  scoreTotal,
  threads,
  versionLabel,
  SubmissionError,
  type Comment,
  type Review,
  type Score,
  type Submission,
  type Version,
} from '../lib/submission';

// P14, "/s/:id": every version of one piece of work, its reviews and the comments on each,
// oldest first. SCRUM-22. One id names a version; the page shows the whole history and
// scrolls to the version that was asked for.

type State =
  | { status: 'loading' }
  | { status: 'ready'; submission: Submission }
  | { status: 'forbidden' }
  | { status: 'error' };

const SECTION_TITLE = 'm-0 font-serif text-[18px] font-semibold leading-7 text-ink';
const EYEBROW = 'm-0 text-meta uppercase tracking-[0.06em] text-ink-meta';

function When({ iso, timeZone }: { iso: string; timeZone: string }) {
  const at = formatInstant(iso, timeZone);
  return (
    <time dateTime={iso} title={at.full}>
      {at.date}, {at.time}
    </time>
  );
}

const scoreColumns: Column<Score>[] = [
  { key: 'criterion', header: 'Criterion', render: (s) => s.text },
  {
    key: 'score',
    header: 'Score',
    render: (s) => (
      <span className="whitespace-nowrap font-semibold text-ink">
        {s.score} / {s.max_points}
      </span>
    ),
  },
  { key: 'note', header: 'Note', render: (s) => s.note ?? '' },
];

function ReviewCard({ review, timeZone }: { review: Review; timeZone: string }) {
  return (
    <Card className="!p-5">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
        <p className="m-0 text-card-title text-ink">{decisionLabel(review)}</p>
        <p className="m-0 text-meta text-ink-meta">
          <When iso={review.created_at} timeZone={timeZone} />
          {review.scores.length > 0 && ` · ${scoreTotal(review.scores)}`}
        </p>
      </div>
      {review.reason && (
        <p className="m-0 mt-3 whitespace-pre-line text-body text-ink-body">{review.reason}</p>
      )}
      {review.scores.length > 0 && (
        <div className="mt-4">
          <Table
            columns={scoreColumns}
            rows={review.scores}
            getRowKey={(s) => String(s.criterion_id)}
            caption="Scores against the assessment criteria"
          />
        </div>
      )}
    </Card>
  );
}

function CommentRow({
  comment,
  timeZone,
  reply = false,
  onReply = undefined,
}: {
  comment: Comment;
  timeZone: string;
  reply?: boolean;
  onReply?: (() => void) | undefined;
}) {
  return (
    <div className={reply ? 'ml-6 border-l-2 border-line pl-4' : ''}>
      <p className="m-0 text-meta text-ink-meta">
        <span className="font-semibold text-ink">{comment.author_name}</span> ·{' '}
        <When iso={comment.created_at} timeZone={timeZone} />
      </p>
      <p className="m-0 mt-1 whitespace-pre-line text-body text-ink-body">{comment.body}</p>
      {onReply && (
        <button
          type="button"
          onClick={onReply}
          className="mt-1 bg-transparent p-0 text-meta font-semibold text-link hover:underline"
        >
          Reply
        </button>
      )}
    </div>
  );
}

function CommentForm({
  versionId,
  parent,
  onPosted,
  onCancel,
}: {
  versionId: number;
  parent: Comment | null;
  onPosted: (comment: Comment) => void;
  onCancel: () => void;
}) {
  const [body, setBody] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const fieldId = `comment-${versionId}-${parent?.id ?? 'new'}`;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!body.trim()) {
      setError('Write something first.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const posted = await postComment(versionId, body.trim(), parent?.id ?? null);
      setBody('');
      onPosted(posted);
    } catch {
      setError('Your comment was not saved. Try again.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className={parent ? 'ml-6 pl-4' : ''}>
      <label htmlFor={fieldId} className="m-0 block text-meta font-medium text-ink-body">
        {parent ? `Reply to ${parent.author_name}` : 'Add a comment'}
      </label>
      <textarea
        id={fieldId}
        value={body}
        onChange={(event) => setBody(event.target.value)}
        rows={3}
        maxLength={4000}
        className="mt-1 w-full rounded-md border border-line bg-surface p-3 text-body text-ink focus:outline focus:outline-2 focus:outline-primary"
      />
      {error && (
        <p role="alert" className="m-0 mt-1 text-meta text-danger">
          {error}
        </p>
      )}
      <div className="mt-2 flex gap-2">
        <Button type="submit" size="sm" loading={busy}>
          {parent ? 'Post reply' : 'Post comment'}
        </Button>
        {parent && (
          <Button type="button" size="sm" variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
}

function VersionSection({
  version,
  total,
  current,
  timeZone,
  onComment,
}: {
  version: Version;
  total: number;
  current: boolean;
  timeZone: string;
  onComment: (versionId: number, comment: Comment) => void;
}) {
  const [replyTo, setReplyTo] = useState<Comment | null>(null);
  const grouped = threads(version.comments);

  return (
    <section
      id={`version-${version.id}`}
      aria-labelledby={`version-${version.id}-title`}
      aria-current={current ? 'true' : undefined}
      className={`rounded-xl border bg-surface p-5 lg:p-6 ${
        current ? 'border-primary' : 'border-line'
      }`}
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 id={`version-${version.id}-title`} className={SECTION_TITLE}>
            {versionLabel(version.version, total)}
          </h2>
          <p className="m-0 mt-0.5 text-meta text-ink-meta">
            Submitted <When iso={version.submitted_at} timeZone={timeZone} />
          </p>
        </div>
        <span className="self-start">
          <Badge status={badgeStatus(version.status)} />
        </span>
      </div>

      {version.file_keys.length > 0 && (
        <ul className="m-0 mt-4 flex list-none flex-col gap-1 p-0">
          {version.file_keys.map((key) => (
            <li key={key} className="text-body text-ink-body">
              {fileName(key)}
              <span className="text-meta text-ink-meta"> · download arrives with file storage</span>
            </li>
          ))}
        </ul>
      )}

      <h3 className="m-0 mt-6 text-card-title text-ink">Review</h3>
      {version.reviews.length === 0 ? (
        <p className="m-0 mt-2 text-body text-ink-body">Not reviewed yet.</p>
      ) : (
        <div className="mt-3 flex flex-col gap-3">
          {version.reviews.map((review) => (
            <ReviewCard key={review.id} review={review} timeZone={timeZone} />
          ))}
        </div>
      )}

      <h3 className="m-0 mt-6 text-card-title text-ink">
        Comments{' '}
        <span className="text-meta font-medium text-ink-meta">{version.comments.length}</span>
      </h3>
      <div className="mt-3 flex flex-col gap-4">
        {grouped.map((thread) => (
          <div key={thread.comment.id} className="flex flex-col gap-3">
            <CommentRow
              comment={thread.comment}
              timeZone={timeZone}
              onReply={() => setReplyTo(thread.comment)}
            />
            {thread.replies.map((item) => (
              <CommentRow key={item.id} comment={item} timeZone={timeZone} reply />
            ))}
            {replyTo?.id === thread.comment.id && (
              <CommentForm
                versionId={version.id}
                parent={thread.comment}
                onPosted={(posted) => {
                  setReplyTo(null);
                  onComment(version.id, posted);
                }}
                onCancel={() => setReplyTo(null)}
              />
            )}
          </div>
        ))}
        {replyTo === null && (
          <CommentForm
            versionId={version.id}
            parent={null}
            onPosted={(posted) => onComment(version.id, posted)}
            onCancel={() => undefined}
          />
        )}
      </div>
    </section>
  );
}

export default function SubmissionPage() {
  const { id = '' } = useParams();
  const [state, setState] = useState<State>({ status: 'loading' });
  // The profile's zone first, then the browser's (SCRUM-15), the same source P10 uses.
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
    fetchSubmission(id)
      .then((submission) => current && setState({ status: 'ready', submission }))
      .catch((error: unknown) => {
        if (!current) return;
        const forbidden = error instanceof SubmissionError && error.status === 403;
        setState({ status: forbidden ? 'forbidden' : 'error' });
      });
    return () => {
      current = false;
    };
  }, [id]);

  useEffect(() => {
    if (state.status !== 'ready') return;
    document.getElementById(`version-${id}`)?.scrollIntoView({ block: 'start' });
  }, [state.status, id]);

  const addComment = useCallback((versionId: number, comment: Comment) => {
    setState((previous) => {
      if (previous.status !== 'ready') return previous;
      return {
        status: 'ready',
        submission: {
          ...previous.submission,
          versions: previous.submission.versions.map((v) =>
            v.id === versionId ? { ...v, comments: [...v.comments, comment] } : v,
          ),
        },
      };
    });
  }, []);

  if (state.status === 'loading') return null;
  if (state.status === 'forbidden') {
    return (
      <main className="flex-1 px-4 py-10 lg:px-14">
        <h1 className="m-0 text-page-title">You do not have access to this</h1>
        <p className="m-0 mt-2 text-body text-ink-body">
          Only the person who handed it in and their supervisors can open a submission.{' '}
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
        This submission could not be loaded. Reload the page to try again.
      </p>
    );
  }

  const { submission } = state;
  const { assignment, member, versions } = submission;
  const requested = versions.find((v) => String(v.id) === id) ?? versions[versions.length - 1];
  const due = assignment.due_at ? formatInstant(assignment.due_at, timeZone) : null;

  return (
    <main className="flex-1 px-4 pb-12 pt-6 lg:px-14 lg:pt-14">
      <p className={EYEBROW}>Submission</p>
      <div className="mt-1 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <h1 className="m-0 text-page-title tracking-[-0.01em]">{assignment.title}</h1>
        <span className="self-start">
          <Badge status={badgeStatus(requested.status)} />
        </span>
      </div>
      <p className="m-0 mt-2 text-body text-ink-body">
        {member.full_name} · {pointsLabel(assignment.points_value)}
        {due && (
          <>
            {' '}
            · Due{' '}
            <time dateTime={assignment.due_at ?? undefined} title={due.full}>
              {due.date}, {due.time}
            </time>
          </>
        )}
      </p>

      <nav aria-label="Versions" className="mt-5">
        <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
          {versions.map((v) => (
            <li key={v.id}>
              <Link
                to={`/s/${v.id}`}
                aria-current={v.id === requested.id ? 'page' : undefined}
                className={`inline-flex h-btn-sm items-center rounded-md border px-3 text-[13px] font-semibold no-underline ${
                  v.id === requested.id
                    ? 'border-primary bg-primary text-primary-on'
                    : 'border-line bg-surface text-ink hover:bg-surface-recessed'
                }`}
              >
                {versionLabel(v.version, versions.length)}
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      <div className="mt-6 flex max-w-[960px] flex-col gap-6">
        {versions.map((v) => (
          <VersionSection
            key={v.id}
            version={v}
            total={versions.length}
            current={v.id === requested.id}
            timeZone={timeZone}
            onComment={addComment}
          />
        ))}
      </div>
    </main>
  );
}
