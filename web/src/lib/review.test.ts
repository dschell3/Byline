import { describe, expect, test } from 'vitest';
import {
  ReviewError,
  buildReview,
  canReview,
  emptyDrafts,
  parseScore,
  reviewFailure,
  runningScores,
  scoreProblem,
} from './review';
import { reviewScoreLabel, type Criterion, type Version } from './submission';

const criteria: Criterion[] = [1, 2, 3, 4].map((n) => ({
  id: 10 + n,
  position: n,
  text: `Criterion ${n}`,
  detail: null,
  max_points: 5,
}));

function version(id: number, status: string): Version {
  return {
    id,
    version: id,
    status,
    submitted_at: '2026-11-20T10:00:00Z',
    file_keys: [],
    submission_kind: 'text',
    content: 'work',
    reviews: [],
    comments: [],
  };
}

describe('who sees the form', () => {
  const one = version(1, 'changes_requested');
  const two = version(2, 'submitted');

  test('a supervisor or admin on the latest waiting version', () => {
    expect(canReview(['supervisor'], two, [one, two])).toBe(true);
    expect(canReview(['member', 'admin'], two, [one, two])).toBe(true);
  });

  test('not a member, not an old version, not once decided', () => {
    expect(canReview(['member'], two, [one, two])).toBe(false);
    expect(canReview(['supervisor'], one, [one, two])).toBe(false);
    expect(canReview(['supervisor'], version(2, 'approved'), [one, version(2, 'approved')])).toBe(
      false,
    );
  });
});

describe('scores', () => {
  test('a whole number from 0 to the maximum', () => {
    expect(parseScore('0', 5)).toBe(0);
    expect(parseScore(' 5 ', 5)).toBe(5);
    expect(parseScore('6', 5)).toBeNull();
    expect(parseScore('-1', 5)).toBeNull();
    expect(parseScore('2.5', 5)).toBeNull();
    expect(parseScore('', 5)).toBeNull();
  });

  test('says what is wrong with a box', () => {
    expect(scoreProblem('', 5)).toBe('Give this a score.');
    expect(scoreProblem('9', 5)).toBe('A whole number from 0 to 5.');
    expect(scoreProblem('3', 5)).toBe('');
  });

  test("the running total uses Lyric's label, empty boxes count as 0", () => {
    const drafts = emptyDrafts(criteria);
    drafts[11] = { score: '5', note: '' };
    drafts[12] = { score: '3', note: '' };
    drafts[13] = { score: '4', note: '' };
    expect(reviewScoreLabel(runningScores(criteria, drafts))).toBe('Review score: 12/20');
  });
});

describe('the request', () => {
  test('is null until every criterion has a valid score', () => {
    const drafts = emptyDrafts(criteria);
    drafts[11] = { score: '5', note: '' };
    expect(buildReview('approved', criteria, drafts, '')).toBeNull();
  });

  test('carries the decision, trimmed reason and notes, blanks as null', () => {
    const drafts = Object.fromEntries(
      criteria.map((c) => [c.id, { score: '3', note: c.position === 2 ? ' Stops early ' : ' ' }]),
    );
    expect(buildReview('changes_requested', criteria, drafts, '  Finish it.  ')).toEqual({
      decision: 'changes_requested',
      reason: 'Finish it.',
      scores: [
        { criterion_id: 11, score: 3, note: null },
        { criterion_id: 12, score: 3, note: 'Stops early' },
        { criterion_id: 13, score: 3, note: null },
        { criterion_id: 14, score: 3, note: null },
      ],
    });
    expect(buildReview('approved', criteria, drafts, '   ')?.reason).toBeNull();
  });
});

describe('when the API says no', () => {
  test('shows its own words for a conflict or a bad score', () => {
    expect(reviewFailure(new ReviewError(409, 'Someone already decided.'))).toBe(
      'Someone already decided.',
    );
    expect(reviewFailure(new ReviewError(422, 'Out of 5.'))).toBe('Out of 5.');
  });

  test('a plain message for anything else', () => {
    expect(reviewFailure(new ReviewError(403, ''))).toBe('You cannot review this submission.');
    expect(reviewFailure(new Error('network'))).toBe('Your review was not saved. Try again.');
  });
});
