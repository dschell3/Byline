// SCRUM-85: Lyric's 11/13 readability check, kept as a test so it cannot slip back.
// Small text (under 14px) must reach 4.5:1 (WCAG AA) on every background it sits on,
// in both themes, and nothing may render smaller than 12px.
/// <reference types="node" />
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import tailwindSource from '../../tailwind.config.js?raw';

// Read from disk: Vitest turns CSS imports, ?raw included, into empty strings.
const css = readFileSync(new URL('./tokens.css', import.meta.url), 'utf8');

// Every component and page, as text, to look for one-off sizes.
const sources = import.meta.glob<string>(['../**/*.{ts,tsx}', '!../**/*.test.ts'], {
  query: '?raw',
  import: 'default',
  eager: true,
});

type Rgb = [number, number, number];

function tokens(selector: string): Record<string, Rgb> {
  const start = css.indexOf(selector);
  const block = css.slice(start, css.indexOf('\n}', start));
  const out: Record<string, Rgb> = {};
  for (const [, name, r, g, b] of block.matchAll(/--([\w-]+):\s*(\d+) (\d+) (\d+);/g)) {
    out[name] = [Number(r), Number(g), Number(b)];
  }
  return out;
}

const light = tokens(':root,');
const dark = { ...light, ...tokens("[data-theme='dark']") };

function luminance([r, g, b]: Rgb): number {
  const channel = (v: number) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

function contrast(a: Rgb, b: Rgb): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

const SURFACES = ['color-page', 'color-surface', 'color-surface-recessed'];

// Every colour used for small text, and the backgrounds it is drawn on.
const PAIRS: [string, string[]][] = [
  ['color-ink', SURFACES],
  ['color-ink-body', SURFACES],
  ['color-ink-meta', SURFACES],
  ['color-link', SURFACES],
  ['color-accent-deep', SURFACES],
  ['color-danger-text', SURFACES],
  ['status-overdue-text', SURFACES],
  ['status-due-soon-text', ['status-due-soon-fill']],
  ['status-optional-text', ['status-optional-fill']],
  ['status-submitted-text', ['status-submitted-fill']],
  ['status-changes-text', ['status-changes-fill']],
  ['status-overdue-text', ['status-overdue-fill']],
  ['status-approved-text', ['status-approved-fill']],
  ['color-on-primary', ['color-primary', 'color-primary-hover', 'color-danger']],
  ['navy-body', ['navy']],
  ['navy-meta', ['navy']],
  ['navy-footer', ['navy']],
  ['navy-accent', ['navy']],
];

describe.each([
  ['light', light],
  ['dark', dark],
])('small text contrast, %s theme', (_, theme) => {
  it.each(PAIRS.flatMap(([fg, bgs]) => bgs.map((bg) => [fg, bg])))(
    '%s on %s is at least 4.5:1',
    (fg, bg) => {
      expect(theme[fg], fg).toBeDefined();
      expect(theme[bg], bg).toBeDefined();
      expect(contrast(theme[fg], theme[bg])).toBeGreaterThanOrEqual(4.5);
    },
  );
});

describe('text size floor', () => {
  it('no type token is smaller than 12px', () => {
    const block = tailwindSource.slice(tailwindSource.indexOf('fontSize:'));
    const sizes = [...block.slice(0, block.indexOf('\n      },')).matchAll(/\['(\d+)px'/g)];
    expect(sizes.length).toBeGreaterThan(0);
    for (const [match, px] of sizes) expect(Number(px), match).toBeGreaterThanOrEqual(12);
  });

  it('no component sets a one-off size under 12px', () => {
    expect(Object.keys(sources).length).toBeGreaterThan(10);
    const tooSmall = Object.entries(sources).flatMap(([file, text]) =>
      [...text.matchAll(/text-\[(\d+(?:\.\d+)?)px\]/g)]
        .filter(([, px]) => Number(px) < 12)
        .map(([match]) => `${file}: ${match}`),
    );
    expect(tooSmall).toEqual([]);
  });
});
