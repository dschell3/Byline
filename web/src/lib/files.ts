// SCRUM-83: upload a file straight to storage and get download links back.
//
// The API never carries the bytes. uploadFile asks it for an upload URL, PUTs
// the file there (XHR, so the progress bar is real), then tells the API the
// upload finished. Every function here takes injectable transports so the
// tests run without a browser.
import { apiFetch } from './auth';

export type Limits = {
  max_upload_mb: number;
  allowed_types: string[];
  allowed_extensions: string[];
  max_text_chars: number;
};

export type StoredFile = {
  id: number;
  name: string;
  content_type: string;
  size_bytes: number;
  status: 'pending' | 'complete';
};

export type FileProblem = 'too_large' | 'type_not_allowed' | 'empty';

export type UploadFailure =
  | { kind: 'refused'; problem: FileProblem }
  | { kind: 'signed_out' }
  | { kind: 'connection_lost' }
  | { kind: 'server' }
  | { kind: 'rejected' };

export type UploadResult = { ok: true; file: StoredFile } | { ok: false; failure: UploadFailure };

// What a user picks: the pieces of File the helpers read. Tests pass plain objects.
export type Picked = { name: string; type: string; size: number };

// Shown until /files/limits answers, and if it never does. Mirrors api/storage.py.
export const FALLBACK_LIMITS: Limits = {
  max_upload_mb: 25,
  allowed_types: [],
  allowed_extensions: [],
  max_text_chars: 20000,
};

export async function fetchLimits(fetcher: typeof apiFetch = apiFetch): Promise<Limits> {
  try {
    const response = await fetcher('/files/limits');
    if (!response.ok) return FALLBACK_LIMITS;
    const body = (await response.json()) as Partial<Limits>;
    return {
      max_upload_mb: body.max_upload_mb ?? FALLBACK_LIMITS.max_upload_mb,
      allowed_types: body.allowed_types ?? [],
      allowed_extensions: body.allowed_extensions ?? [],
      max_text_chars: body.max_text_chars ?? FALLBACK_LIMITS.max_text_chars,
    };
  } catch {
    return FALLBACK_LIMITS;
  }
}

// The limits narrowed to images, for the profile photo picker.
export function imageLimits(limits: Limits): Limits {
  const types = limits.allowed_types.filter((type) => type.startsWith('image/'));
  const extensions = new Set(['.png', '.jpg', '.jpeg', '.gif', '.webp']);
  return {
    ...limits,
    allowed_types: types,
    allowed_extensions: limits.allowed_extensions.filter((ext) => extensions.has(ext)),
  };
}

// The sentence under the picker: size, count and accepted extensions.
export function describeLimits(limits: Limits, maxFiles: number): string {
  const count = maxFiles === 1 ? 'one file' : `up to ${maxFiles} files`;
  const accepted = limits.allowed_extensions.length
    ? ` Accepted: ${limits.allowed_extensions.join(', ')}.`
    : '';
  return `Up to ${limits.max_upload_mb} MB each, ${count}.${accepted}`;
}

export function extensionOf(name: string): string {
  const dot = name.lastIndexOf('.');
  return dot < 0 ? '' : name.slice(dot).toLowerCase();
}

// The same check the API makes, so a bad pick is refused before any request leaves.
// With empty lists (limits not loaded yet) only the size is checked; the API still decides.
export function checkFile(file: Picked, limits: Limits): FileProblem | null {
  if (file.size <= 0) return 'empty';
  if (file.size > limits.max_upload_mb * 1024 * 1024) return 'too_large';
  if (limits.allowed_types.length && !limits.allowed_types.includes(file.type.toLowerCase())) {
    return 'type_not_allowed';
  }
  if (
    limits.allowed_extensions.length &&
    !limits.allowed_extensions.includes(extensionOf(file.name))
  ) {
    return 'type_not_allowed';
  }
  return null;
}

