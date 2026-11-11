import { describe, expect, test } from 'vitest';
import {
  badgeStatus,
  decisionLabel,
  fileName,
  scoreTotal,
  threads,
  versionLabel,
  type Comment,
  type Review,
} from './submission';

function comment(id: number, parent: number | null = null): Comment {
  return {
    id,
    author_membership_id: 1,
    author_name: 'Amara Okafor',
    parent_comment_id: parent,
    body: `comment ${id}`,
    created_at: '2026-11-05T10:00:00Z',
  };
}

const review: Review = {
  id: 1,
  decision: 'changes_requested',
  reason: 'Finish the phone frames.',
  is_final: true,
  actor_type: 'person',
  actor_name: 'Marguerite Ellis',
  created_at: '2026-11-04T10:00:00Z',
  scores: [
    { criterion_id: 1, position: 1, text: 'A', max_points: 5, score: 5, note: null },
    { criterion_id: 2, position: 2, text: 'B', max_points: 5, score: 2, note: 'Stops early' },
  ],
};

describe('threads', () => {
  test('groups replies under their parent, in order', () => {
    const result = threads([comment(1), comment(2, 1), comment(3), comment(4, 1)]);
    expect(result.map((t) => t.comment.id)).toEqual([1, 3]);
    expect(result[0].replies.map((r) => r.id)).toEqual([2, 4]);
    expect(result[1].replies).toEqual([]);
  });

  test('shows a reply with no parent in the list as its own thread', () => {
    const result = threads([comment(5, 99)]);
    expect(result.map((t) => t.comment.id)).toEqual([5]);
  });

  test('is empty for no comments', () => {
    expect(threads([])).toEqual([]);
  });
});

describe('wording', () => {
  test('maps a submission status onto the badge words', () => {
    expect(badgeStatus('submitted')).toBe('submitted');
    expect(badgeStatus('changes_requested')).toBe('changes');
    expect(badgeStatus('approved')).toBe('approved');
    expect(badgeStatus('anything else')).toBe('submitted');
  });

  test('says who decided what, and marks drafts', () => {
    expect(decisionLabel(review)).toBe('Changes requested by Marguerite Ellis');
    expect(decisionLabel({ ...review, is_final: false })).toBe(
      'Changes requested by Marguerite Ellis (draft)',
    );
    expect(decisionLabel({ ...review, decision: 'approved', actor_type: 'system' })).toBe(
      'Approved (AI draft)',
    );
  });

  test('counts versions and points', () => {
    expect(versionLabel(2, 2)).toBe('Version 2 of 2');
    expect(scoreTotal(review.scores)).toBe('7 / 10');
    expect(scoreTotal([])).toBe('0 / 0');
  });

  test('names a file from its object key', () => {
    expect(fileName('submissions/demo/volunteer-dashboard-v1.pdf')).toBe(
      'volunteer-dashboard-v1.pdf',
    );
    expect(fileName('plain.txt')).toBe('plain.txt');
  });
});
