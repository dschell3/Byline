import { describe, expect, test } from 'vitest';
import { isTimeZone, viewerTimeZone } from './timezone';

describe('isTimeZone', () => {
  test('accepts real zone names', () => {
    expect(isTimeZone('Asia/Kolkata')).toBe(true);
    expect(isTimeZone('America/Los_Angeles')).toBe(true);
    expect(isTimeZone('UTC')).toBe(true);
  });

  test('rejects anything else', () => {
    expect(isTimeZone('Mars/Olympus_Mons')).toBe(false);
    expect(isTimeZone('')).toBe(false);
    expect(isTimeZone(null)).toBe(false);
    expect(isTimeZone(undefined)).toBe(false);
  });
});

describe('viewerTimeZone', () => {
  test('uses the profile zone when it is usable', () => {
    expect(viewerTimeZone('Asia/Kolkata', () => 'America/Los_Angeles')).toBe('Asia/Kolkata');
  });

  test('a chosen UTC stays UTC, whatever the browser says', () => {
    expect(viewerTimeZone('UTC', () => 'Asia/Kolkata')).toBe('UTC');
  });

  test('falls back to the browser when the profile has no usable zone', () => {
    expect(viewerTimeZone('', () => 'Asia/Kolkata')).toBe('Asia/Kolkata');
    expect(viewerTimeZone(null, () => 'Asia/Kolkata')).toBe('Asia/Kolkata');
    expect(viewerTimeZone('Mars/Olympus_Mons', () => 'America/Los_Angeles')).toBe(
      'America/Los_Angeles',
    );
  });

  test('falls back to UTC when neither can be used', () => {
    expect(viewerTimeZone(null, () => null)).toBe('UTC');
    expect(viewerTimeZone('Mars/Olympus_Mons', () => 'Also/Not_A_Zone')).toBe('UTC');
  });
});
