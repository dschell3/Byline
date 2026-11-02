import { describe, expect, test } from 'vitest';
import { dueLabel, formatInstant, isTimeZone, relativeTime, viewerTimeZone } from './time';

// One deadline and one clock, read from two places.
const DEADLINE = '2026-11-07T18:29:00Z';
const NOW = new Date('2026-11-05T18:29:00Z');

function from(now: Date, ms: number): string {
  return new Date(now.getTime() + ms).toISOString();
}
const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;

describe('one deadline, two viewers (SCRUM-15)', () => {
  test('a member in IST and a supervisor in PST read the same moment correctly', () => {
    expect(dueLabel(DEADLINE, 'Asia/Kolkata', NOW)).toMatchObject({
      date: 'Sat 7 Nov',
      time: '11:59 PM',
      relative: 'in 2 days',
    });
    // The same calendar day here, but a different time on the clock.
    expect(dueLabel(DEADLINE, 'America/Los_Angeles', NOW)).toMatchObject({
      date: 'Sat 7 Nov',
      time: '10:29 AM',
      relative: 'in 2 days',
    });
  });

  test('a deadline that crosses midnight reads as two calendar days', () => {
    const late = '2026-11-07T20:00:00Z';
    expect(dueLabel(late, 'Asia/Kolkata', NOW)).toMatchObject({
      date: 'Sun 8 Nov',
      time: '1:30 AM',
      relative: 'in 3 days',
    });
    expect(dueLabel(late, 'America/Los_Angeles', NOW)).toMatchObject({
      date: 'Sat 7 Nov',
      time: '12:00 PM',
      relative: 'in 2 days',
    });
  });

  test('the tooltip names the zone, so the time can be placed', () => {
    expect(formatInstant(DEADLINE, 'Asia/Kolkata').full).toBe(
      'Saturday 7 November 2026, 11:59 PM Asia/Kolkata (GMT+5:30)',
    );
    expect(formatInstant(DEADLINE, 'America/Los_Angeles').full).toBe(
      'Saturday 7 November 2026, 10:29 AM America/Los_Angeles (GMT-8)',
    );
  });

  test('an unknown zone falls back to UTC instead of failing', () => {
    expect(formatInstant(DEADLINE, 'Mars/Olympus_Mons')).toMatchObject({
      date: 'Sat 7 Nov',
      time: '6:29 PM',
    });
  });
});

describe('relativeTime', () => {
  test('counts minutes under an hour', () => {
    expect(relativeTime(from(NOW, 20 * MINUTE), 'UTC', NOW)).toBe('in 20 minutes');
    expect(relativeTime(from(NOW, MINUTE), 'UTC', NOW)).toBe('in 1 minute');
    expect(relativeTime(from(NOW, -45 * MINUTE), 'UTC', NOW)).toBe('45 minutes ago');
    expect(relativeTime(from(NOW, -MINUTE), 'UTC', NOW)).toBe('1 minute ago');
  });

  test('counts hours under a day', () => {
    expect(relativeTime(from(NOW, 3 * HOUR), 'UTC', NOW)).toBe('in 3 hours');
    expect(relativeTime(from(NOW, HOUR), 'UTC', NOW)).toBe('in 1 hour');
    expect(relativeTime(from(NOW, -2 * HOUR), 'UTC', NOW)).toBe('2 hours ago');
    expect(relativeTime(from(NOW, -23 * HOUR), 'UTC', NOW)).toBe('23 hours ago');
  });

  test('falls through to calendar days from a day on', () => {
    expect(relativeTime(from(NOW, 25 * HOUR), 'UTC', NOW)).toBe('tomorrow');
    expect(relativeTime(from(NOW, 49 * HOUR), 'UTC', NOW)).toBe('in 2 days');
    expect(relativeTime(from(NOW, -25 * HOUR), 'UTC', NOW)).toBe('yesterday');
    expect(relativeTime(from(NOW, -72 * HOUR), 'UTC', NOW)).toBe('3 days ago');
  });

  test('counts days where the person is, not in UTC', () => {
    // 25 hours on is 19:29 UTC on the 6th, which is already the 7th in Mumbai.
    expect(relativeTime(from(NOW, 25 * HOUR), 'Asia/Kolkata', NOW)).toBe('in 2 days');
  });
});

describe('dueLabel', () => {
  test('handles work with no due date', () => {
    expect(dueLabel(null, 'UTC', NOW)).toEqual({
      date: 'No due date',
      time: '',
      relative: '',
      full: '',
    });
  });
});

describe('isTimeZone', () => {
  test('accepts real zone names and rejects anything else', () => {
    expect(isTimeZone('Asia/Kolkata')).toBe(true);
    expect(isTimeZone('UTC')).toBe(true);
    expect(isTimeZone('Mars/Olympus_Mons')).toBe(false);
    expect(isTimeZone('')).toBe(false);
    expect(isTimeZone(null)).toBe(false);
    expect(isTimeZone(undefined)).toBe(false);
  });
});

describe('viewerTimeZone', () => {
  test('the profile zone wins, even when it says UTC', () => {
    expect(viewerTimeZone('Asia/Kolkata', () => 'America/Los_Angeles')).toBe('Asia/Kolkata');
    expect(viewerTimeZone('UTC', () => 'Asia/Kolkata')).toBe('UTC');
  });

  test('an empty or unknown profile zone falls back to the browser', () => {
    expect(viewerTimeZone('', () => 'Asia/Kolkata')).toBe('Asia/Kolkata');
    expect(viewerTimeZone(null, () => 'Asia/Kolkata')).toBe('Asia/Kolkata');
    expect(viewerTimeZone('Mars/Olympus_Mons', () => 'America/Los_Angeles')).toBe(
      'America/Los_Angeles',
    );
  });

  test('UTC when neither can be used', () => {
    expect(viewerTimeZone(null, () => null)).toBe('UTC');
    expect(viewerTimeZone('Mars/Olympus_Mons', () => 'Also/Not_A_Zone')).toBe('UTC');
  });
});
