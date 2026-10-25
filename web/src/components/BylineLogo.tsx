// Byline mark + wordmark from the Figma frames.
// "page" follows the light/dark theme; "navy" is for the always-dark brand panel.
type BylineLogoProps = { tone: 'page' | 'navy'; size: number };

export function BylineLogo({ tone, size }: BylineLogoProps) {
  const onNavy = tone === 'navy';
  const wordSize = size >= 30 ? 'text-[24px]' : 'text-[22px]';

  return (
    <span className="inline-flex items-center gap-2.5">
      <svg
        width={size}
        height={size}
        viewBox="0 0 28 28"
        fill="none"
        aria-hidden="true"
        className="block shrink-0"
      >
        <rect
          x="1"
          y="1"
          width="26"
          height="26"
          rx="7.5"
          className={onNavy ? 'fill-white' : 'fill-primary'}
        />
        <path
          d="M6.5 20.5h15"
          strokeWidth="2.1"
          strokeLinecap="round"
          className={onNavy ? 'stroke-[#1B3A6B]' : 'stroke-white'}
        />
        <path
          d="M7.6 15.8c2.1-5.6 4.3-6.4 5-3.8.6 2.3-1.5 4.3.3 4.8 1.7.5 3.1-2 4.3-5.1"
          strokeWidth="2.1"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={onNavy ? 'stroke-[#8C82E4]' : 'stroke-accent'}
        />
        <circle cx="20.4" cy="12.6" r="1.5" className={onNavy ? 'fill-[#8C82E4]' : 'fill-accent'} />
      </svg>
      <span
        className={`font-serif font-bold tracking-[-0.025em] ${wordSize} ${onNavy ? 'text-white' : 'text-ink'}`}
      >
        Byline
      </span>
    </span>
  );
}
