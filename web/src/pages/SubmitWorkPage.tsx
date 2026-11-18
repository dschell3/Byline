import { useEffect, useState, useSyncExternalStore } from 'react';
import { Link, useNavigate, useOutletContext, useParams } from 'react-router';
import type { CurrentUser } from '../lib/auth';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { FileUpload } from '../components/FileUpload';
import { ResubmitFeedback } from '../components/ResubmitFeedback';
import {
  clearDraft,
  emptyDraft,
  hasContent,
  loadDraft,
  saveDraft,
  type Draft,
  type SubmissionKind,
} from '../lib/draft';
import { FALLBACK_LIMITS, fetchLimits, type Limits } from '../lib/files';
import { classifyFailure, FAILURE_MESSAGE, isTooLong } from '../lib/submitFailure';
import { isResubmit } from '../lib/resubmit';
import { createSubmission } from '../lib/submitWork';
import { fetchWork, type WorkItem } from '../lib/work';

// SCRUM-20: what is typed here is kept on this device as it is typed, one draft per assignment.
type DraftState = {
  assignmentId: number;
  userId: number;
  draft: Draft;
  restored: boolean;
  saved: boolean;
};

function openDraft(assignmentId: number, validId: boolean, userId: number): DraftState {
  const draft = validId ? loadDraft(`${userId}:${assignmentId}`) : emptyDraft();
  return { assignmentId, userId, draft, restored: hasContent(draft), saved: true };
}

function subscribeOnline(callback: () => void) {
  window.addEventListener('online', callback);
  window.addEventListener('offline', callback);
  return () => {
    window.removeEventListener('online', callback);
    window.removeEventListener('offline', callback);
  };
}

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
  { kind: 'file', label: 'Upload files' },
];

const MAX_FILES = 10;

