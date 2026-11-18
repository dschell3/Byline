import { describe, expect, test, vi } from 'vitest';
import {
  FALLBACK_LIMITS,
  checkFile,
  downloadUrl,
  extensionOf,
  failureMessage,
  fetchLimits,
  formatSize,
  uploadFile,
  type Limits,
  type PutBytes,
} from './files';

const LIMITS: Limits = {
  max_upload_mb: 25,
  allowed_types: ['application/pdf', 'image/png'],
  allowed_extensions: ['.pdf', '.png'],
  max_text_chars: 20000,
};

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

const picked = (name: string, type: string, size: number) =>
  new File(['x'.repeat(Math.max(size, 0))], name, { type });

describe('fetchLimits', () => {
  test('reads the four limits', async () => {
    const fetcher = vi.fn().mockResolvedValue(json(LIMITS));
    expect(await fetchLimits(fetcher)).toEqual(LIMITS);
    expect(fetcher).toHaveBeenCalledWith('/files/limits');
  });

  test('falls back when the API is unreachable or answers badly', async () => {
    expect(await fetchLimits(vi.fn().mockRejectedValue(new Error('down')))).toEqual(
      FALLBACK_LIMITS,
    );
    expect(await fetchLimits(vi.fn().mockResolvedValue(new Response('', { status: 500 })))).toEqual(
      FALLBACK_LIMITS,
    );
  });
});

describe('checkFile', () => {
  test.each([
    ['notes.pdf', 'application/pdf', 1024, null],
    ['Photo.PNG', 'image/png', 1024, null],
    ['big.pdf', 'application/pdf', 25 * 1024 * 1024 + 1, 'too_large'],
    ['empty.pdf', 'application/pdf', 0, 'empty'],
    ['run.exe', 'application/x-msdownload', 10, 'type_not_allowed'],
    ['run.exe', 'application/pdf', 10, 'type_not_allowed'],
  ] as const)('%s (%s, %d bytes) → %s', (name, type, size, expected) => {
    expect(checkFile({ name, type, size }, LIMITS)).toBe(expected);
  });

  test('with the fallback limits only the size is checked', () => {
    expect(checkFile({ name: 'run.exe', type: 'x/y', size: 10 }, FALLBACK_LIMITS)).toBeNull();
    expect(
      checkFile(
        { name: 'a.pdf', type: 'application/pdf', size: 26 * 1024 * 1024 },
        FALLBACK_LIMITS,
      ),
    ).toBe('too_large');
  });

  test('extensionOf keeps only the last dotted part, lower-cased', () => {
    expect(extensionOf('My.Report.PDF')).toBe('.pdf');
    expect(extensionOf('noext')).toBe('');
  });
});

describe('uploadFile', () => {
  const pendingBody = {
    id: 42,
    name: 'notes.pdf',
    content_type: 'application/pdf',
    size_bytes: 3,
    status: 'pending',
    upload_url: '/api/files/local/org-1/abc.pdf',
  };
  const completeBody = { ...pendingBody, status: 'complete', upload_url: undefined };

  test('begins, PUTs with progress, completes', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(json(pendingBody, 201))
      .mockResolvedValueOnce(json(completeBody));
    const put: PutBytes = vi.fn(async (url, _file, contentType, onProgress) => {
      expect(url).toBe('/api/files/local/org-1/abc.pdf');
      expect(contentType).toBe('application/pdf');
      onProgress(0.5);
      return 204;
    });
    const seen: number[] = [];

    const result = await uploadFile(
      picked('notes.pdf', 'application/pdf', 3),
      (f) => seen.push(f),
      {
        fetcher,
        put,
      },
    );

    expect(result).toEqual({
      ok: true,
      file: expect.objectContaining({ id: 42, status: 'complete' }),
    });
    expect(seen).toEqual([0, 0.5, 1]);
    expect(fetcher).toHaveBeenNthCalledWith(1, '/files', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'notes.pdf', content_type: 'application/pdf', size_bytes: 3 }),
    });
    expect(fetcher).toHaveBeenNthCalledWith(2, '/files/42/complete', { method: 'POST' });
  });

  test.each([
    [413, { kind: 'refused', problem: 'too_large' }],
    [415, { kind: 'refused', problem: 'type_not_allowed' }],
    [401, { kind: 'signed_out' }],
    [500, { kind: 'server' }],
    [403, { kind: 'rejected' }],
  ] as const)('a %d from POST /files is reported without a PUT', async (status, failure) => {
    const fetcher = vi.fn().mockResolvedValue(new Response('', { status }));
    const put = vi.fn();
    const result = await uploadFile(picked('a.pdf', 'application/pdf', 3), undefined, {
      fetcher,
      put,
    });
    expect(result).toEqual({ ok: false, failure });
    expect(put).not.toHaveBeenCalled();
  });

  test('a PUT the bucket refuses is rejected and never completed', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(json(pendingBody, 201));
    const put: PutBytes = vi.fn(async () => 403);
    const result = await uploadFile(picked('a.pdf', 'application/pdf', 3), undefined, {
      fetcher,
      put,
    });
    expect(result).toEqual({ ok: false, failure: { kind: 'rejected' } });
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  test('a dropped connection anywhere is connection_lost', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(json(pendingBody, 201));
    const put: PutBytes = vi.fn(async () => {
      throw new Error('network');
    });
    const result = await uploadFile(picked('a.pdf', 'application/pdf', 3), undefined, {
      fetcher,
      put,
    });
    expect(result).toEqual({ ok: false, failure: { kind: 'connection_lost' } });
  });

  test('a 409 from complete is rejected so the page offers a retry', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(json(pendingBody, 201))
      .mockResolvedValueOnce(new Response('', { status: 409 }));
    const put: PutBytes = vi.fn(async () => 204);
    const result = await uploadFile(picked('a.pdf', 'application/pdf', 3), undefined, {
      fetcher,
      put,
    });
    expect(result).toEqual({ ok: false, failure: { kind: 'rejected' } });
  });

  test('a file with no type is sent as octet-stream and the API decides', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response('', { status: 415 }));
    await uploadFile(picked('notes', '', 3), undefined, { fetcher, put: vi.fn() });
    expect(JSON.parse(vi.mocked(fetcher).mock.calls[0][1].body as string).content_type).toBe(
      'application/octet-stream',
    );
  });
});

describe('failureMessage', () => {
  test('says the limit for a refused file and a plain sentence otherwise', () => {
    expect(failureMessage({ kind: 'refused', problem: 'too_large' }, LIMITS)).toContain('25 MB');
    expect(failureMessage({ kind: 'refused', problem: 'type_not_allowed' }, LIMITS)).toContain(
      '.pdf, .png',
    );
    expect(failureMessage({ kind: 'connection_lost' }, LIMITS)).toContain('Nothing was attached');
  });
});

describe('downloadUrl', () => {
  test('returns the URL, or null when the viewer may not open it', async () => {
    expect(
      await downloadUrl(
        42,
        vi.fn().mockResolvedValue(json({ download_url: '/api/files/local/k' })),
      ),
    ).toBe('/api/files/local/k');
    expect(
      await downloadUrl(42, vi.fn().mockResolvedValue(new Response('', { status: 403 }))),
    ).toBeNull();
    expect(await downloadUrl(42, vi.fn().mockRejectedValue(new Error('down')))).toBeNull();
  });
});

describe('formatSize', () => {
  test.each([
    [512, '512 B'],
    [2048, '2 KB'],
    [3.5 * 1024 * 1024, '3.5 MB'],
  ])('%d → %s', (bytes, text) => {
    expect(formatSize(bytes)).toBe(text);
  });
});
