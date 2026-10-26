import type { ReactNode } from 'react';
import { BylineMark } from './BylineMark';

// The navy brand panel on the public pages (P01 sign-in, P05 invite), from the Figma frames.
// Navy in both themes. Each page passes its own copy; the mark, lines and illustration are shared.
type Props = {
  eyebrow: string;
  heading: ReactNode;
  body: ReactNode;
  quote: string;
  quoteBy: string;
};

export function BrandPanel({ eyebrow, heading, body, quote, quoteBy }: Props) {
  return (
    <aside className="hidden flex-1 items-center py-8 pr-8 lg:flex">
      <div className="ruled-navy relative flex h-full max-h-[856px] w-full max-w-[600px] flex-col justify-between overflow-hidden rounded-[18px] bg-navy px-11 py-10 shadow-[0_20px_50px_rgba(15,29,51,0.18)]">
        <div className="flex flex-col gap-3.5">
          <BylineMark tone="navy" />
          <span className="mt-[18px] text-meta font-bold uppercase tracking-[0.1em] text-navy-accent">
            {eyebrow}
          </span>
          <h2 className="m-0 max-w-[440px] text-page-title tracking-[-0.01em] text-navy-heading">
            {heading}
          </h2>
          <p className="m-0 max-w-[420px] text-[15px] leading-6 text-navy-body">{body}</p>
          <blockquote className="m-0 mt-1 border-l-2 border-navy-accent pl-4">
            <p className="m-0 text-[14px] italic leading-[22px] text-navy-quote">{quote}</p>
            <p className="m-0 mt-2 text-meta font-normal text-navy-meta">— {quoteBy}</p>
          </blockquote>
        </div>

        <svg
          viewBox="0 0 400 250"
          fill="none"
          aria-hidden="true"
          className="mx-auto block w-full max-w-[400px]"
        >
          {[74, 144].map((y) => (
            <g key={y}>
              <line x1="14" y1={y} x2="386" y2={y} strokeWidth="1.5" className="stroke-navy-rule" />
              <rect x="14" y={y - 26} width="168" height="10" rx="5" className="fill-navy-bar" />
              <path
                d={`M348 ${y - 18} l6 7 11-14`}
                strokeWidth="2.6"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="stroke-navy-check"
              />
            </g>
          ))}
          <line x1="14" y1="214" x2="386" y2="214" strokeWidth="1.5" className="stroke-navy-rule" />
          <rect x="14" y="188" width="240" height="10" rx="5" className="fill-navy-bar" />
          <path
            d="M20 182c9-22 18-26 21-15 2.5 9-6 17 1.5 19 7 2 13-8 18-20"
            strokeWidth="2.6"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="stroke-navy-accent"
          />
        </svg>

        <p className="m-0 text-meta font-normal text-navy-footer">
          The Emerson Empire · a record of real work
        </p>
      </div>
    </aside>
  );
}
