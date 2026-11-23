import { describe, expect, it } from 'vitest';
import { DEFAULT_FILTERS, emptyMessage, isLate, queueQuery, waitingFor } from './reviewQueue';

const NOW = new Date('2026-11-10T12:00:00Z');
const ago = (ms: number) => new Date(NOW.getTime() - ms).toISOString();
const HOUR = 3_600_000;

describe('waitingFor', () => {
  it('counts minutes, hours, then days', () => {
    expect(waitingFor(ago(5 * 60_000), NOW)).toBe('5 minutes');
    expect(waitingFor(ago(3 * HOUR), NOW)).toBe('3 hours');
    expect(waitingFor(ago(26 * HOUR), NOW)).toBe('1 day');
    expect(waitingFor(ago(72 * HOUR), NOW)).toBe('3 days');
  });
  it('says at least one minute, and never goes negative', () => {
    expect(waitingFor(ago(5_000), NOW)).toBe('1 minute');
    expect(waitingFor(ago(-HOUR), NOW)).toBe('1 minute');
  });
});

describe('isLate', () => {
  it('is true from two days', () => {
    expect(isLate(ago(47 * HOUR), NOW)).toBe(false);
    expect(isLate(ago(48 * HOUR), NOW)).toBe(true);
  });
});

describe('queueQuery', () => {
  it('always sends the status and leaves empty filters out', () => {
    expect(queueQuery(DEFAULT_FILTERS)).toBe('status=submitted');
  });
  it('adds the chosen filters', () => {
    expect(queueQuery({ status: 'all', team: '2', cohort: '', assignment: '9' })).toBe(
      'status=all&team_id=2&assignment_id=9',
    );
  });
});

describe('emptyMessage', () => {
  it('celebrates an empty default queue', () => {
    expect(emptyMessage(DEFAULT_FILTERS).title).toBe('You have reviewed everything');
  });
  it('points back at the filters when one is set', () => {
    expect(emptyMessage({ ...DEFAULT_FILTERS, team: '2' }).title).toBe(
      'Nothing matches these filters',
    );
    expect(emptyMessage({ ...DEFAULT_FILTERS, status: 'approved' }).title).toBe(
      'Nothing matches these filters',
    );
  });
});
