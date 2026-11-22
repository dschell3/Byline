import { useState } from 'react';
import { Button } from './ui/Button';
import { Card } from './ui/Card';
import {
  buildReview,
  emptyDrafts,
  postReview,
  reviewFailure,
  runningScores,
  scoreProblem,
  type Decision,
  type ScoreDraft,
} from '../lib/review';
import { reviewScoreLabel, type Criterion, type Submission } from '../lib/submission';

// P20 (SCRUM-26): the supervisor scores every criterion, can write a reason, and approves or
// requests changes. It sits on the latest version of /s/:id while that version is waiting.
// SCRUM-27 makes the reason required when changes are requested; it is optional here.

const FIELD =
  'w-full rounded-md border bg-surface px-3 text-body text-ink focus:outline focus:outline-2 focus:outline-primary';

function CriterionRow({
  criterion,
  draft,
  showError,
  onChange,
}: {
  criterion: Criterion;
  draft: ScoreDraft;
  showError: boolean;
  onChange: (draft: ScoreDraft) => void;
}) {
  const scoreId = `criterion-${criterion.id}-score`;
  const noteId = `criterion-${criterion.id}-note`;
  const problem = showError ? scoreProblem(draft.score, criterion.max_points) : '';

  return (
    <li className="flex flex-col gap-3 border-t border-line py-4 first:border-t-0 first:pt-0 sm:flex-row sm:items-start sm:gap-6">
      <div className="flex-1">
        <label htmlFor={scoreId} className="m-0 block text-body font-semibold text-ink">
          {criterion.position}. {criterion.text}
        </label>
        {criterion.detail && (
          <p className="m-0 mt-0.5 text-meta text-ink-meta">{criterion.detail}</p>
        )}
        <label htmlFor={noteId} className="sr-only">
          Note on {criterion.text} (optional)
        </label>
        <input
          id={noteId}
          type="text"
          value={draft.note}
          maxLength={1000}
          placeholder="Note (optional)"
          onChange={(event) => onChange({ ...draft, note: event.target.value })}
          className={`mt-2 h-btn-sm border-line ${FIELD}`}
        />
      </div>
      <div className="sm:w-[132px]">
        <div className="flex items-center gap-2">
          <input
            id={scoreId}
            type="text"
            inputMode="numeric"
            autoComplete="off"
            value={draft.score}
            aria-invalid={problem ? true : undefined}
            aria-describedby={problem ? `${scoreId}-error` : undefined}
            onChange={(event) => onChange({ ...draft, score: event.target.value })}
            className={`h-btn w-[64px] text-center ${FIELD} ${
              problem ? 'border-status-overdue-text' : 'border-line'
            }`}
          />
          <span className="whitespace-nowrap text-body text-ink-meta">
            / {criterion.max_points}
          </span>
        </div>
        {problem && (
          <p id={`${scoreId}-error`} className="m-0 mt-1 text-meta text-status-overdue-text">
            {problem}
          </p>
        )}
      </div>
    </li>
  );
}

export function ReviewForm({
  versionId,
  criteria,
  onReviewed,
}: {
  versionId: number;
  criteria: Criterion[];
  onReviewed: (submission: Submission) => void;
}) {
  const [drafts, setDrafts] = useState(() => emptyDrafts(criteria));
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState<Decision | null>(null);
  const [checked, setChecked] = useState(false);
  const [error, setError] = useState('');

  async function decide(decision: Decision) {
    setChecked(true);
    const input = buildReview(decision, criteria, drafts, reason);
    if (input === null) {
      setError('Score every criterion first.');
      return;
    }
    setBusy(decision);
    setError('');
    try {
      onReviewed(await postReview(versionId, input));
    } catch (failure) {
      setError(reviewFailure(failure));
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card className="!p-5">
      <form
        aria-labelledby={`review-form-${versionId}`}
        noValidate
        onSubmit={(event) => event.preventDefault()}
      >
        <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
          <h4 id={`review-form-${versionId}`} className="m-0 text-card-title text-ink">
            Your review
          </h4>
          <p className="m-0 text-body font-semibold text-ink" aria-live="polite">
            {reviewScoreLabel(runningScores(criteria, drafts))}
          </p>
        </div>

        {criteria.length === 0 ? (
          <p className="m-0 mt-3 text-body text-ink-body">
            This assignment has no criteria to score.
          </p>
        ) : (
          <ol className="m-0 mt-4 list-none p-0">
            {criteria.map((criterion) => (
              <CriterionRow
                key={criterion.id}
                criterion={criterion}
                draft={drafts[criterion.id] ?? { score: '', note: '' }}
                showError={checked}
                onChange={(draft) =>
                  setDrafts((previous) => ({ ...previous, [criterion.id]: draft }))
                }
              />
            ))}
          </ol>
        )}

        <label
          htmlFor={`review-reason-${versionId}`}
          className="m-0 mt-5 block text-meta font-semibold text-ink"
        >
          Reason (optional)
        </label>
        <textarea
          id={`review-reason-${versionId}`}
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          rows={4}
          maxLength={4000}
          className="mt-1.5 w-full rounded-md border border-line bg-surface p-3 text-body text-ink focus:outline focus:outline-2 focus:outline-primary"
        />

        {error && (
          <p role="alert" className="m-0 mt-2 text-meta text-status-overdue-text">
            {error}
          </p>
        )}

        <div className="mt-4 flex flex-wrap gap-2">
          <Button
            type="button"
            loading={busy === 'approved'}
            disabled={busy !== null}
            onClick={() => decide('approved')}
          >
            Approve
          </Button>
          <Button
            type="button"
            variant="secondary"
            loading={busy === 'changes_requested'}
            disabled={busy !== null}
            onClick={() => decide('changes_requested')}
          >
            Request changes
          </Button>
        </div>
      </form>
    </Card>
  );
}
