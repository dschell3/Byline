import { describe, expect, test } from 'vitest';
import {
  AssignmentError,
  audienceLine,
  criterionPoints,
  fileSize,
  isNotYours,
  nextAction,
  paragraphs,
  pointsAvailable,
  yourTime,
} from './assignment';

describe('audienceLine', () => {
  test('says whether it counts, then the track and cohort it was set for', () => {
    expect(audienceLine({ is_mandatory: true, track: 'UX/UI', cohort: 'Cohort 7' })).toBe(
      'Mandatory · UX/UI · Cohort 7',
    );
  });

  test('leaves out what the assignment does not target', () => {
    expect(audienceLine({ is_mandatory: false, track: null, cohort: null })).toBe('Optional');
    expect(audienceLine({ is_mandatory: true, track: null, cohort: 'Cohort 7' })).toBe(
      'Mandatory · Cohort 7',
    );
  });
});

describe('paragraphs', () => {
  test('a blank line starts a new paragraph', () => {
    expect(paragraphs('First.\n\nSecond.\n \nThird.')).toEqual(['First.', 'Second.', 'Third.']);
  });

  test('keeps single line breaks inside a paragraph', () => {
    expect(paragraphs('One\nTwo')).toEqual(['One\nTwo']);
  });

  test('nothing written is no paragraphs', () => {
    expect(paragraphs(null)).toEqual([]);
    expect(paragraphs('  \n\n ')).toEqual([]);
  });
});

describe('points wording', () => {
  test('an assignment says what is available, not a score', () => {
    expect(pointsAvailable(20)).toBe('20 points available');
    expect(pointsAvailable(1)).toBe('1 point available');
  });

  test('a criterion says its share', () => {
    expect(criterionPoints(4)).toBe('4 points');
    expect(criterionPoints(1)).toBe('1 point');
  });
});

describe('fileSize', () => {
  test('reads as the Figma does', () => {
    expect(fileSize(24_576)).toBe('24 KB');
    expect(fileSize(1_153_434)).toBe('1.1 MB');
    expect(fileSize(512)).toBe('512 B');
  });

  test('is empty when the size is not known', () => {
    expect(fileSize(null)).toBe('');
  });
});

describe('yourTime', () => {
  const september = new Date('2026-09-25T12:00:00Z');

  test('names the place and its offset on that date', () => {
    expect(yourTime('Africa/Lagos', september)).toBe('your time, Lagos GMT+1');
    expect(yourTime('America/Los_Angeles', september)).toBe('your time, Los Angeles GMT-7');
    expect(yourTime('America/Los_Angeles', new Date('2026-12-01T12:00:00Z'))).toBe(
      'your time, Los Angeles GMT-8',
    );
  });

  test('does not say UTC twice', () => {
    expect(yourTime('UTC', september)).toBe('your time, UTC');
  });

  test('survives a zone the browser does not know', () => {
    expect(yourTime('Mars/Olympus_Mons', september)).toBe('your time, Olympus Mons');
  });
});

describe('nextAction', () => {
  test('a hand-in that exists wins: View submission, P14', () => {
    expect(nextAction({ id: 7, submission_id: 42, can_submit: true })).toEqual({
      kind: 'view',
      to: '/s/42',
    });
    expect(nextAction({ id: 7, submission_id: 42, can_submit: false })).toEqual({
      kind: 'view',
      to: '/s/42',
    });
  });

  test('nothing handed in yet: Submit, P13', () => {
    expect(nextAction({ id: 7, submission_id: null, can_submit: true })).toEqual({
      kind: 'submit',
      to: '/a/7/submit',
    });
  });

  test('nothing handed in and the late policy has closed it: no button', () => {
    expect(nextAction({ id: 7, submission_id: null, can_submit: false })).toEqual({
      kind: 'closed',
    });
  });
});

describe('isNotYours', () => {
  test('403, a missing id and a malformed id all read the same', () => {
    expect(isNotYours(new AssignmentError(403))).toBe(true);
    expect(isNotYours(new AssignmentError(404))).toBe(true);
    expect(isNotYours(new AssignmentError(422))).toBe(true);
  });

  test('a server failure is not "not yours"', () => {
    expect(isNotYours(new AssignmentError(500))).toBe(false);
    expect(isNotYours(new Error('offline'))).toBe(false);
  });
});
