// SCRUM-14: data and wording for My Work (P10).
import { apiFetch } from './auth';
import type { LatePolicy } from './latePolicy';
import type { Status } from '../components/ui/Badge';

export type WorkItem = {
  id: number;
  title: string;
  set_by: string;
  due_at: string | null;
  points: number;
  status: Status;
  // SCRUM-23: describeLatePolicy() in latePolicy.ts turns these into words.
  late_policy: LatePolicy;
  late_cutoff_hours: number | null;
};

export type WorkGroup = { key: Status; label: string; items: WorkItem[] };

// The API always sends all six groups, in the order the card asks for.
export async function fetchWork(): Promise<WorkGroup[]> {
  const response = await apiFetch('/me/work');
  if (!response.ok) throw new Error(`GET /me/work failed with ${response.status}`);
  const body: { groups: WorkGroup[] } = await response.json();
  return body.groups;
}

// dueLabel lives in time.ts now (SCRUM-15); re-exported so My Work and its tests are unaffected.
export { dueLabel } from './time';

export function pointsLabel(points: number): string {
  return points === 1 ? '1 pt' : `${points} pts`;
}
