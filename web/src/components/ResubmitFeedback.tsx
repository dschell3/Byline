import { useEffect, useState } from 'react';
import { ReviewCard } from './ReviewCard';
import { fetchHome } from '../lib/home';
import { viewerTimeZone } from '../lib/time';
import { finalReviews, latestVersion, nextVersionNumber } from '../lib/resubmit';
import { fetchSubmission, versionLabel, type Review } from '../lib/submission';

// SCRUM-21: the reviewer's reason and scores on the last version, shown above the resubmit
// form on P13 so the member never has to leave the page to see what to fix.

type State =
  | { submissionId: number; status: 'ready'; reviews: Review[]; next: number }
  | { submissionId: number; status: 'error' };

export function ResubmitFeedback({ submissionId }: { submissionId: number }) {
  const [state, setState] = useState<State | null>(null);
  // The profile's zone first, then the browser's (SCRUM-15), like P14.
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
    fetchSubmission(String(submissionId))
      .then((submission) => {
        if (!current) return;
        const latest = latestVersion(submission);
        setState({
          submissionId,
          status: 'ready',
          reviews: latest ? finalReviews(latest) : [],
          next: nextVersionNumber(submission),
        });
      })
      .catch(() => current && setState({ submissionId, status: 'error' }));
    return () => {
      current = false;
    };
  }, [submissionId]);

  if (!state || state.submissionId !== submissionId) {
    return (
      <p className="m-0 mt-6 text-meta text-ink-meta">Loading your reviewer&apos;s feedback…</p>
    );
  }

  if (state.status === 'error') {
    return (
      <p role="alert" className="m-0 mt-6 text-body text-ink">
        Your reviewer&apos;s feedback could not be loaded. Reload the page to try again.
      </p>
    );
  }

  return (
    <section aria-labelledby="resubmit-feedback-title" className="mt-6 flex flex-col gap-4">
      <div>
        <h2 id="resubmit-feedback-title" className="text-section">
          What your reviewer asked for
        </h2>
        <p className="m-0 mt-1 text-meta text-ink-meta">
          Resubmitting · this will be {versionLabel(state.next, state.next)}
        </p>
      </div>
      {state.reviews.length === 0 ? (
        <p className="m-0 text-body text-ink-body">
          There is no written feedback on your last version.
        </p>
      ) : (
        state.reviews.map((review) => (
          <ReviewCard key={review.id} review={review} timeZone={timeZone} />
        ))
      )}
    </section>
  );
}
