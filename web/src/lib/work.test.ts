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

describe('one deadline, read by people in different timezones (SCRUM-15)', () => {
  // 03:00 UTC on Fri 30 Oct is 08:30 that day in Mumbai and 20:00 on Thu 29 Oct in Los Angeles.
  const DEADLINE = '2026-10-30T03:00:00Z';

  test('a member in IST and a supervisor in PST read the same instant on their own calendars', () => {
    // 10:00 UTC on Thu 29 Oct: 15:30 that day in Mumbai, 03:00 that day in Los Angeles.
    const now = new Date('2026-10-29T10:00:00Z');
    expect(dueLabel(DEADLINE, 'Asia/Kolkata', now)).toEqual({
      date: 'Fri 30 Oct',
      relative: 'tomorrow',
    });
    expect(dueLabel(DEADLINE, 'America/Los_Angeles', now)).toEqual({
      date: 'Thu 29 Oct',
      relative: 'today',
    });
  });

  test('the same deadline can be late on one calendar and still today on another', () => {
    // 12:00 UTC on Fri 30 Oct is 17:30 that day in Mumbai and 05:00 that day in Los Angeles.
    const noon = '2026-10-30T12:00:00Z';
    // 20:00 UTC on Fri 30 Oct: already 01:30 on Sat 31 Oct in Mumbai, 13:00 on Fri in Los Angeles.
    const now = new Date('2026-10-30T20:00:00Z');
    expect(dueLabel(noon, 'Asia/Kolkata', now)).toEqual({
      date: 'Fri 30 Oct',
      relative: 'yesterday',
    });
    expect(dueLabel(noon, 'America/Los_Angeles', now)).toEqual({
      date: 'Fri 30 Oct',
      relative: 'today',
    });
  });

  test('the same person changing zone sees the same instant on a different calendar', () => {
    const now = new Date('2026-10-29T10:00:00Z');
    expect(dueLabel(DEADLINE, 'Asia/Kolkata', now).date).toBe('Fri 30 Oct');
    expect(dueLabel(DEADLINE, 'Pacific/Pago_Pago', now).date).toBe('Thu 29 Oct');
  });
});
