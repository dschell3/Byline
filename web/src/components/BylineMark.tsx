// The Byline logo: the signature mark and the wordmark, from the Figma P01 frame.
// "light" sits on the page background, "navy" on the dark brand panel.
type Props = { tone?: 'light' | 'navy' };

export function BylineMark({ tone = 'light' }: Props) {
  const navy = tone === 'navy';
  return (
    <span className="inline-flex items-center gap-2.5">
      <svg
        width={navy ? 28 : 30}
        height={navy ? 28 : 30}
        viewBox="0 0 28 28"
        fill="none"
        aria-hidden="true"
        className="shrink-0"
      >
        <rect
          x="1"
          y="1"
          width="26"
          height="26"
          rx="7.5"
          className={navy ? 'fill-navy-heading' : 'fill-primary'}
        />
        <path
          d="M6.5 20.5h15"
          strokeWidth="2.1"
          strokeLinecap="round"
          className={navy ? 'stroke-primary' : 'stroke-primary-on'}
        />
        <path
          d="M7.6 15.8c2.1-5.6 4.3-6.4 5-3.8.6 2.3-1.5 4.3.3 4.8 1.7.5 3.1-2 4.3-5.1"
          strokeWidth="2.1"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={navy ? 'stroke-navy-accent' : 'stroke-accent'}
        />
        <circle cx="20.4" cy="12.6" r="1.5" className={navy ? 'fill-navy-accent' : 'fill-accent'} />
      </svg>
      <span
        className={`font-serif font-bold tracking-[-0.025em] ${
          navy ? 'text-[22px] text-navy-heading' : 'text-[24px] text-ink'
        }`}
      >
        Byline
      </span>
    </span>
  );
}
