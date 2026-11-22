// SCRUM-24: data and wording for the review queue (P19).
import { apiFetch } from './auth';

export type QueueRow = {
  submission_id: number;
  intern_name: string;
  assignment_id: number;
  assignment_title: string;
  team_id: number | null;
  team_name: string | null;
  cohort_id: number | null;
  cohort_name: string | null;
  track_name: string | null;
  submitted_at: string;
  status: string;
};

export type Option = { id: number; name: string };

export type Queue = {
  rows: QueueRow[];
  filters: { teams: Option[]; cohorts: Option[]; assignments: Option[] };
};

// 'submitted' is "waiting for review", the default view.
export type StatusFilter = 'submitted' | 'changes_requested' | 'approved' | 'all';

export type Filters = {
  status: StatusFilter;
  team: string;
  cohort: string;
  assignment: string;
};

export const DEFAULT_FILTERS: Filters = {
  status: 'submitted',
  team: '',
  cohort: '',
  assignment: '',
};

export const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: 'submitted', label: 'Waiting for review' },
  { value: 'changes_requested', label: 'Changes requested' },
  { value: 'approved', label: 'Approved' },
  { value: 'all', label: 'All' },
];

export class QueueError extends Error {
  status: number;
  constructor(status: number) {
    super(`GET /review/queue failed with ${status}`);
    this.status = status;
  }
}

// The query string for a set of filters. Empty ones are left out.
export function queueQuery(filters: Filters): string {
  const params = new URLSearchParams();
  params.set('status', filters.status);
  if (filters.team) params.set('team_id', filters.team);
  if (filters.cohort) params.set('cohort_id', filters.cohort);
  if (filters.assignment) params.set('assignment_id', filters.assignment);
  return params.toString();
}

export async function fetchQueue(filters: Filters): Promise<Queue> {
  const response = await apiFetch(`/review/queue?${queueQuery(filters)}`);
  if (!response.ok) throw new QueueError(response.status);
  return response.json();
}

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

// How long something has waited: "12 minutes", "5 hours", "3 days". Never negative.
export function waitingFor(iso: string, now: Date = new Date()): string {
  const ms = Math.max(0, now.getTime() - new Date(iso).getTime());
  const count = (n: number, unit: string) => `${n} ${unit}${n === 1 ? '' : 's'}`;
  if (ms < HOUR) return count(Math.max(1, Math.floor(ms / MINUTE)), 'minute');
  if (ms < DAY) return count(Math.floor(ms / HOUR), 'hour');
  return count(Math.floor(ms / DAY), 'day');
}

// Waiting two days or more: the row says so in more than colour.
export function isLate(iso: string, now: Date = new Date()): boolean {
  return now.getTime() - new Date(iso).getTime() >= 2 * DAY;
}

// What the empty queue says. Waiting with nothing in it is good news; a filter that
// matches nothing is not, so it points back to the filters instead.
export function emptyMessage(filters: Filters): { title: string; detail: string } {
  const narrowed = filters.team || filters.cohort || filters.assignment;
  if (narrowed || filters.status !== 'submitted') {
    return {
      title: 'Nothing matches these filters',
      detail: 'Try clearing a filter to see more of the queue.',
    };
  }
  return {
    title: 'You have reviewed everything',
    detail:
      'Every submission from your team has an answer. New work shows up here the moment it is handed in.',
  };
}
