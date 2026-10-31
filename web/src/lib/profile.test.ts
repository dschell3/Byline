import { describe, expect, test } from 'vitest';
import {
  FALLBACK_ZONES,
  buildPatch,
  invalidFields,
  profileProblem,
  startingTimeZone,
  timeZoneOptions,
  toForm,
  type Profile,
} from './profile';

const SAVED: Profile = {
  full_name: 'Amara Okafor',
  email: 'amara@example.com',
  photo_url: null,
  timezone: 'Africa/Lagos',
  contact_preference: 'email',
  contact_detail: null,
  email_assignments: true,
  email_reminders: true,
  email_digest: true,
  public_byline_consent: false,
  public_byline_consent_at: null,
};

describe('timeZoneOptions', () => {
  test('uses the browser’s list, sorted, with UTC added', () => {
    expect(timeZoneOptions(() => ['Europe/Paris', 'Africa/Lagos'])).toEqual([
      'Africa/Lagos',
      'Europe/Paris',
      'UTC',
    ]);
  });

  test('does not repeat UTC when the browser already lists it', () => {
    expect(timeZoneOptions(() => ['UTC', 'Asia/Tokyo'])).toEqual(['Asia/Tokyo', 'UTC']);
  });

  test('falls back to a short list when the browser has no Intl.supportedValuesOf', () => {
    const options = timeZoneOptions(() => {
      throw new TypeError('Intl.supportedValuesOf is not a function');
    });
    expect(options.length).toBeGreaterThanOrEqual(12);
    expect(options).toEqual(expect.arrayContaining(FALLBACK_ZONES));
    expect(options).toContain('UTC');
    expect(options).toEqual([...options].sort());
  });

  test('falls back too when the browser’s list is empty', () => {
    expect(timeZoneOptions(() => [])).toContain('Africa/Lagos');
  });

  test('this browser’s own list works', () => {
    const options = timeZoneOptions();
    expect(options).toContain('UTC');
    expect(options).toContain('Africa/Lagos');
  });
});

describe('profileProblem', () => {
  test('a refused field points at the highlighted fields', () => {
    expect(profileProblem(422).title).toBe('Check the highlighted fields');
  });

  test('anything else is a generic retry', () => {
    expect(profileProblem(500).title).toBe('Your changes were not saved');
    expect(profileProblem(404).title).toBe('Your changes were not saved');
  });
});

describe('invalidFields', () => {
  test('names the fields the API refused', () => {
    const body = {
      detail: [
        { loc: ['body', 'timezone'], msg: 'Value error, Unknown timezone.' },
        { loc: ['body', 'photo_url'], msg: 'Value error' },
      ],
    };
    expect(invalidFields(body)).toEqual(['timezone', 'photo_url']);
  });

  test('is empty when the body is not the usual list', () => {
    expect(invalidFields(null)).toEqual([]);
    expect(invalidFields({ detail: 'nope' })).toEqual([]);
    expect(invalidFields({ detail: [{ loc: ['body'] }] })).toEqual([]);
  });
});

describe('buildPatch', () => {
  test('nothing changed means nothing to send', () => {
    expect(buildPatch(SAVED, toForm(SAVED))).toEqual({});
  });

  test('sends only what changed, with text trimmed', () => {
    const form = { ...toForm(SAVED), full_name: '  Amara N. Okafor ', timezone: 'Asia/Tokyo' };
    expect(buildPatch(SAVED, form)).toEqual({
      full_name: 'Amara N. Okafor',
      timezone: 'Asia/Tokyo',
    });
  });

  test('blank photo and detail clear to null', () => {
    const saved = { ...SAVED, photo_url: 'https://example.com/a.png', contact_detail: 'amara_o' };
    const form = { ...toForm(saved), photo_url: '  ', contact_detail: '' };
    expect(buildPatch(saved, form)).toEqual({ photo_url: null, contact_detail: null });
  });

  test('carries the switches and the contact choice', () => {
    const form = {
      ...toForm(SAVED),
      contact_preference: 'discord' as const,
      email_digest: false,
      public_byline_consent: true,
    };
    expect(buildPatch(SAVED, form)).toEqual({
      contact_preference: 'discord',
      email_digest: false,
      public_byline_consent: true,
    });
  });
});

describe('toForm', () => {
  test('missing text shows as an empty field', () => {
    const form = toForm(SAVED);
    expect(form.photo_url).toBe('');
    expect(form.contact_detail).toBe('');
  });
});

describe('startingTimeZone', () => {
  test('a stored UTC gives way to the browser’s zone', () => {
    expect(startingTimeZone('UTC', 'Africa/Lagos')).toBe('Africa/Lagos');
  });

  test('a zone the person has chosen is kept', () => {
    expect(startingTimeZone('Asia/Tokyo', 'Africa/Lagos')).toBe('Asia/Tokyo');
  });

  test('UTC stays when the browser cannot say or also says UTC', () => {
    expect(startingTimeZone('UTC', null)).toBe('UTC');
    expect(startingTimeZone('UTC', 'UTC')).toBe('UTC');
  });
});
