/** @type {import('tailwindcss').Config} */

// SCRUM-70: every colour points at a CSS variable defined in src/styles/tokens.css,
// which holds the light and dark values. No hex codes live in this file.
const token = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    extend: {
      // Palette "Cloud & Navy", from the Figma "Byline — design foundations" page
      colors: {
        page: token('color-page'),
        surface: {
          DEFAULT: token('color-surface'),
          recessed: token('color-surface-recessed'),
        },
        line: token('color-line'),
        ink: {
          DEFAULT: token('color-ink'),
          body: token('color-ink-body'),
          meta: token('color-ink-meta'),
        },
        primary: {
          DEFAULT: token('color-primary'),
          on: token('color-on-primary'),
        },
        accent: token('color-accent'),
        // Always-navy brand panel, the same in light and dark (P01)
        navy: {
          DEFAULT: token('navy'),
          heading: token('navy-heading'),
          body: token('navy-body'),
          quote: token('navy-quote'),
          meta: token('navy-meta'),
          footer: token('navy-footer'),
          rule: token('navy-rule'),
          bar: token('navy-bar'),
          accent: token('navy-accent'),
          check: token('navy-check'),
        },
        danger: token('color-danger'),
        link: token('color-link'),
        // The six status words: text colour + fill colour
        status: {
          'due-soon': { text: token('status-due-soon-text'), fill: token('status-due-soon-fill') },
          optional: { text: token('status-optional-text'), fill: token('status-optional-fill') },
          submitted: { text: token('status-submitted-text'), fill: token('status-submitted-fill') },
          changes: { text: token('status-changes-text'), fill: token('status-changes-fill') },
          overdue: { text: token('status-overdue-text'), fill: token('status-overdue-fill') },
          approved: { text: token('status-approved-text'), fill: token('status-approved-fill') },
        },
      },
      fontFamily: {
        serif: ['"Source Serif 4"', 'Georgia', 'serif'],
        sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'page-title': ['32px', { lineHeight: '40px', fontWeight: '600' }],
        section: ['22px', { lineHeight: '28px', fontWeight: '600' }],
        'card-title': ['16px', { lineHeight: '22px', fontWeight: '600' }],
        body: ['14px', { lineHeight: '21px', fontWeight: '400' }],
        meta: ['12px', { lineHeight: '18px', fontWeight: '500' }],
      },
      height: {
        btn: '44px', // full size, the phone tap target
        'btn-sm': '36px', // small variant
      },
    },
  },
  plugins: [],
};
