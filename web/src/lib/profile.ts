// SCRUM-17: data and wording for the profile page (P18).
import type { Problem } from '../components/ProblemNotice';
import { apiFetch } from './auth';

export type ContactPreference = 'email' | 'discord' | 'phone';

export type Profile = {
  full_name: string;
  email: string;
  photo_url: string | null;
  timezone: string;
  contact_preference: ContactPreference;
  contact_detail: string | null;
  email_assignments: boolean;
  email_reminders: boolean;
  email_digest: boolean;
  public_byline_consent: boolean;
  public_byline_consent_at: string | null;
};

// The fields the person can change. Email is read-only here; the consent stamp is the API's.
export type ProfilePatch = Partial<Omit<Profile, 'email' | 'public_byline_consent_at'>>;

// What the form holds while it is being edited: text fields are always strings.
export type ProfileForm = {
  full_name: string;
  photo_url: string;
  timezone: string;
  contact_preference: ContactPreference;
  contact_detail: string;
  email_assignments: boolean;
  email_reminders: boolean;
  email_digest: boolean;
  public_byline_consent: boolean;
};

// null when the person has no organization yet (the API answers 404).
export async function fetchProfile(): Promise<Profile | null> {
  const response = await apiFetch('/me/profile');
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`GET /me/profile failed with ${response.status}`);
  return response.json();
}

export type SaveResult =
  { ok: true; profile: Profile } | { ok: false; status: number; fields: string[] };

// Which fields the API refused: the second part of each error's location, e.g. body.timezone.
export function invalidFields(body: unknown): string[] {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (!Array.isArray(detail)) return [];
  return detail
    .map((item: { loc?: unknown[] } | null) => item?.loc?.[1])
    .filter((name): name is string => typeof name === 'string');
}

// Sends only what changed. The API answers with the whole profile as it now stands.
export async function saveProfile(patch: ProfilePatch): Promise<SaveResult> {
  const response = await apiFetch('/me/profile', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  });
  if (response.ok) return { ok: true, profile: await response.json() };
  const body = await response.json().catch(() => null);
  return { ok: false, status: response.status, fields: invalidFields(body) };
}

export function toForm(profile: Profile): ProfileForm {
  return {
    full_name: profile.full_name,
    photo_url: profile.photo_url ?? '',
    timezone: profile.timezone,
    contact_preference: profile.contact_preference,
    contact_detail: profile.contact_detail ?? '',
    email_assignments: profile.email_assignments,
    email_reminders: profile.email_reminders,
    email_digest: profile.email_digest,
    public_byline_consent: profile.public_byline_consent,
  };
}

const FLAGS = [
  'email_assignments',
  'email_reminders',
  'email_digest',
  'public_byline_consent',
] as const;

// The difference between what is saved and what the form now says. Empty means nothing to send.
// Blank text becomes null so a cleared photo or detail is cleared on the server too.
export function buildPatch(saved: Profile, form: ProfileForm): ProfilePatch {
  const patch: ProfilePatch = {};
  const name = form.full_name.trim();
  if (name !== saved.full_name) patch.full_name = name;
  const photo = form.photo_url.trim() || null;
  if (photo !== saved.photo_url) patch.photo_url = photo;
  const zone = form.timezone.trim();
  if (zone !== saved.timezone) patch.timezone = zone;
  if (form.contact_preference !== saved.contact_preference) {
    patch.contact_preference = form.contact_preference;
  }
  const detail = form.contact_detail.trim() || null;
  if (detail !== saved.contact_detail) patch.contact_detail = detail;
  FLAGS.forEach((flag) => {
    if (form[flag] !== saved[flag]) patch[flag] = form[flag];
  });
  return patch;
}

// A stored UTC is the API's fallback for "the browser could not say", so offer the zone the
// browser reports instead. Anything else the person has chosen stays as it is.
export function startingTimeZone(saved: string, browser: string | null): string {
  return saved === 'UTC' && browser && browser !== 'UTC' ? browser : saved;
}

// Used when the browser has no Intl.supportedValuesOf, so the list is never empty.
export const FALLBACK_ZONES = [
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'America/Sao_Paulo',
  'Europe/London',
  'Europe/Paris',
  'Africa/Lagos',
  'Asia/Dubai',
  'Asia/Kolkata',
  'Asia/Tokyo',
  'Australia/Sydney',
];

function browserZones(): string[] {
  return Intl.supportedValuesOf('timeZone');
}

// Every zone the browser knows, sorted, for the picker's list. Browsers leave UTC out of that
// list, but it is a valid choice and where many accounts start, so it is always added.
export function timeZoneOptions(list: () => string[] = browserZones): string[] {
  let zones: string[] = [];
  try {
    zones = list();
  } catch {
    // Older browsers have no Intl.supportedValuesOf; the short list above is used instead.
  }
  const names = zones.length > 0 ? zones : FALLBACK_ZONES;
  return Array.from(new Set([...names, 'UTC'])).sort();
}

// What each refused field is told. The API names the field; the wording is ours.
export const FIELD_ERRORS: Record<string, string> = {
  full_name: 'Enter a name of 1 to 200 characters.',
  photo_url: 'Use a link that starts with https://.',
  timezone: 'Choose a timezone from the list.',
  contact_preference: 'Choose email, Discord or phone.',
  contact_detail: 'Keep this to 200 characters or fewer.',
};

// What to tell the person when saving fails.
export function profileProblem(status: number): Problem {
  if (status === 422) {
    return {
      title: 'Check the highlighted fields',
      detail: 'Something you entered is not valid. Fix the fields marked in red, then save again.',
    };
  }
  return {
    title: 'Your changes were not saved',
    detail: 'Try again in a moment. If it keeps happening, ask your supervisor.',
  };
}
