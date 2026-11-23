// SCRUM-20: typed work survives a refresh, a crash or a dropped connection.
// Drafts live in this browser only, one per assignment, and are cleared once a submit succeeds.

import type { StoredFile } from './files';

export type SubmissionKind = 'text' | 'link' | 'pr' | 'file';

// values.file is the note that goes with attached files; the files are already in storage.
export type Draft = {
  kind: SubmissionKind;
  values: Record<SubmissionKind, string>;
  files: StoredFile[];
};

type Store = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>;

const PREFIX = 'byline:draft:';
const KINDS: SubmissionKind[] = ['text', 'link', 'pr', 'file'];

export function emptyDraft(): Draft {
  return { kind: 'text', values: { text: '', link: '', pr: '', file: '' }, files: [] };
}

export function hasContent(draft: Draft): boolean {
  return draft.files.length > 0 || KINDS.some((kind) => draft.values[kind].trim() !== '');
}

function isStoredFile(value: unknown): value is StoredFile {
  if (!value || typeof value !== 'object') return false;
  const file = value as Partial<StoredFile>;
  return (
    typeof file.id === 'number' &&
    typeof file.name === 'string' &&
    typeof file.content_type === 'string' &&
    typeof file.size_bytes === 'number' &&
    file.status === 'complete'
  );
}

// Private windows and blocked site data can make storage missing or throw, so every use is guarded.
function defaultStore(): Store | null {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}

export function loadDraft(
  assignmentId: number | string,
  store: Store | null = defaultStore(),
): Draft {
  try {
    const raw = store?.getItem(PREFIX + assignmentId);
    if (!raw) return emptyDraft();
    const data = JSON.parse(raw) as Partial<Draft> | null;
    const draft = emptyDraft();
    if (data && typeof data === 'object') {
      if (data.kind && KINDS.includes(data.kind)) draft.kind = data.kind;
      for (const kind of KINDS) {
        const value = data.values?.[kind];
        if (typeof value === 'string') draft.values[kind] = value;
      }
      if (Array.isArray(data.files)) draft.files = data.files.filter(isStoredFile);
    }
    return draft;
  } catch {
    return emptyDraft();
  }
}

// true when the draft is kept (or there is nothing to keep), false when this browser would not store it.
export function saveDraft(
  assignmentId: number | string,
  draft: Draft,
  store: Store | null = defaultStore(),
): boolean {
  if (!store) return false;
  try {
    if (hasContent(draft)) store.setItem(PREFIX + assignmentId, JSON.stringify(draft));
    else store.removeItem(PREFIX + assignmentId);
    return true;
  } catch {
    return false;
  }
}

export function clearDraft(
  assignmentId: number | string,
  store: Store | null = defaultStore(),
): void {
  try {
    store?.removeItem(PREFIX + assignmentId);
  } catch {
    // nothing to clear
  }
}
