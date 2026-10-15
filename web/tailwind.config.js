/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      // SCRUM-70: tokens from the Figma "Byline — design foundations" page
      // Palette "Cloud & Navy"
      colors: {
        page: "#EEF2F7",              // page background, the cloud ground
        surface: {
          DEFAULT: "#FFFFFF",         // cards, headers, rows
          recessed: "#F7F9FC",        // table heads, zebra rows
        },
        line: "#D6DEE8",              // 1px hairline borders
        ink: {
          DEFAULT: "#0F1D33",         // text strong: titles, names
          body: "#3A4A61",            // sentences
          meta: "#55698A",            // dates, counts, labels
        },
        primary: "#1B3A6B",           // one primary action per screen
        accent: {
          DEFAULT: "#5A4BD1",         // logo and marketing only, never a status
          "on-navy": "#8C82E4",       // flourish on dark navy
        },
        // The six status words: text colour + fill colour
        status: {
          "due-soon": { text: "#14427F", fill: "#E0EAFA" },
          optional: { text: "#42536E", fill: "#E6EBF2" },
          submitted: { text: "#0E5F5F", fill: "#D8EDED" },
          changes: { text: "#8A4F00", fill: "#FAE7CC" },
          overdue: { text: "#A3201A", fill: "#FADFDD" },
          approved: { text: "#15602F", fill: "#D9EDE0" },
        },
      },
      fontFamily: {
        serif: ['"Source Serif 4"', "Georgia", "serif"],
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
      },
      fontSize: {
        "page-title": ["32px", { lineHeight: "40px", fontWeight: "600" }],
        section: ["22px", { lineHeight: "28px", fontWeight: "600" }],
        "card-title": ["16px", { lineHeight: "22px", fontWeight: "600" }],
        body: ["14px", { lineHeight: "21px", fontWeight: "400" }],
        meta: ["12px", { lineHeight: "18px", fontWeight: "500" }],
      },
      height: {
        btn: "44px",                  // full size, the phone tap target
        "btn-sm": "36px",             // small variant
      },
    },
  },
  plugins: [],
};