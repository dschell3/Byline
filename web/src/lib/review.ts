// SCRUM-26: the supervisor's decision on P20, "Approve" or "Request changes" with a score
// per criterion. The API checks every rule again; these are here so the form can say what
// is wrong before anything is sent.
import { apiFetch } from './auth';
import type { Criterion, Submission, Version } from './submission';

export type Decision = 'approved' | 'changes_requested';

// What the form holds for one criterion. The score is the raw text of the field, so an
// empty or half-typed box is never silently read as 0.
export type ScoreDraft = { score: string; note: string };

export type ReviewInput = {
  decision: Decision;
  reason: string | null;
  scores: { criterion_id: number; score: number; note: string | null }[];
};

export class ReviewError extends Error {
  status: number;

  detail: string;

  constructor(status: number, detail: string) {
    super(`POST /submissions/review failed with ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

// Only a supervisor or admin, and only on the latest version while it is waiting.
// Reviewing your own work is refused by the API, which is the only side that knows it.
export function canReview(roles: string[], version: Version, versions: Version[]): boolean {
  const reviewer = roles.includes('supervisor') || roles.includes('admin');
  const latest = versions[versions.length - 1];
  return reviewer && latest?.id === version.id && version.status === 'submitted';
}

export function emptyDrafts(criteria: Criterion[]): Record<number, ScoreDraft> {
  return Object.fromEntries(criteria.map((c) => [c.id, { score: '', note: '' }]));
}

// A whole number from 0 to the criterion's maximum, or null for anything else.
export function parseScore(raw: string, max: number): number | null {
  const text = raw.trim();
  if (!/^\d+$/.test(text)) return null;
  const value = Number(text);
  return value <= max ? value : null;
}

// The message under one score box, or '' when it is fine.
export function scoreProblem(raw: string, max: number): string {
  if (!raw.trim()) return 'Give this a score.';
  return parseScore(raw, max) === null ? `A whole number from 0 to ${max}.` : '';
}

// The running total for the label. Boxes that are empty or wrong count as 0.
export function runningScores(
  criteria: Criterion[],
  drafts: Record<number, ScoreDraft>,
): { score: number; max_points: number }[] {
  return criteria.map((c) => ({
    score: parseScore(drafts[c.id]?.score ?? '', c.max_points) ?? 0,
    max_points: c.max_points,
  }));
}

// The request body, or null if any score is missing or out of range.
export function buildReview(
  decision: Decision,
  criteria: Criterion[],
  drafts: Record<number, ScoreDraft>,
  reason: string,
): ReviewInput | null {
  const parsed = criteria.map((c) => {
    const draft = drafts[c.id] ?? { score: '', note: '' };
    return {
      criterion_id: c.id,
      score: parseScore(draft.score, c.max_points),
      note: draft.note.trim() || null,
    };
  });
  if (parsed.some((p) => p.score === null)) return null;
  const scores = parsed.map((p) => ({ ...p, score: p.score as number }));
  return { decision, reason: reason.trim() || null, scores };
}

// What to tell the reviewer when the API says no.
export function reviewFailure(error: unknown): string {
  if (error instanceof ReviewError) {
    if (error.status === 409 || error.status === 422) return error.detail;
    if (error.status === 403) return 'You cannot review this submission.';
  }
  return 'Your review was not saved. Try again.';
}

export async function postReview(versionId: number, input: ReviewInput): Promise<Submission> {
  const response = await apiFetch(`/submissions/${versionId}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    let detail = '';
    try {
      const body = await response.json();
      if (typeof body.detail === 'string') detail = body.detail;
    } catch {
      // No JSON body; the status alone decides the message.
    }
    throw new ReviewError(response.status, detail || 'Check the scores and try again.');
  }
  return response.json();
}
