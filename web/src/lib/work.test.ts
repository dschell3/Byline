import { describe, expect, test } from 'vitest';
import { dueLabel, pointsLabel } from './work';

const NOW = new Date('2026-10-26T12:00:00Z'); // a Monday

describe('dueLabel', () => {
  test('says today, tomorrow and days ahead', () => {
    expect(dueLabel('2026-10-26T20:00:00Z', 'UTC', NOW)).toEqual({
      date: 'Mon 26 Oct',
      relative: 'today',
    });
    expect(dueLabel('2026-10-27T20:00:00Z', 'UTC', NOW).relative).toBe('tomorrow');
    expect(dueLabel('2026-10-28T20:00:00Z', 'UTC', NOW)).toEqual({
      date: 'Wed 28 Oct',
      relative: 'in 2 days',
    });
  });

  test('says yesterday and days ago for late work', () => {
    expect(dueLabel('2026-10-25T20:00:00Z', 'UTC', NOW).relative).toBe('yesterday');
    expect(dueLabel('2026-10-23T20:00:00Z', 'UTC', NOW).relative).toBe('3 days ago');
  });

  test('counts days where the person is, not in UTC', () => {
    // 23:30 UTC on the 26th is already the 27th in Lagos (UTC+1) -- but "now" is the 26th there too.
    expect(dueLabel('2026-10-26T23:30:00Z', 'Africa/Lagos', NOW)).toEqual({
      date: 'Tue 27 Oct',
      relative: 'tomorrow',
    });
  });

  test('handles work with no due date', () => {
    expect(dueLabel(null, 'UTC', NOW)).toEqual({ date: 'No due date', relative: '' });
  });
});

describe('pointsLabel', () => {
  test('pluralises', () => {
    expect(pointsLabel(1)).toBe('1 pt');
    expect(pointsLabel(10)).toBe('10 pts');
  });
});
