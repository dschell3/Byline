// SCRUM-15: everything that turns an instant into words for the person looking at it.
// Calendar-only dates (a cohort's start and end) are not instants and stay in home.ts.
import { daysBetween, inDays, startDate, timeZoneLabel, todayIn } from './home';
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

// The profile's zone (P18) when it is usable, else the browser's, else UTC. A profile that
// says UTC wins: the person may really be there, and the profile page offers the browser's
// zone when the saved value is UTC.
export function viewerTimeZone(
  profileZone: string | null | undefined,
  browser: () => string | null = browserTimeZone,
): string {
  if (isTimeZone(profileZone)) return profileZone;
  const fromBrowser = browser();
  return isTimeZone(fromBrowser) ? fromBrowser : 'UTC';
}

// "11:59 PM". The locale and options are fixed so the text does not vary by browser, and the
// narrow no-break space newer browsers put before PM becomes an ordinary space.
function clock(instant: Date, timeZone: string): string {
  const format = (zone: string) =>
    new Intl.DateTimeFormat('en-US', { timeZone: zone, hour: 'numeric', minute: '2-digit' })
      .format(instant)
      .replace(/[\u202f\u00a0]/g, ' ');
  try {
    return format(timeZone);
  } catch {
    return format('UTC');
  }
}

// One instant as the viewer reads it: "Sat 7 Nov", "11:59 PM", and the long form for a tooltip,
// "Saturday 7 November 2026, 11:59 PM Asia/Kolkata (GMT+5:30)".
export function formatInstant(
  iso: string,
  timeZone: string,
): { date: string; time: string; full: string } {
  const instant = new Date(iso);
  const day = todayIn(timeZone, instant);
  const time = clock(instant, timeZone);
  return {
    date: startDate(day, true),
    time,
    full: `${startDate(day)} ${day.slice(0, 4)}, ${time} ${timeZoneLabel(timeZone, instant)}`,
  };
}

const MINUTE_MS = 60 * 1000;
const HOUR_MS = 60 * MINUTE_MS;

function plural(count: number, unit: string): string {
  return `${count} ${unit}${count === 1 ? '' : 's'}`;
}

// "in 20 minutes", "3 hours ago", "tomorrow", "3 days ago", read against the viewer's own clock.
// Under a day it counts minutes and hours; beyond that it counts calendar days where they are.
export function relativeTime(iso: string, timeZone: string, now: Date = new Date()): string {
  const due = new Date(iso);
  const diff = due.getTime() - now.getTime();
  const away = Math.abs(diff);
  const later = diff >= 0;
  if (away < HOUR_MS) {
    const text = plural(Math.max(1, Math.floor(away / MINUTE_MS)), 'minute');
    return later ? `in ${text}` : `${text} ago`;
  }
  if (away < 24 * HOUR_MS) {
    const text = plural(Math.floor(away / HOUR_MS), 'hour');
    return later ? `in ${text}` : `${text} ago`;
  }
  const days = daysBetween(todayIn(timeZone, now), todayIn(timeZone, due));
  if (days === 0) return 'today';
  if (days === -1) return 'yesterday';
  if (days < 0) return `${-days} days ago`;
  return inDays(days);
}

// What a My Work row says about a deadline.
export function dueLabel(
  dueAt: string | null,
  timeZone: string,
  now: Date = new Date(),
): { date: string; time: string; relative: string; full: string } {
  if (!dueAt) return { date: 'No due date', time: '', relative: '', full: '' };
  return { ...formatInstant(dueAt, timeZone), relative: relativeTime(dueAt, timeZone, now) };
}
