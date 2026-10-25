import { describe, expect, test } from 'vitest';
import { safeNext, signInPath } from './auth';

const ORIGIN = 'https://byline-web-eh4k.onrender.com';

describe('signInPath', () => {
  test('keeps the destination, path, query and hash', () => {
    expect(signInPath('/work/42?tab=feedback#note')).toBe(
      '/signin?next=%2Fwork%2F42%3Ftab%3Dfeedback%23note',
    );
  });

  test('leaves ?next= off when the destination is home', () => {
    expect(signInPath('/')).toBe('/signin');
  });

  test('round-trips through safeNext', () => {
    const next = new URL(signInPath('/work/42?tab=feedback'), ORIGIN).searchParams.get('next');
    expect(safeNext(next, ORIGIN)).toBe('/work/42?tab=feedback');
  });
});

describe('safeNext', () => {
  test.each([
    ['/work/42', '/work/42'],
    ['/work/42?tab=feedback#note', '/work/42?tab=feedback#note'],
  ])('returns a path on this site: %s', (raw, expected) => {
    expect(safeNext(raw, ORIGIN)).toBe(expected);
  });

  test.each([
    null,
    '',
    'work/42',
    'https://evil.example/phish',
    '//evil.example/phish',
    '/\\evil.example/phish',
    '/\t/evil.example',
    'javascript:alert(1)',
    '/signin',
    '/signin?next=%2Fwork',
  ])('falls back to home for %j', (raw) => {
    expect(safeNext(raw, ORIGIN)).toBe('/');
  });
});
