import { apiFetch } from './auth';

export type SubmissionKind = 'text' | 'link' | 'pr';

export async function createSubmission(
  assignmentId: number,
  kind: SubmissionKind,
  content: string,
): Promise<Response> {
  return apiFetch(`/assignments/${assignmentId}/submissions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ kind, content }),
  });
}
