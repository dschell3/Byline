/** @type {import('tailwindcss').Config} */

// SCRUM-70: every colour points at a CSS variable defined in src/styles/tokens.css,
// which holds the light and dark values. No hex codes live in this file.
const token = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    extend: {
      // SCRUM-81: palette is Lyric's Emerson theme (draft option A); the values live in tokens.css
      colors: {
        page: token('color-page'),
        surface: {
          DEFAULT: token('color-surface'),
          recessed: token('color-surface-recessed'),
        },
        line: {
          DEFAULT: token('color-line'),
          strong: token('color-line-strong'),
        },
        ink: {
          DEFAULT: token('color-ink'),
          body: token('color-ink-body'),
          meta: token('color-ink-meta'),
        },
        primary: {
          DEFAULT: token('color-primary'),
          hover: token('color-primary-hover'),
          on: token('color-on-primary'),
        },
        accent: {
          DEFAULT: token('color-accent'),
          deep: token('color-accent-deep'),
        },
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
          changes: {
            text: token('status-changes-text'),
            fill: token('status-changes-fill'),
            dot: token('status-changes-dot'),
          },
          overdue: { text: token('status-overdue-text'), fill: token('status-overdue-fill') },
          approved: { text: token('status-approved-text'), fill: token('status-approved-fill') },
        },
      },
      fontFamily: {
        // SCRUM-81: Emerson type. Libre Caslon Display ships in regular (400) only.
        serif: ['"Libre Caslon Display"', 'Georgia', 'serif'],
        sans: ['"DM Sans"', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'page-title': ['40px', { lineHeight: '46px', letterSpacing: '-0.02em', fontWeight: '400' }],
        section: ['20px', { lineHeight: '26px', fontWeight: '400' }],
        'card-title': ['15px', { lineHeight: '21px', fontWeight: '600' }],
        body: ['14px', { lineHeight: '21px', fontWeight: '400' }],
        meta: ['12px', { lineHeight: '18px', fontWeight: '500' }],
        // SCRUM-80: button labels from the Figma foundations/P01 buttons.
        button: ['14px', { lineHeight: '20px', fontWeight: '600' }],
        'button-sm': ['13px', { lineHeight: '20px', fontWeight: '600' }],
      },
      height: {
        btn: '44px', // full size, the phone tap target
        'btn-sm': '36px', // small variant
      },
    },
  },
  plugins: [],
};
