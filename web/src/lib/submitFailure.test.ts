import { describe, expect, test } from 'vitest';
import { classifyFailure, FAILURE_MESSAGE, isTooLong, MAX_TEXT_CHARS } from './submitFailure';

describe('classifyFailure', () => {
  test('a request that never arrived is a lost connection', () => {
    expect(classifyFailure(new TypeError('Failed to fetch'))).toBe('connection_lost');
    expect(classifyFailure(new DOMException('aborted', 'AbortError'))).toBe('connection_lost');
  });

  test('a reply says what went wrong', () => {
    expect(classifyFailure(new Response(null, { status: 413 }))).toBe('too_large');
    expect(classifyFailure(new Response(null, { status: 401 }))).toBe('signed_out');
    expect(classifyFailure(new Response(null, { status: 503 }))).toBe('server');
    expect(classifyFailure(new Response(null, { status: 422 }))).toBe('rejected');
  });

  test('too large and connection lost read differently, and both say the text is kept', () => {
    expect(FAILURE_MESSAGE.too_large).not.toBe(FAILURE_MESSAGE.connection_lost);
    for (const message of Object.values(FAILURE_MESSAGE)) {
      expect(message).toMatch(/still here|saved on this device|draft will be here/);
    }
  });
});

describe('isTooLong', () => {
  test('only typed text has a length limit', () => {
    expect(isTooLong('text', 'a'.repeat(MAX_TEXT_CHARS))).toBe(false);
    expect(isTooLong('text', 'a'.repeat(MAX_TEXT_CHARS + 1))).toBe(true);
    expect(isTooLong('link', 'a'.repeat(MAX_TEXT_CHARS + 1))).toBe(false);
  });
});
