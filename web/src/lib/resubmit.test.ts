import { describe, expect, test } from 'vitest';
import { finalReviews, isResubmit, latestVersion, nextVersionNumber } from './resubmit';
import type { Review, Submission, Version } from './submission';

function review(id: number, isFinal: boolean): Review {
  return {
    id,
    decision: 'changes_requested',
    reason: `reason ${id}`,
    is_final: isFinal,
    actor_type: isFinal ? 'person' : 'system',
    actor_name: isFinal ? 'Marguerite Ellis' : null,
    created_at: '2026-11-05T10:00:00Z',
    scores: [],
  };
}

function version(id: number, number: number, reviews: Review[] = []): Version {
  return {
    id,
    version: number,
    status: 'changes_requested',
    submitted_at: '2026-11-04T10:00:00Z',
    file_keys: [],
    submission_kind: 'text',
    content: 'work',
    reviews,
    comments: [],
  };
}

function submission(versions: Version[]): Submission {
  return {
    id: versions[0]?.id ?? 1,
    assignment: { id: 1, title: 'Task', points_value: 20, due_at: null },
    member: { membership_id: 1, full_name: 'Amara Okafor' },
    versions,
  };
}

describe('latestVersion', () => {
  test('picks the highest version number, whatever the order', () => {
    const s = submission([version(12, 2), version(11, 1)]);
    expect(latestVersion(s)?.id).toBe(12);
  });

  test('is null when there are no versions', () => {
    expect(latestVersion(submission([]))).toBeNull();
  });
});

describe('finalReviews', () => {
  test('keeps only final reviews, in order', () => {
    const v = version(1, 1, [review(1, false), review(2, true), review(3, true)]);
    expect(finalReviews(v).map((r) => r.id)).toEqual([2, 3]);
  });
});

describe('nextVersionNumber', () => {
  test('is one more than the latest', () => {
    expect(nextVersionNumber(submission([version(11, 1), version(12, 2)]))).toBe(3);
  });

  test('is 1 before the first hand-in', () => {
    expect(nextVersionNumber(submission([]))).toBe(1);
  });
});

describe('isResubmit', () => {
  test('only when there is a submission and changes were requested', () => {
    expect(isResubmit({ submission_id: 5, status: 'changes' })).toBe(true);
    expect(isResubmit({ submission_id: 5, status: 'submitted' })).toBe(false);
    expect(isResubmit({ submission_id: null, status: 'changes' })).toBe(false);
  });
});
