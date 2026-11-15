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

const typed: Draft = { kind: 'link', values: { text: 'my notes', link: 'https://x.test', pr: '' } };

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
    ).toEqual({ kind: 'text', values: { text: '', link: '', pr: 'p' } });
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

  test('hasContent ignores whitespace', () => {
    expect(hasContent(emptyDraft())).toBe(false);
    expect(hasContent({ ...emptyDraft(), values: { text: '  ', link: '', pr: '' } })).toBe(false);
    expect(hasContent(typed)).toBe(true);
  });
});