export const PROBLEM_MESSAGE: Record<FileProblem, (limits: Limits) => string> = {
  too_large: (limits) => `That file is over ${limits.max_upload_mb} MB. Choose a smaller one.`,
  type_not_allowed: (limits) =>
    limits.allowed_extensions.length
      ? `That type is not accepted. Use one of ${limits.allowed_extensions.join(', ')}.`
      : 'That type is not accepted.',
  empty: () => 'That file is empty.',
};

export const FAILURE_MESSAGE: Record<UploadFailure['kind'], string> = {
  refused: 'That file was not accepted.',
  signed_out: 'You were signed out. Sign in again and try the upload once more.',
  connection_lost: 'Connection lost during the upload. Nothing was attached. Try again.',
  server: 'Something went wrong on our side. Nothing was attached. Try again in a moment.',
  rejected: 'The upload could not be finished. Try again.',
};

export function failureMessage(failure: UploadFailure, limits: Limits): string {
  return failure.kind === 'refused'
    ? PROBLEM_MESSAGE[failure.problem](limits)
    : FAILURE_MESSAGE[failure.kind];
}

// PUT the bytes to the presigned URL, reporting 0..1 as they go. Resolves to the status
// code; rejects when the request never got an answer.
export type PutBytes = (
  url: string,
  file: Blob,
  contentType: string,
  onProgress: (fraction: number) => void,
) => Promise<number>;

export const xhrPut: PutBytes = (url, file, contentType, onProgress) =>
  new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open('PUT', url);
    request.setRequestHeader('Content-Type', contentType);
    request.upload.onprogress = (event) => {
      if (event.lengthComputable && event.total > 0) onProgress(event.loaded / event.total);
    };
    request.onload = () => resolve(request.status);
    request.onerror = () => reject(new Error('upload failed'));
    request.onabort = () => reject(new Error('upload aborted'));
    request.send(file);
  });

function classify(response: Response): UploadFailure {
  if (response.status === 413) return { kind: 'refused', problem: 'too_large' };
  if (response.status === 415) return { kind: 'refused', problem: 'type_not_allowed' };
  if (response.status === 401) return { kind: 'signed_out' };
  if (response.status >= 500) return { kind: 'server' };
  return { kind: 'rejected' };
}

export async function uploadFile(
  file: Blob & Picked,
  onProgress: (fraction: number) => void = () => {},
  transports: { fetcher?: typeof apiFetch; put?: PutBytes } = {},
): Promise<UploadResult> {
  const fetcher = transports.fetcher ?? apiFetch;
  const put = transports.put ?? xhrPut;
  const contentType = file.type || 'application/octet-stream';

  try {
    const begin = await fetcher('/files', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: file.name, content_type: contentType, size_bytes: file.size }),
    });
    if (begin.status !== 201) return { ok: false, failure: classify(begin) };
    const pending = (await begin.json()) as StoredFile & { upload_url: string };

    onProgress(0);
    const status = await put(pending.upload_url, file, contentType, onProgress);
    if (status < 200 || status >= 300) return { ok: false, failure: { kind: 'rejected' } };
    onProgress(1);

    const done = await fetcher(`/files/${pending.id}/complete`, { method: 'POST' });
    if (!done.ok) return { ok: false, failure: classify(done) };
    return { ok: true, file: (await done.json()) as StoredFile };
  } catch {
    return { ok: false, failure: { kind: 'connection_lost' } };
  }
}

// A short-lived URL for a file the viewer may open, or null when they may not.
export async function downloadUrl(
  fileId: number,
  fetcher: typeof apiFetch = apiFetch,
): Promise<string | null> {
  try {
    const response = await fetcher(`/files/${fileId}`);
    if (!response.ok) return null;
    const body = (await response.json()) as { download_url?: string };
    return typeof body.download_url === 'string' ? body.download_url : null;
  } catch {
    return null;
  }
}

export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
