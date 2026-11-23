import { describe, expect, test } from 'vitest';

// SCRUM-84: wording Lyric asked us to drop in her 11/13 review. These checks read the page
// source, so the words cannot quietly come back on sign-in, invite and join, or first-run home.
const pageSourceByPath = import.meta.glob<string>('./*Page.tsx', {
  query: '?raw',
  import: 'default',
  eager: true,
});

function pageSource(fileName: string): string {
  const source = pageSourceByPath[`./${fileName}`];
  if (source === undefined) throw new Error(`No page called ${fileName}`);
  return source;
}

const DROPPED_PHRASES = ['twelve weeks', 'permanently', 'yours to keep'];
const PAGES_LYRIC_REVIEWED = ['SignInPage.tsx', 'InvitePage.tsx', 'HomePage.tsx'];

describe("Lyric's 11/13 wording", () => {
  test.each(PAGES_LYRIC_REVIEWED)('%s does not use any of the dropped phrases', (fileName) => {
    const source = pageSource(fileName).toLowerCase();
    for (const phrase of DROPPED_PHRASES) {
      expect(source, `"${phrase}" is back in ${fileName}`).not.toContain(phrase);
    }
  });

  test.each(['SignInPage.tsx', 'InvitePage.tsx'])(
    '%s shows no quote in the brand panel',
    (fileName) => {
      expect(pageSource(fileName)).not.toMatch(/\bquote=/);
    },
  );
});