export default function SubmitWorkPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const user = useOutletContext<CurrentUser>();

  const assignmentId = Number(id);
  const validId =
    typeof id === 'string' &&
    /^\d+$/.test(id) &&
    Number.isSafeInteger(assignmentId) &&
    assignmentId > 0;

  const [loadState, setLoadState] = useState<LoadState | null>(null);
  const [draftState, setDraftState] = useState(() => openDraft(assignmentId, validId, user.id));
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  // SCRUM-83: every limit the form states comes from the API; the fallback mirrors it.
  const [limits, setLimits] = useState<Limits>(FALLBACK_LIMITS);
  // A different assignment opens its own draft.
  if (draftState.assignmentId !== assignmentId || draftState.userId !== user.id) {
    setDraftState(openDraft(assignmentId, validId, user.id));
  }
  const online = useSyncExternalStore(
    subscribeOnline,
    () => navigator.onLine,
    () => true,
  );
  const { draft } = draftState;
  const draftKey = `${user.id}:${assignmentId}`;
  const kind = draft.kind;
  const content = draft.values[kind];
  const maxChars = limits.max_text_chars;
  // A file submission needs a file; the note is optional. Everything else needs its text.
  const ready = kind === 'file' ? draft.files.length > 0 : content.trim() !== '';

  function update(next: Draft) {
    setSubmitError(null);
    setDraftState({
      assignmentId,
      userId: user.id,
      draft: next,
      restored: false,
      saved: saveDraft(draftKey, next),
    });
  }

  async function handleSubmit() {
    if (submitting || !validId || !online) return;

    const value = content.trim();
    if (
      !ready ||
      isTooLong(kind, content, maxChars) ||
      ((kind === 'link' || kind === 'pr') && value.length > 2048)
    ) {
      setSubmitError('Enter valid content within the allowed length.');
      return;
    }

    setSubmitting(true);
    setSubmitError(null);

    try {
      const response = await createSubmission(
        assignmentId,
        kind,
        value,
        draft.files.map((file) => file.id),
      );

      if (!response.ok) {
        const message =
          response.status === 409
            ? 'Already submitted or deadline passed. Check My Work before retrying. Your draft is still here.'
            : response.status === 422
              ? 'Check your text or URL and try again. Your draft is still here.'
              : FAILURE_MESSAGE[classifyFailure(response)];
        setSubmitError(message);
        return;
      }

      const saved = (await response.json()) as { id?: number };

      if (
        response.status !== 201 ||
        !Number.isSafeInteger(saved.id) ||
        !saved.id ||
        saved.id <= 0
      ) {
        setSubmitError(
          'Could not confirm the submission. Check My Work before retrying. Your draft is still here.',
        );
        return;
      }

      clearDraft(draftKey);
      navigate(`/s/${saved.id}`, { replace: true });
    } catch {
      setSubmitError(
        'Could not confirm whether work was submitted. Check My Work before retrying. Your draft is still here.',
      );
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    let active = true;
    fetchLimits().then((loaded) => active && setLimits(loaded));
    return () => {
      active = false;
    };
  }, []);

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

        // SCRUM-83: open on the kind the supervisor asked for, unless a draft is already under way.
        const wanted = item?.submission_kind;
        if (wanted) {
          setDraftState((current) =>
            current.assignmentId === assignmentId && !hasContent(current.draft)
              ? { ...current, draft: { ...current.draft, kind: wanted } }
              : current,
          );
        }
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

        <h1 className="mt-5 text-page-title">
          {isResubmit(assignment) ? 'Resubmit work' : 'Submit work'}
        </h1>

        <p className="mt-2 text-body text-ink-body">{assignment.title}</p>

        {/* SCRUM-21: the reviewer's reason and scores, on this screen, above the form. */}
        {isResubmit(assignment) && assignment.submission_id !== null && (
          <ResubmitFeedback submissionId={assignment.submission_id} />
        )}

        <Card className="mt-6 !p-6">
          <h2 className="text-section">Choose how to submit</h2>

          <div className="mt-4 flex flex-wrap gap-3">
            {CHOICES.map((choice) => (
              <Button
                key={choice.kind}
                type="button"
                variant={kind === choice.kind ? 'primary' : 'secondary'}
                aria-pressed={kind === choice.kind}
                onClick={() => update({ ...draft, kind: choice.kind })}
              >
                {choice.label}
              </Button>
            ))}
          </div>

          <div className="mt-6">
            {kind === 'file' ? (
              <div className="space-y-4">
                <FileUpload
                  limits={limits}
                  files={draft.files}
                  maxFiles={MAX_FILES}
                  disabled={submitting}
                  onChange={(files) => update({ ...draft, files })}
                />
                <label htmlFor="submission-note" className="block">
                  <span className="mb-2 block text-meta font-semibold">Note (optional)</span>
                  <textarea
                    id="submission-note"
                    rows={3}
                    value={content}
                    onChange={(event) =>
                      update({ ...draft, values: { ...draft.values, file: event.target.value } })
                    }
                    placeholder="Anything your reviewer should know about these files"
                    className="w-full rounded-md border border-line bg-surface p-3 text-body text-ink"
                  />
                </label>
              </div>
            ) : kind === 'text' ? (
              <label htmlFor="submission-text" className="block">
                <span className="mb-2 block text-meta font-semibold">Your submission</span>

                <textarea
                  id="submission-text"
                  rows={8}
                  value={content}
                  onChange={(event) =>
                    update({ ...draft, values: { ...draft.values, text: event.target.value } })
                  }
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
                  onChange={(event) =>
                    update({ ...draft, values: { ...draft.values, [kind]: event.target.value } })
                  }
                  placeholder={
                    kind === 'pr'
                      ? 'https://github.com/owner/repository/pull/123'
                      : 'https://example.com/your-work'
                  }
                  className="h-btn w-full rounded-md border border-line bg-surface px-3 text-body text-ink"
                />
              </label>
            )}
            {(kind === 'text' || kind === 'file') && (
              <p className="mt-2 text-meta text-ink-meta">
                {content.length.toLocaleString()} / {maxChars.toLocaleString()} characters
              </p>
            )}
            {isTooLong(kind, content, maxChars) && (
              <p role="alert" className="mt-2 text-meta text-status-overdue-text">
                {FAILURE_MESSAGE.too_large}
              </p>
            )}
            <p role="status" className="mt-3 text-meta text-ink-meta">
              {!draftState.saved
                ? 'This browser cannot keep a draft, so keep a copy of what you type.'
                : !online
                  ? hasContent(draft)
                    ? 'You are offline. Your draft is saved on this device.'
                    : 'You are offline.'
                  : draftState.restored
                    ? 'Draft restored from this device.'
                    : hasContent(draft)
                      ? 'Draft saved on this device.'
                      : ''}
            </p>
          </div>

          <p className="mt-5 text-meta text-ink-meta">
            Your draft is kept until the server confirms submission.
          </p>

          {submitError && (
            <p role="alert" className="mt-3 text-meta text-status-overdue-text">
              {submitError}
            </p>
          )}

          <div className="mt-5">
            <Button
              type="button"
              loading={submitting}
              disabled={submitting || !online || !ready || isTooLong(kind, content, maxChars)}
              onClick={() => void handleSubmit()}
            >
              {isResubmit(assignment) ? 'Resubmit work' : 'Submit work'}
            </Button>
          </div>
        </Card>
      </div>
    </main>
  );
}
