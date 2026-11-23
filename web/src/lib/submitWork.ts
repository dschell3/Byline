import { apiFetch } from './auth';

export type SubmissionKind = 'text' | 'link' | 'pr' | 'file';

// For kind "file", content is the optional note and fileIds the completed uploads (SCRUM-83).
export async function createSubmission(
  assignmentId: number,
  kind: SubmissionKind,
  content: string,
  fileIds: number[] = [],
): Promise<Response> {
  return apiFetch(`/assignments/${assignmentId}/submissions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(
      kind === 'file' ? { kind, content, file_ids: fileIds } : { kind, content },
    ),
  });
}
