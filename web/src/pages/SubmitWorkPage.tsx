import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { fetchWork, type WorkItem } from '../lib/work';

type SubmissionKind = 'text' | 'link' | 'pr';

type LoadState =
  | {
      assignmentId: number;
      status: 'ready';
      assignment: WorkItem | null;
    }
  | {
      assignmentId: number;
      status: 'error';
    };

const CHOICES: { kind: SubmissionKind; label: string }[] = [
  { kind: 'text', label: 'Write text' },
  { kind: 'link', label: 'Submit a link' },
  { kind: 'pr', label: 'GitHub pull request' },
];

export default function SubmitWorkPage() {
  const { id } = useParams();

  const assignmentId = Number(id);
  const validId =
    typeof id === 'string' &&
    /^\d+$/.test(id) &&
    Number.isSafeInteger(assignmentId) &&
    assignmentId > 0;

  const [loadState, setLoadState] = useState<LoadState | null>(null);
  const [kind, setKind] = useState<SubmissionKind>('text');
  const [content, setContent] = useState('');

  useEffect(() => {
    if (!validId) return;

    let active = true;

    fetchWork()
      .then((groups) => {
        if (!active) return;

        const item = groups
          .flatMap((group) => group.items)
          .find((work) => work.id === assignmentId);

        setLoadState({
          assignmentId,
          status: 'ready',
          assignment: item ?? null,
        });
      })
      .catch(() => {
        if (active) {
          setLoadState({
            assignmentId,
            status: 'error',
          });
        }
      });

    return () => {
      active = false;
    };
  }, [assignmentId, validId]);

  // Invalid IDs are handled directly during rendering,
  // without calling setState inside useEffect.
  if (!validId) {
    return (
      <main className="p-8">
        <p role="alert">Invalid assignment.</p>
        <Link to="/">Back to My Work</Link>
      </main>
    );
  }

  // Only show loaded data for the current assignment.
  if (!loadState || loadState.assignmentId !== assignmentId) {
    return <main className="p-8">Loading assignment...</main>;
  }

  if (loadState.status === 'error') {
    return (
      <main className="p-8">
        <p role="alert">Could not load your assignment.</p>
        <Link to="/">Back to My Work</Link>
      </main>
    );
  }

  const assignment = loadState.assignment;

  if (!assignment) {
    return (
      <main className="p-8">
        <p role="alert">Assignment not found in your work.</p>
        <Link to="/">Back to My Work</Link>
      </main>
    );
  }

  return (
    <main className="flex-1 px-4 pb-12 pt-6 lg:px-14 lg:pt-14">
      <div className="max-w-[800px]">
        <Link to="/" className="text-meta text-link">
          Back to My Work
        </Link>

        <h1 className="mt-5 text-page-title">Submit work</h1>

        <p className="mt-2 text-body text-ink-body">{assignment.title}</p>

        <Card className="mt-6 !p-6">
          <h2 className="text-section">Choose how to submit</h2>

          <div className="mt-4 flex flex-wrap gap-3">
            {CHOICES.map((choice) => (
              <Button
                key={choice.kind}
                type="button"
                variant={kind === choice.kind ? 'primary' : 'secondary'}
                aria-pressed={kind === choice.kind}
                onClick={() => {
                  setKind(choice.kind);
                  setContent('');
                }}
              >
                {choice.label}
              </Button>
            ))}

            <Button type="button" variant="secondary" disabled>
              File upload — coming with file storage
            </Button>
          </div>

          <div className="mt-6">
            {kind === 'text' ? (
              <label htmlFor="submission-text" className="block">
                <span className="mb-2 block text-meta font-semibold">Your submission</span>

                <textarea
                  id="submission-text"
                  rows={8}
                  value={content}
                  onChange={(event) => setContent(event.target.value)}
                  placeholder="Enter your work here..."
                  className="w-full rounded-md border border-line bg-surface p-3 text-body text-ink"
                />
              </label>
            ) : (
              <label htmlFor="submission-url" className="block">
                <span className="mb-2 block text-meta font-semibold">
                  {kind === 'pr' ? 'GitHub pull request URL' : 'Link URL'}
                </span>

                <input
                  id="submission-url"
                  type="url"
                  value={content}
                  onChange={(event) => setContent(event.target.value)}
                  placeholder={
                    kind === 'pr'
                      ? 'https://github.com/owner/repository/pull/123'
                      : 'https://example.com/your-work'
                  }
                  className="h-btn w-full rounded-md border border-line bg-surface px-3 text-body text-ink"
                />
              </label>
            )}
          </div>

          <p className="mt-5 text-meta text-ink-meta">
            Submission saving and validation will be connected to the backend in the next step.
            Nothing is sent yet.
          </p>

          <div className="mt-5">
            <Button type="button" disabled>
              Submit work
            </Button>
          </div>
        </Card>
      </div>
    </main>
  );
}
