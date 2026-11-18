// SCRUM-22: data and wording for the submission page (P14).
import { apiFetch } from './auth';
import type { Status } from '../components/ui/Badge';

export type Score = {
  criterion_id: number;
  position: number;
  text: string;
  max_points: number;
  score: number;
  note: string | null;
};

export type Review = {
  id: number;
  decision: 'approved' | 'changes_requested';
  reason: string | null;
  is_final: boolean;
  actor_type: 'person' | 'system';
  actor_name: string | null;
  created_at: string;
  scores: Score[];
};

export type Comment = {
  id: number;
  author_membership_id: number;
  author_name: string;
  parent_comment_id: number | null;
  body: string;
  created_at: string;
};

// SCRUM-83: a file on a version, by the id GET /files/{id} takes.
export type VersionFile = { id: number; name: string; content_type: string; size_bytes: number };

export type Version = {
  id: number;
  version: number;
  status: string;
  submitted_at: string;
  file_keys: string[];
  // The stored_file rows behind file_keys. A key from before file storage has no row.
  files: VersionFile[];
  submission_kind: 'text' | 'link' | 'pr' | 'file' | null;
  content: string | null;
  reviews: Review[];
  comments: Comment[];
};

export type Submission = {
  id: number;
  assignment: { id: number; title: string; points_value: number; due_at: string | null };
  member: { membership_id: number; full_name: string };
  versions: Version[];
};

export type Thread = { comment: Comment; replies: Comment[] };

export class SubmissionError extends Error {
  status: number;

  constructor(status: number) {
    super(`GET /submissions failed with ${status}`);
    this.status = status;
  }
}

export async function fetchSubmission(id: string): Promise<Submission> {
  const response = await apiFetch(`/submissions/${id}`);
  if (!response.ok) throw new SubmissionError(response.status);
  return response.json();
}

export async function postComment(
  versionId: number,
  body: string,
  parentId: number | null,
): Promise<Comment> {
  const response = await apiFetch(`/submissions/${versionId}/comments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ body, parent_comment_id: parentId }),
  });
  if (!response.ok) throw new SubmissionError(response.status);
  return response.json();
}

// The six status words the Badge knows; a submission's own status is one of three of them.
export function badgeStatus(status: string): Status {
  if (status === 'approved') return 'approved';
  if (status === 'changes_requested') return 'changes';
  return 'submitted';
}

export function decisionLabel(review: Review): string {
  const what = review.decision === 'approved' ? 'Approved' : 'Changes requested';
  if (review.actor_type === 'system') return `${what} (AI draft)`;
  const who = review.actor_name ?? 'A reviewer';
  return review.is_final ? `${what} by ${who}` : `${what} by ${who} (draft)`;
}

// "Version 2 of 2". Latest is the one that counts on My Work and in the queue.
export function versionLabel(version: number, total: number): string {
  return `Version ${version} of ${total}`;
}

// Top-level comments in order, each with its replies in order. A reply whose parent is
// missing (never written by the API, but cheap to survive) is shown as its own thread.
export function threads(comments: Comment[]): Thread[] {
  const byId = new Map<number, Thread>();
  const result: Thread[] = [];
  comments.forEach((comment) => {
    if (comment.parent_comment_id === null || !byId.has(comment.parent_comment_id)) {
      const thread = { comment, replies: [] };
      byId.set(comment.id, thread);
      result.push(thread);
    } else {
      byId.get(comment.parent_comment_id)!.replies.push(comment);
    }
  });
  return result;
}

// Points out of the maximum for one review, "13 / 20".
export function scoreTotal(scores: Score[]): string {
  const got = scores.reduce((sum, s) => sum + s.score, 0);
  const max = scores.reduce((sum, s) => sum + s.max_points, 0);
  return `${got} / ${max}`;
}

// The last part of an object key, which is the file's name once storage lands (SCRUM-19).
export function fileName(key: string): string {
  return key.split('/').pop() || key;
}

// What P14 lists for a version: a link for every file with a row, a bare name for the rest.
export type FileRow =
  { kind: 'link'; id: number; name: string; size_bytes: number } | { kind: 'name'; name: string };

export function fileRows(version: Pick<Version, 'file_keys' | 'files'>): FileRow[] {
  const linked: FileRow[] = version.files.map((file) => ({
    kind: 'link',
    id: file.id,
    name: file.name,
    size_bytes: file.size_bytes,
  }));
  // Keys without a row (seed data from before SCRUM-83) still show their name.
  const leftover = Math.max(version.file_keys.length - version.files.length, 0);
  const bare: FileRow[] = version.file_keys
    .slice(version.file_keys.length - leftover)
    .map((key) => ({ kind: 'name', name: fileName(key) }));
  return [...linked, ...bare];
}
