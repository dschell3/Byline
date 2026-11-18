import { useEffect, useId, useRef, useState, type ChangeEvent } from 'react';
import { Button } from './ui/Button';
import { fileSize } from '../lib/assignment';
import {
  checkFile,
  describeLimits,
  failureMessage,
  PROBLEM_MESSAGE,
  uploadFile,
  type Limits,
  type StoredFile,
} from '../lib/files';

// SCRUM-83: the one file picker for P13 attachments and the P18 photo. The parent owns the
// list of completed files; a bad pick is refused before any request leaves.

type InFlight = { key: number; name: string; progress: number; error: string | null };

export type FileUploadProps = {
  limits: Limits;
  // The completed uploads attached so far. The parent owns the list.
  files: StoredFile[];
  onChange: (files: StoredFile[]) => void;
  maxFiles?: number;
  label?: string;
  disabled?: boolean;
  id?: string;
};

let nextKey = 1;

export function FileUpload({
  limits,
  files,
  onChange,
  maxFiles = 10,
  label = 'Attach files',
  disabled = false,
  id = '',
}: FileUploadProps) {
  const generatedId = useId();
  const inputId = id || generatedId;
  const hintId = `${inputId}-hint`;
  const inputRef = useRef<HTMLInputElement>(null);
  const [inFlight, setInFlight] = useState<InFlight[]>([]);
  // The parent's list may change under an upload, so the latest is read at completion time.
  const latest = useRef(files);
  useEffect(() => {
    latest.current = files;
  }, [files]);

  const room = maxFiles - files.length - inFlight.filter((f) => f.error === null).length;
  const full = room <= 0;

  function patch(key: number, change: Partial<InFlight>) {
    setInFlight((current) => current.map((f) => (f.key === key ? { ...f, ...change } : f)));
  }

  async function start(file: File) {
    const key = nextKey++;
    const problem = checkFile(file, limits);
    if (problem) {
      setInFlight((current) => [
        ...current,
        { key, name: file.name, progress: 0, error: PROBLEM_MESSAGE[problem](limits) },
      ]);
      return;
    }
    setInFlight((current) => [...current, { key, name: file.name, progress: 0, error: null }]);
    const result = await uploadFile(file, (fraction) => patch(key, { progress: fraction }));
    if (result.ok) {
      setInFlight((current) => current.filter((f) => f.key !== key));
      onChange([...latest.current, result.file]);
    } else {
      patch(key, { error: failureMessage(result.failure, limits) });
    }
  }

  function picked(event: ChangeEvent<HTMLInputElement>) {
    const chosen = Array.from(event.target.files ?? []).slice(0, Math.max(room, 0));
    event.target.value = '';
    for (const file of chosen) void start(file);
  }

  const accept = limits.allowed_extensions.join(',') || undefined;

  return (
    <div>
      <span className="mb-1.5 block text-meta font-semibold text-ink">{label}</span>
      <input
        ref={inputRef}
        id={inputId}
        type="file"
        className="sr-only"
        multiple={maxFiles > 1}
        accept={accept}
        aria-describedby={hintId}
        disabled={disabled || full}
        onChange={picked}
      />
      <div className="flex flex-wrap items-center gap-3">
        <Button
          type="button"
          variant="secondary"
          disabled={disabled || full}
          onClick={() => inputRef.current?.click()}
        >
          {maxFiles === 1 ? 'Choose file' : 'Choose files'}
        </Button>
        <p id={hintId} className="m-0 text-meta text-ink-meta">
          {full
            ? `That is the most you can attach (${maxFiles}).`
            : describeLimits(limits, maxFiles)}
        </p>
      </div>

      {(files.length > 0 || inFlight.length > 0) && (
        <ul className="m-0 mt-3 list-none space-y-2 p-0">
          {files.map((file) => (
            <li
              key={file.id}
              className="flex items-center justify-between gap-3 rounded-md border border-line bg-surface px-3 py-2"
            >
              <span className="min-w-0 truncate text-body text-ink">
                {file.name}
                <span className="ml-2 text-meta text-ink-meta">{fileSize(file.size_bytes)}</span>
              </span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                disabled={disabled}
                aria-label={`Remove ${file.name}`}
                onClick={() => onChange(files.filter((f) => f.id !== file.id))}
              >
                Remove
              </Button>
            </li>
          ))}
          {inFlight.map((upload) => (
            <li
              key={upload.key}
              className="rounded-md border border-line bg-surface px-3 py-2"
              aria-live="polite"
            >
              <div className="flex items-center justify-between gap-3">
                <span className="min-w-0 truncate text-body text-ink">{upload.name}</span>
                {upload.error ? (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    aria-label={`Dismiss ${upload.name}`}
                    onClick={() => setInFlight((c) => c.filter((f) => f.key !== upload.key))}
                  >
                    Dismiss
                  </Button>
                ) : (
                  <span className="text-meta text-ink-meta">
                    {Math.round(upload.progress * 100)}%
                  </span>
                )}
              </div>
              {upload.error ? (
                <p role="alert" className="m-0 mt-1 text-meta text-status-overdue-text">
                  {upload.error}
                </p>
              ) : (
                <div
                  role="progressbar"
                  aria-label={`Uploading ${upload.name}`}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={Math.round(upload.progress * 100)}
                  className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-surface-recessed"
                >
                  <div
                    className="h-full bg-primary transition-[width]"
                    style={{ width: `${Math.round(upload.progress * 100)}%` }}
                  />
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
