import { afterEach, describe, expect, test, vi } from 'vitest';
import { apiFetch } from './auth';
import { createSubmission } from './submitWork';

vi.mock('./auth', () => ({
  apiFetch: vi.fn(),
}));

afterEach(() => vi.clearAllMocks());

describe('createSubmission', () => {
  test.each([
    ['text', 'My finished assignment'],
    ['link', 'https://example.com/work'],
    ['pr', 'https://github.com/owner/repo/pull/12'],
  ] as const)('sends a %s submission to the correct endpoint', async (kind, content) => {
    vi.mocked(apiFetch).mockResolvedValue(new Response('{}', { status: 201 }));

    const response = await createSubmission(7, kind, content);

    expect(response.status).toBe(201);
    expect(apiFetch).toHaveBeenCalledWith('/assignments/7/submissions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kind, content }),
    });
  });

  test('a file submission carries the ids and the note (SCRUM-83)', async () => {
    vi.mocked(apiFetch).mockResolvedValue(new Response('{}', { status: 201 }));
    await createSubmission(7, 'file', 'Two drafts.', [3, 1]);
    expect(apiFetch).toHaveBeenCalledWith('/assignments/7/submissions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kind: 'file', content: 'Two drafts.', file_ids: [3, 1] }),
    });
  });

  test('returns a failed response so the page can preserve its draft', async () => {
    const failure = new Response(null, { status: 409 });
    vi.mocked(apiFetch).mockResolvedValue(failure);

    expect(await createSubmission(7, 'text', 'My work')).toBe(failure);
  });
});
