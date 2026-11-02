import { describe, expect, test } from 'vitest';
import { dueLabel, pointsLabel } from './work';

const NOW = new Date('2026-10-26T12:00:00Z'); // a Monday

describe('dueLabel', () => {
  test('says hours for the next day, then tomorrow and days ahead', () => {
    expect(dueLabel('2026-10-26T20:00:00Z', 'UTC', NOW)).toMatchObject({
      date: 'Mon 26 Oct',
      relative: 'in 8 hours',
    });
    expect(dueLabel('2026-10-27T20:00:00Z', 'UTC', NOW).relative).toBe('tomorrow');
    expect(dueLabel('2026-10-28T20:00:00Z', 'UTC', NOW)).toMatchObject({
      date: 'Wed 28 Oct',
      relative: 'in 2 days',
    });
  });

  test('says hours, yesterday and days ago for late work', () => {
    expect(dueLabel('2026-10-25T20:00:00Z', 'UTC', NOW).relative).toBe('16 hours ago');
    expect(dueLabel('2026-10-25T10:00:00Z', 'UTC', NOW).relative).toBe('yesterday');
    expect(dueLabel('2026-10-23T20:00:00Z', 'UTC', NOW).relative).toBe('3 days ago');
  });

  test('counts days where the person is, not in UTC', () => {
    // 23:30 UTC on the 27th is already the 28th in Lagos (UTC+1): two calendar days ahead there,
    // one in UTC.
    expect(dueLabel('2026-10-27T23:30:00Z', 'Africa/Lagos', NOW)).toMatchObject({
      date: 'Wed 28 Oct',
      relative: 'in 2 days',
    });
    expect(dueLabel('2026-10-27T23:30:00Z', 'UTC', NOW).relative).toBe('tomorrow');
  });

  test('handles work with no due date', () => {
    expect(dueLabel(null, 'UTC', NOW)).toMatchObject({ date: 'No due date', relative: '' });
  });
});

describe('pointsLabel', () => {
  test('pluralises', () => {
    expect(pointsLabel(1)).toBe('1 pt');
    expect(pointsLabel(10)).toBe('10 pts');
  });
});
