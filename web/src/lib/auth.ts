// SCRUM-13: the browser side of sessions.
// The session itself is an HTTP-only cookie the API sets, so nothing here can read or store it.
// Every call goes to /api on our own origin (Vite proxies it locally, Render rewrites it in
// staging), which is what lets a SameSite cookie travel with it.

export type CurrentUser = {
  id: number;
  full_name: string;
  roles: string[];
};

const SIGN_IN = '/signin';

// Where to send someone to sign in, remembering where they were going.
export function signInPath(destination: string): string {
  return destination === '/' ? SIGN_IN : `${SIGN_IN}?next=${encodeURIComponent(destination)}`;
}

// The page to land on after signing in. Only a path on this site is allowed, so a crafted
// link like /signin?next=https://evil.example cannot bounce someone off Byline.
export function safeNext(raw: string | null, origin: string): string {
  if (!raw || !raw.startsWith('/')) return '/';
  let url: URL;
  try {
    url = new URL(raw, origin);
  } catch {
    return '/';
  }
  if (url.origin !== origin || url.pathname === SIGN_IN) return '/';
  return `${url.pathname}${url.search}${url.hash}`;
}

// fetch for the API. A 401 means the session ended mid-use: go to sign-in and come back here.
export async function apiFetch(
  path: string,
  init: Parameters<typeof fetch>[1] = {},
): Promise<Response> {
  const response = await fetch(`/api${path}`, { credentials: 'same-origin', ...init });
  if (response.status === 401) {
    const { pathname, search, hash } = window.location;
    window.location.assign(signInPath(`${pathname}${search}${hash}`));
  }
  return response;
}

// Who is signed in, or null when nobody is. Does not redirect; RequireAuth decides that.
export async function fetchCurrentUser(): Promise<CurrentUser | null> {
  const response = await fetch('/api/auth/me', { credentials: 'same-origin' });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error(`GET /auth/me failed with ${response.status}`);
  return response.json();
}

export function signIn(email: string, password: string): Promise<Response> {
  return fetch('/api/auth/sign-in', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
}

export async function signOut(): Promise<void> {
  await fetch('/api/auth/sign-out', { method: 'POST', credentials: 'same-origin' });
}
