import { describe, expect, test } from 'vitest';
import {
  MIN_PASSWORD_LENGTH,
  acceptProblem,
  browserTimeZone,
  cohortWeeks,
  linkHost,
} from './invite';

describe('cohortWeeks', () => {
  test('rounds the span to whole weeks', () => {
    expect(cohortWeeks('2026-09-28', '2026-12-18')).toBe(12);
    expect(cohortWeeks('2026-09-28', '2026-10-05')).toBe(1);
  });

  test('is null without both dates or when the end comes first', () => {
    expect(cohortWeeks(null, '2026-12-18')).toBeNull();
    expect(cohortWeeks('2026-09-28', null)).toBeNull();
    expect(cohortWeeks('2026-12-18', '2026-09-28')).toBeNull();
  });
});

describe('browserTimeZone', () => {
  test('passes the browser’s zone through', () => {
    expect(browserTimeZone(() => 'Africa/Lagos')).toBe('Africa/Lagos');
  });

  test('is null when the browser cannot say or throws', () => {
    expect(browserTimeZone(() => undefined)).toBeNull();
    expect(browserTimeZone(() => '')).toBeNull();
    expect(
      browserTimeZone(() => {
        throw new RangeError('no zone');
      }),
    ).toBeNull();
  });
});

describe('linkHost', () => {
  test('shows where a pack link goes', () => {
    expect(linkHost('https://www.figma.com/file/abc')).toBe('figma.com');
    expect(linkHost('https://drive.google.com/x')).toBe('drive.google.com');
    expect(linkHost('not a url')).toBe('link');
  });
});

describe('acceptProblem', () => {
  test('each refusal gets its own wording', () => {
    expect(acceptProblem(409).title).toMatch(/already have/i);
    expect(acceptProblem(410).title).toMatch(/no longer/i);
    expect(acceptProblem(422).detail).toContain(String(MIN_PASSWORD_LENGTH));
  });

  test('anything else is a generic retry', () => {
    expect(acceptProblem(500).title).toBe('Something went wrong');
  });
});
