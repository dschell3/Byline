import { describe, expect, test } from 'vitest';
import {
  cohortStage,
  dateRange,
  firstName,
  inDays,
  initials,
  startDate,
  timeZoneLabel,
  todayIn,
} from './home';

describe('names', () => {
  test('first name and initials', () => {
    expect(firstName('Amara Okafor')).toBe('Amara');
    expect(initials('Marguerite Ellis')).toBe('ME');
    expect(initials('Amara Chioma Okafor')).toBe('AO');
    expect(initials('Cher')).toBe('C');
  });
});

describe('todayIn', () => {
  // 23:30 UTC on 27 Sep is already 28 Sep in Lagos (UTC+1) but still 27 Sep in Los Angeles.
  const now = new Date('2026-09-27T23:30:00Z');

  test('uses the person’s own calendar day', () => {
    expect(todayIn('Africa/Lagos', now)).toBe('2026-09-28');
    expect(todayIn('America/Los_Angeles', now)).toBe('2026-09-27');
  });

  test('falls back to UTC for an unknown zone', () => {
    expect(todayIn('Not/AZone', now)).toBe('2026-09-27');
  });
});

describe('cohortStage', () => {
  test('before the start date is variant A, with the days left', () => {
    expect(cohortStage('2026-09-28', '2026-09-21')).toEqual({ kind: 'upcoming', daysUntil: 7 });
  });

  test('the start date itself is week 1', () => {
    expect(cohortStage('2026-09-28', '2026-09-28')).toEqual({ kind: 'running', week: 1 });
  });

  test('day 8 is week 2', () => {
    expect(cohortStage('2026-09-28', '2026-10-05')).toEqual({ kind: 'running', week: 2 });
  });

  test('no start date counts as running, week unknown', () => {
    expect(cohortStage(null, '2026-10-05')).toEqual({ kind: 'running', week: null });
  });
});

describe('date wording', () => {
  test('matches the Figma copy', () => {
    expect(startDate('2026-09-28')).toBe('Monday 28 September');
    expect(startDate('2026-09-28', true)).toBe('Mon 28 Sep');
    expect(dateRange('2026-09-28', '2026-12-18')).toBe('28 Sep – 18 Dec 2026');
    expect(timeZoneLabel('Africa/Lagos', new Date('2026-09-27T12:00:00Z'))).toBe(
      'Africa/Lagos (GMT+1)',
    );
    expect(inDays(7)).toBe('in 7 days');
    expect(inDays(1)).toBe('tomorrow');
  });
});
