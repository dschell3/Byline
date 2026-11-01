// SCRUM-15: which timezone the app shows dates in.
import { browserTimeZone } from './invite';

// True for a name this browser can use, such as "Asia/Kolkata".
export function isTimeZone(name: string | null | undefined): name is string {
  if (!name) return false;
  try {
    new Intl.DateTimeFormat('en-US', { timeZone: name });
    return true;
  } catch {
    return false;
  }
}

// The profile's zone (P18) when it is usable, else the browser's, else UTC.
export function viewerTimeZone(
  profileZone: string | null | undefined,
  browser: () => string | null = browserTimeZone,
): string {
  if (isTimeZone(profileZone)) return profileZone;
  const fromBrowser = browser();
  return isTimeZone(fromBrowser) ? fromBrowser : 'UTC';
}
