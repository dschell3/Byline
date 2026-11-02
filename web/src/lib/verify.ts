// SCRUM-12: the browser side of an email verification link (P04).
import type { Problem } from '../components/ProblemNotice';

export type VerifyState = 'verified' | 'expired' | 'already_verified';

export type Verification = {
  state: VerifyState;
  email: string;
  // When the address was confirmed (ISO). Null only when the link has expired.
  verified_at: string | null;
};

// Uses the link. null when the API has never heard of the token (404).
// A POST, so a mail scanner that prefetches the page cannot use the link up.
export async function verifyEmail(token: string): Promise<Verification | null> {
  const response = await fetch(`/api/verify/${encodeURIComponent(token)}`, {
    method: 'POST',
    credentials: 'same-origin',
  });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`POST /verify failed with ${response.status}`);
  return response.json();
}

// Sends a new link after an expired one. Resolves to the status code.
export async function resendVerification(token: string): Promise<number> {
  const response = await fetch(`/api/verify/${encodeURIComponent(token)}/resend`, {
    method: 'POST',
    credentials: 'same-origin',
  });
  return response.status;
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

// "14 Sep" for the already-verified screen, in the reader's own timezone. The month names are
// ours because Intl's short months differ by platform ("Sep" on one, "Sept" on another).
export function confirmedOn(iso: string, timeZone?: string): string {
  const parts = new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'numeric',
    timeZone,
  }).formatToParts(new Date(iso));
  const day = parts.find((part) => part.type === 'day')?.value ?? '';
  const month = Number(parts.find((part) => part.type === 'month')?.value);
  return `${day} ${MONTHS[month - 1]}`;
}

// Matches VERIFICATION_LIFETIME in api/verifications.py and the SCRUM-12 card.
export const LINK_LIFETIME = '24 hours';

export const UNREACHABLE: Problem = {
  title: 'Byline could not be reached',
  detail: 'Check your connection and try again.',
};

// What to tell the person when "Send a new link" fails.
export function resendProblem(status: number): Problem {
  if (status === 409) {
    return {
      title: 'This link no longer needs a new one',
      detail: 'Reload the page to see where things stand.',
    };
  }
  return {
    title: 'The new link could not be sent',
    detail: 'Try again in a moment.',
  };
}
