import { describe, expect, test } from 'vitest';
import { clearDraft, emptyDraft, hasContent, loadDraft, saveDraft, type Draft } from './draft';

function fakeStore(initial: Record<string, string> = {}) {
  const data = new Map(Object.entries(initial));
  return {
    data,
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => void data.set(key, value),
    removeItem: (key: string) => void data.delete(key),
  };
}

const typed: Draft = {
  kind: 'link',
  values: { text: 'my notes', link: 'https://x.test', pr: '', file: '' },
  files: [],
};
const attached = {
  id: 42,
  name: 'brief.pdf',
  content_type: 'application/pdf',
  size_bytes: 10,
  status: 'complete' as const,
};

describe('drafts', () => {
  test('what was typed comes back after a refresh, for the same assignment only', () => {
    const store = fakeStore();
    expect(saveDraft(7, typed, store)).toBe(true);
    expect(loadDraft(7, store)).toEqual(typed);
    expect(loadDraft(8, store)).toEqual(emptyDraft());
  });

  test('keeps the text of every kind, so switching kinds loses nothing', () => {
    const store = fakeStore();
    saveDraft(7, typed, store);
    expect(loadDraft(7, store).values.text).toBe('my notes');
  });

  test('an empty draft removes the saved copy', () => {
    const store = fakeStore();
    saveDraft(7, typed, store);
    saveDraft(7, emptyDraft(), store);
    expect(store.data.size).toBe(0);
  });

  test('clearDraft forgets it after a successful submit', () => {
    const store = fakeStore();
    saveDraft(7, typed, store);
    clearDraft(7, store);
    expect(loadDraft(7, store)).toEqual(emptyDraft());
  });

  test('damaged or odd saved data gives an empty draft, not a crash', () => {
    expect(loadDraft(7, fakeStore({ 'byline:draft:7': '{not json' }))).toEqual(emptyDraft());
    expect(loadDraft(7, fakeStore({ 'byline:draft:7': 'null' }))).toEqual(emptyDraft());
    expect(
      loadDraft(7, fakeStore({ 'byline:draft:7': '{"kind":"zip","values":{"text":5,"pr":"p"}}' })),
    ).toEqual({ kind: 'text', values: { text: '', link: '', pr: 'p', file: '' }, files: [] });
  });

  test('missing or throwing storage reports false and never throws', () => {
    expect(saveDraft(7, typed, null)).toBe(false);
    expect(loadDraft(7, null)).toEqual(emptyDraft());
    const broken = {
      getItem: () => {
        throw new Error('blocked');
      },
      setItem: () => {
        throw new Error('full');
      },
      removeItem: () => {
        throw new Error('blocked');
      },
    };
    expect(saveDraft(7, typed, broken)).toBe(false);
    expect(loadDraft(7, broken)).toEqual(emptyDraft());
    expect(() => clearDraft(7, broken)).not.toThrow();
  });

  test('drafts are isolated between signed-in accounts', () => {
    const store = fakeStore();
    saveDraft('1:7', typed, store);
    expect(loadDraft('1:7', store)).toEqual(typed);
    expect(loadDraft('2:7', store)).toEqual(emptyDraft());
    clearDraft('1:7', store);
    expect(loadDraft('1:7', store)).toEqual(emptyDraft());
  });

  test('hasContent ignores whitespace', () => {
    expect(hasContent(emptyDraft())).toBe(false);
    expect(
      hasContent({ ...emptyDraft(), values: { text: '  ', link: '', pr: '', file: '' } }),
    ).toBe(false);
  });

  test('attached files count as content and come back, damaged entries dropped (SCRUM-83)', () => {
    const store = fakeStore();
    const withFile: Draft = { ...emptyDraft(), kind: 'file', files: [attached] };
    expect(hasContent(withFile)).toBe(true);
    saveDraft(7, withFile, store);
    expect(loadDraft(7, store)).toEqual(withFile);
    const damaged = fakeStore({
      'byline:draft:7': JSON.stringify({
        kind: 'file',
        files: [attached, { id: 'x' }, { ...attached, id: 43, status: 'pending' }, null],
      }),
    });
    expect(loadDraft(7, damaged).files).toEqual([attached]);
    expect(hasContent(typed)).toBe(true);
  });
});
