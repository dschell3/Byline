// SCRUM-11: the browser side of an invite link (P05).
import type { Problem } from '../components/ProblemNotice';

export type InviteState = 'open' | 'expired' | 'used' | 'revoked';

export type Invite = {
  state: InviteState;
  email: string;
  role: string;
  expires_at: string;
  organization: { name: string };
  cohort: { name: string; starts_on: string | null; ends_on: string | null } | null;
  track: { name: string; onboarding_pack_url: string | null } | null;
  invited_by: { full_name: string; email: string };
};

// null when the API has never heard of the token (404).
export async function fetchInvite(token: string): Promise<Invite | null> {
  const response = await fetch(`/api/invites/${encodeURIComponent(token)}`);
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`GET /invites failed with ${response.status}`);
  return response.json();
}

export type AcceptBody = { full_name: string; password: string; timezone: string | null };

// One action: creates the account and the membership and signs the browser in (cookie).
export function acceptInvite(token: string, body: AcceptBody): Promise<Response> {
  return fetch(`/api/invites/${encodeURIComponent(token)}/accept`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

// The zone the browser reports, or null when it cannot say. The API stores UTC for null.
export function browserTimeZone(
  resolve: () => string | undefined = () => Intl.DateTimeFormat().resolvedOptions().timeZone,
): string | null {
  try {
    return resolve() || null;
  } catch {
    return null;
  }
}

const DAY_MS = 24 * 60 * 60 * 1000;

// "12 weeks" for the cohort chip; null when either date is missing or the order is wrong.
export function cohortWeeks(startsOn: string | null, endsOn: string | null): number | null {
  if (!startsOn || !endsOn) return null;
  const days = (Date.parse(`${endsOn}T00:00:00Z`) - Date.parse(`${startsOn}T00:00:00Z`)) / DAY_MS;
  if (!Number.isFinite(days) || days <= 0) return null;
  return Math.round(days / 7);
}

// "figma.com" for a pack link, so the row can say where it goes.
export function linkHost(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return 'link';
  }
}

export const MIN_PASSWORD_LENGTH = 10;

const PROBLEMS: Record<number, Problem> = {
  409: {
    title: 'You already have a Byline account',
    detail: 'This email is already signed up. Sign in instead of joining again.',
  },
  410: {
    title: 'This invite can no longer be used',
    detail: 'Reload the page to see why, and who to ask for a new one.',
  },
  422: {
    title: 'Check your name and password',
    detail: `Your password needs at least ${MIN_PASSWORD_LENGTH} characters.`,
  },
};

export const UNREACHABLE: Problem = {
  title: 'Byline could not be reached',
  detail: 'Check your connection and try again.',
};

// What to tell the person when the accept call fails.
export function acceptProblem(status: number): Problem {
  return (
    PROBLEMS[status] ?? {
      title: 'Something went wrong',
      detail: 'Try again in a moment. If it keeps happening, ask the person who invited you.',
    }
  );
}
