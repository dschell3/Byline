// SCRUM-14: data and wording for My Work (P10).
import { apiFetch } from './auth';
import { daysBetween, inDays, startDate, todayIn } from './home';
import type { Status } from '../components/ui/Badge';

export type WorkItem = {
  id: number;
  title: string;
  set_by: string;
  due_at: string | null;
  points: number;
  status: Status;
};

export type WorkGroup = { key: Status; label: string; items: WorkItem[] };

// The API always sends all six groups, in the order the card asks for.
export async function fetchWork(): Promise<WorkGroup[]> {
  const response = await apiFetch('/me/work');
  if (!response.ok) throw new Error(`GET /me/work failed with ${response.status}`);
  const body: { groups: WorkGroup[] } = await response.json();
  return body.groups;
}

// "Tue 27 Oct" and "tomorrow", both on the calendar where the person is.
export function dueLabel(
  dueAt: string | null,
  timeZone: string,
  now: Date = new Date(),
): { date: string; relative: string } {
  if (!dueAt) return { date: 'No due date', relative: '' };
  const dueDay = todayIn(timeZone, new Date(dueAt));
  const days = daysBetween(todayIn(timeZone, now), dueDay);
  let relative: string;
  if (days === 0) relative = 'today';
  else if (days === -1) relative = 'yesterday';
  else if (days < 0) relative = `${-days} days ago`;
  else relative = inDays(days);
  return { date: startDate(dueDay, true), relative };
}

export function pointsLabel(points: number): string {
  return points === 1 ? '1 pt' : `${points} pts`;
}
