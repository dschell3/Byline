// SCRUM-16: data for the first-run screen (P11) and the date wording it needs.
import { apiFetch } from './auth';

export type Home = {
  full_name: string;
  timezone: string;
  organization: { name: string };
  cohort: { name: string; starts_on: string | null; ends_on: string | null } | null;
  track: { name: string; onboarding_pack_url: string | null } | null;
  supervisor: { full_name: string; email: string } | null;
  has_work: boolean;
};

// null when the person has no organization yet (the API answers 404).
export async function fetchHome(): Promise<Home | null> {
  const response = await apiFetch('/me/home');
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`GET /me/home failed with ${response.status}`);
  return response.json();
}

export function firstName(fullName: string): string {
  return fullName.trim().split(/\s+/)[0] ?? fullName;
}

export function initials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/);
  const letters = parts.length > 1 ? [parts[0], parts[parts.length - 1]] : parts;
  return letters.map((part) => part[0]?.toUpperCase() ?? '').join('');
}

// Today's calendar date (YYYY-MM-DD) where the person is, not where the server is.
export function todayIn(timeZone: string, now: Date = new Date()): string {
  const format = (zone: string) =>
    new Intl.DateTimeFormat('en-CA', {
      timeZone: zone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).format(now);
  try {
    return format(timeZone);
  } catch {
    return format('UTC');
  }
}

const DAY_MS = 24 * 60 * 60 * 1000;

function daysBetween(from: string, to: string): number {
  return Math.round((Date.parse(`${to}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / DAY_MS);
}

// Variant A of P11 before the cohort starts, variant B once it is running.
export type CohortStage =
  { kind: 'upcoming'; daysUntil: number } | { kind: 'running'; week: number | null };

export function cohortStage(startsOn: string | null, today: string): CohortStage {
  if (!startsOn) return { kind: 'running', week: null };
  const days = daysBetween(today, startsOn);
  if (days > 0) return { kind: 'upcoming', daysUntil: days };
  return { kind: 'running', week: Math.floor(-days / 7) + 1 };
}

// Fixed names rather than Intl, whose short forms vary by browser ("Sep" vs "Sept").
const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];
const WEEKDAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

// Dates are calendar dates with no time, so read them in UTC to keep the day as stored.
function parts(isoDate: string) {
  const date = new Date(`${isoDate}T00:00:00Z`);
  return {
    day: date.getUTCDate(),
    month: MONTHS[date.getUTCMonth()],
    weekday: WEEKDAYS[date.getUTCDay()],
    year: date.getUTCFullYear(),
  };
}

// "Monday 28 September", or "Mon 28 Sep" for phones.
export function startDate(isoDate: string, short = false): string {
  const { day, month, weekday } = parts(isoDate);
  return short
    ? `${weekday.slice(0, 3)} ${day} ${month.slice(0, 3)}`
    : `${weekday} ${day} ${month}`;
}

// "28 Sep – 18 Dec 2026"
export function dateRange(startsOn: string, endsOn: string): string {
  const start = parts(startsOn);
  const end = parts(endsOn);
  return `${start.day} ${start.month.slice(0, 3)} – ${end.day} ${end.month.slice(0, 3)} ${end.year}`;
}

// "Africa/Lagos (GMT+1)"
export function timeZoneLabel(timeZone: string, now: Date = new Date()): string {
  try {
    const offset = new Intl.DateTimeFormat('en-US', { timeZone, timeZoneName: 'shortOffset' })
      .formatToParts(now)
      .find((part) => part.type === 'timeZoneName')?.value;
    return offset ? `${timeZone} (${offset})` : timeZone;
  } catch {
    return timeZone;
  }
}

export function inDays(days: number): string {
  return days === 1 ? 'tomorrow' : `in ${days} days`;
}
