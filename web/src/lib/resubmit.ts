// SCRUM-21: which feedback the resubmit screen (P13, resubmission variant) shows, and the
// version number the next hand-in will get. The server decides the real number; this is the label.
import type { Review, Submission, Version } from './submission';
import type { WorkItem } from './work';

// The newest version: the one the supervisor reviewed last and the one My Work links to.
export function latestVersion(submission: Submission): Version | null {
  return submission.versions.reduce<Version | null>(
    (latest, v) => (latest === null || v.version > latest.version ? v : latest),
    null,
  );
}

// Only what a person decided. AI drafts never reach the member here.
export function finalReviews(version: Version): Review[] {
  return version.reviews.filter((review) => review.is_final);
}

export function nextVersionNumber(submission: Submission): number {
  const latest = latestVersion(submission);
  return latest === null ? 1 : latest.version + 1;
}

// A row on My Work opens the resubmit variant when its latest version came back with changes.
export function isResubmit(item: Pick<WorkItem, 'submission_id' | 'status'>): boolean {
  return item.submission_id !== null && item.status === 'changes';
}
