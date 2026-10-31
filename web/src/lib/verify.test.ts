import { describe, expect, test } from 'vitest';
import { confirmedOn, resendProblem } from './verify';

describe('confirmedOn', () => {
  test('shows the day and short month', () => {
    expect(confirmedOn('2026-09-14T10:00:00Z', 'UTC')).toBe('14 Sep');
  });

  test('uses the reader’s timezone, so a late-night confirmation can fall on the next day', () => {
    expect(confirmedOn('2026-09-14T23:30:00Z', 'UTC')).toBe('14 Sep');
    expect(confirmedOn('2026-09-14T23:30:00Z', 'Africa/Lagos')).toBe('15 Sep');
  });
});

describe('resendProblem', () => {
  test('a link that is no longer expired asks for a reload', () => {
    expect(resendProblem(409).detail).toMatch(/reload/i);
  });

  test('anything else is a retry', () => {
    expect(resendProblem(500).title).toMatch(/could not be sent/i);
  });
});
