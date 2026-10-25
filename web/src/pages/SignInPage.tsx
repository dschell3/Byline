import type { CSSProperties, FormEvent } from 'react';
import { Link } from 'react-router';
import { BylineLogo } from '../components/BylineLogo';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';

// SCRUM-1: P01 (desktop) and X01 (phone) from the Figma export. Route /signin, public.

// Faint ruled lines behind the form, fading out to the left. Uses the line token so it follows the theme.
const formLines: CSSProperties = {
  backgroundImage:
    'repeating-linear-gradient(to bottom, rgb(var(--color-line)) 0 1px, transparent 1px 15px)',
  maskImage: 'linear-gradient(to left, #000, transparent)',
  WebkitMaskImage: 'linear-gradient(to left, #000, transparent)',
};

// Same lines on the navy panel, spaced 16px.
const panelLines: CSSProperties = {
  backgroundImage: 'repeating-linear-gradient(to bottom, #8FA4C0 0 1px, transparent 1px 16px)',
};

// The brand panel is navy in both themes, so its colours are fixed rather than theme tokens.
function BrandPanel() {
  return (
    <aside className="hidden items-center py-8 pr-8 xl:flex">
      <div className="relative flex min-h-[calc(100vh-4rem)] w-[600px] flex-col justify-between overflow-hidden rounded-[18px] bg-[#0F1D33] px-11 py-10 shadow-[0_20px_50px_rgba(15,29,51,0.18)]">
        <div aria-hidden="true" className="absolute inset-0 opacity-[0.14]" style={panelLines} />

        <div className="relative flex flex-col gap-3.5">
          <BylineLogo tone="navy" size={28} />
          <span className="mt-[18px] text-meta font-bold uppercase tracking-[0.1em] text-[#8C82E4]">
            A record of real work
          </span>
          <h2 className="max-w-[440px] font-serif text-page-title tracking-[-0.01em] text-white">
            Every approved piece, credited to you by name.
          </h2>
          <p className="max-w-[420px] text-[15px] leading-6 text-[#AFC0D6]">
            Byline turns twelve weeks of unpaid work into something you can hand to an employer.
          </p>
          <div className="mt-1 border-l-2 border-[#8C82E4] pl-4">
            <p className="text-[14px] italic leading-[22px] text-[#C6D5E8]">
              “I finished my internship with a spreadsheet row and no proof I had done anything.”
            </p>
            <p className="mt-2 text-meta text-[#8FA4C0]">— why this exists</p>
          </div>
        </div>

        <div className="relative flex justify-center">
          <svg
            width="400"
            height="250"
            viewBox="0 0 400 250"
            fill="none"
            aria-hidden="true"
            className="block"
          >
            {[74, 144, 214].map((y) => (
              <line key={y} x1="14" y1={y} x2="386" y2={y} stroke="#2C4870" strokeWidth="1.5" />
            ))}
            <rect x="14" y="48" width="168" height="10" rx="5" fill="#3E5F8C" />
            <rect x="14" y="118" width="168" height="10" rx="5" fill="#3E5F8C" />
            <rect x="14" y="188" width="240" height="10" rx="5" fill="#3E5F8C" />
            {[56, 126].map((y) => (
              <path
                key={y}
                d={`M348 ${y} l6 7 11-14`}
                stroke="#7FE3A8"
                strokeWidth="2.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            ))}
            <path
              d="M20 182c9-22 18-26 21-15 2.5 9-6 17 1.5 19 7 2 13-8 18-20"
              stroke="#8C82E4"
              strokeWidth="2.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>

        <p className="relative text-meta font-normal text-[#7A8FAC]">
          The Emerson Empire · a record of real work
        </p>
      </div>
    </aside>
  );
}

export default function SignInPage() {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    // TODO(auth card): send credentials to the API; on failure show the P01 error box.
  }

  return (
    // Capped at the 1440px Figma frame width and centred, so wide monitors keep P01's proportions.
    <div className="min-h-screen bg-page">
      <div className="mx-auto flex min-h-screen max-w-[1440px] flex-col xl:flex-row">
        {/* Phone/tablet top bar (X01) */}
        <header className="flex h-14 shrink-0 items-center justify-center border-b border-line bg-surface xl:hidden">
          <BylineLogo tone="page" size={28} />
        </header>

        <main className="relative flex flex-1 justify-center px-4 pb-10 pt-10 xl:items-center xl:px-14 xl:py-10">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-y-0 right-0 hidden w-[760px] max-w-full opacity-50 xl:block"
            style={formLines}
          />

          <div className="relative flex w-full max-w-[460px] flex-col gap-3.5 xl:gap-[18px]">
            <div className="hidden xl:block">
              <BylineLogo tone="page" size={30} />
            </div>

            <h1 className="font-serif text-[24px] font-semibold leading-[31px] tracking-[-0.01em] text-ink xl:text-[30px] xl:leading-[38px]">
              Sign in
            </h1>

            <form onSubmit={handleSubmit} className="flex flex-col gap-3.5 xl:gap-[18px]">
              <Input
                label="Email address"
                name="email"
                type="email"
                autoComplete="email"
                required
              />
              <Input
                label="Password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
              />
              <Button type="submit" className="w-full">
                Sign in
              </Button>
            </form>

            <Link
              to="/forgot"
              className="text-center text-[13px] font-semibold text-link hover:underline"
            >
              I forgot my password
            </Link>

            <p className="mt-2 text-center text-meta text-ink-meta xl:mt-0">
              New here? Your supervisor sends you an invite link by email.
            </p>
          </div>
        </main>

        <BrandPanel />
      </div>
    </div>
  );
}
