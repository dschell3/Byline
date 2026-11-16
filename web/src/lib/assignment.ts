// SCRUM-18: data and wording for the assignment page (P12).
import { apiFetch } from './auth';
import type { AssignmentLateRules } from './latePolicy';
import type { Status } from '../components/ui/Badge';

export type Criterion = {
  id: number;
  position: number;
  text: string;
  detail: string | null;
  max_points: number;
};

export type ReferenceLink = { label: string; url: string };

export type Attachment = { name: string; size_bytes: number | null };

// due_at, late_policy and late_cutoff_hours are the fields describeLatePolicy() needs (SCRUM-23).
export type Assignment = AssignmentLateRules & {
  id: number;
  title: string;
  description: string | null;
  set_by: string;
  set_at: string;
  points: number;
  is_mandatory: boolean;
  status: Status;
  track: string | null;
  cohort: string | null;
  criteria: Criterion[];
  reference_links: ReferenceLink[];
  attachments: Attachment[];
  // The member's latest submission, once there is one.
  submission_id: number | null;
  // False once the late policy has stopped taking hand-ins.
  can_submit: boolean;
};

export class AssignmentError extends Error {
  status: number;

  constructor(status: number) {
    super(`GET /assignments failed with ${status}`);
    this.status = status;
  }
}

export async function fetchAssignment(id: string): Promise<Assignment> {
  const response = await apiFetch(`/assignments/${encodeURIComponent(id)}`);
  if (!response.ok) throw new AssignmentError(response.status);
  return response.json();
}

// The API answers 403 for an assignment that was not set for this person and for an id that
// does not exist, and 422 for an id that is not a number. All three read as "not yours".
export function isNotYours(error: unknown): boolean {
  return error instanceof AssignmentError && [403, 404, 422].includes(error.status);
}

// "Mandatory · UX/UI · Cohort 7": whether it counts, then who it was set for.
export function audienceLine(
  assignment: Pick<Assignment, 'is_mandatory' | 'track' | 'cohort'>,
): string {
  const parts = [assignment.is_mandatory ? 'Mandatory' : 'Optional'];
  if (assignment.track) parts.push(assignment.track);
  if (assignment.cohort) parts.push(assignment.cohort);
  return parts.join(' · ');
}

// The description is plain text. A blank line starts a new paragraph; single line breaks are
// kept inside one by the page (whitespace-pre-line).
export function paragraphs(description: string | null): string[] {
  if (!description) return [];
  return description
    .split(/\n\s*\n/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);
}

// "20 points available", the client's wording for what an assignment is worth (11/13 review).
// It is what can be earned, not a score: review scores and awarded points are shown elsewhere.
export function pointsAvailable(points: number): string {
  return points === 1 ? '1 point available' : `${points} points available`;
}

// One criterion's share, "4 points".
export function criterionPoints(points: number): string {
  return points === 1 ? '1 point' : `${points} points`;
}

// "24 KB", "1.1 MB". Empty when the size is not known.
export function fileSize(bytes: number | null): string {
  if (bytes === null || bytes < 0) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// "your time, Lagos GMT+1": tells the intern the due time is already in their own zone.
export function yourTime(timeZone: string, at: Date = new Date()): string {
  const place = timeZone.split('/').pop()!.replace(/_/g, ' ');
  // UTC has no place name to pair with an offset; "UTC GMT+0" would say the same thing twice.
  if (place === 'UTC' || place === 'GMT') return `your time, ${place}`;
  try {
    const offset = new Intl.DateTimeFormat('en-US', { timeZone, timeZoneName: 'shortOffset' })
      .formatToParts(at)
      .find((part) => part.type === 'timeZoneName')?.value;
    if (!offset) return `your time, ${place}`;
    return `your time, ${place} ${offset}`;
  } catch {
    return `your time, ${place}`;
  }
}

// What the page offers: the hand-in that already exists (P14), a new one (P13), or neither
// once the late policy has stopped taking work.
export type Action =
  { kind: 'view'; to: string } | { kind: 'submit'; to: string } | { kind: 'closed' };

export function nextAction(
  assignment: Pick<Assignment, 'id' | 'submission_id' | 'can_submit'>,
): Action {
  if (assignment.submission_id !== null) {
    return { kind: 'view', to: `/s/${assignment.submission_id}` };
  }
  if (assignment.can_submit) return { kind: 'submit', to: `/a/${assignment.id}/submit` };
  return { kind: 'closed' };
}
