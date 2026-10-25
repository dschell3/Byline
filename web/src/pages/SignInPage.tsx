import { useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { BylineMark } from '../components/BylineMark';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { safeNext, signIn } from '../lib/auth';

// P01 Sign in, built to the Figma frame (SCRUM-8 layout, SCRUM-13 return-after-sign-in).
// Below 1024px the navy panel is dropped and the form takes the screen, as on a phone.

type Problem = { title: string; detail: string };

const WRONG_CREDENTIALS: Problem = {
  title: 'Email or password is not right',
  detail: 'Check both and try again. For your safety we do not say which one was wrong.',
};
const UNREACHABLE: Problem = {
  title: 'Byline could not be reached',
  detail: 'Check your connection and try again.',
};

async function problemFrom(response: Response): Promise<Problem> {
  if (response.status === 429) {
    const body = await response.json().catch(() => ({}));
    return {
      title: 'Too many attempts',
      detail: typeof body.detail === 'string' ? body.detail : 'Try again later.',
    };
  }
  // 401 is the API's deliberate "either could be wrong"; a 422 (malformed email) reads the same.
  return WRONG_CREDENTIALS;
}

function WarningIcon() {
  return (
    <svg
      width="19"
      height="19"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="mt-px shrink-0 text-status-overdue-text"
    >
      <path d="M12 3 2.5 20h19L12 3z" />
      <line x1="12" y1="10" x2="12" y2="14" />
      <circle cx="12" cy="17" r=".6" fill="currentColor" />
    </svg>
  );
}

function BrandPanel() {
  return (
    <aside className="hidden flex-1 items-center py-8 pr-8 lg:flex">
      <div className="ruled-navy relative flex h-full max-h-[856px] w-full max-w-[600px] flex-col justify-between overflow-hidden rounded-[18px] bg-navy px-11 py-10 shadow-[0_20px_50px_rgba(15,29,51,0.18)]">
        <div className="flex flex-col gap-3.5">
          <BylineMark tone="navy" />
          <span className="mt-[18px] text-meta font-bold uppercase tracking-[0.1em] text-navy-accent">
            A record of real work
          </span>
          <h2 className="m-0 max-w-[440px] text-page-title tracking-[-0.01em] text-navy-heading">
            Every approved piece, credited to you by name.
          </h2>
          <p className="m-0 max-w-[420px] text-[15px] leading-6 text-navy-body">
            Byline turns twelve weeks of unpaid work into something you can hand to an employer.
          </p>
          <blockquote className="m-0 mt-1 border-l-2 border-navy-accent pl-4">
            <p className="m-0 text-[14px] italic leading-[22px] text-navy-quote">
              “I finished my internship with a spreadsheet row and no proof I had done anything.”
            </p>
            <p className="m-0 mt-2 text-meta font-normal text-navy-meta">— why this exists</p>
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

export default function SignInPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [problem, setProblem] = useState<Problem | null>(null);
  const [loading, setLoading] = useState(false);
  const returning = params.has('next');

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setProblem(null);
    setLoading(true);
    try {
      const response = await signIn(String(form.get('email')), String(form.get('password')));
      if (response.ok) {
        navigate(safeNext(params.get('next'), window.location.origin), { replace: true });
        return;
      }
      setProblem(await problemFrom(response));
    } catch {
      setProblem(UNREACHABLE);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-page lg:flex-row">
      {/* Phone and tablet (Figma X01): a white bar carries the logo and the form starts near the top. */}
      <header className="flex h-[55px] items-center justify-center border-b border-line bg-surface lg:hidden">
        <BylineMark />
      </header>
      <main className="relative flex flex-1 justify-center px-4 pb-10 pt-14 sm:px-14 lg:max-w-[840px] lg:items-center lg:py-10">
        <div
          aria-hidden="true"
          className="ruled-page pointer-events-none absolute inset-y-0 right-0 hidden w-[90%] lg:block"
        />
        <div className="relative flex w-full max-w-[460px] flex-col gap-[18px]">
          <div className="hidden lg:block">
            <BylineMark />
          </div>
          <h1 className="m-0 text-[30px] font-semibold leading-[38px] tracking-[-0.01em]">
            Sign in
          </h1>

          {returning && (
            <p className="m-0 rounded-xl border border-status-approved-text/30 bg-status-approved-fill px-[17px] py-[15px] text-[13px] leading-5 text-ink-body">
              You were signed out. Sign in again and you come straight back to the page you were on.
            </p>
          )}

          <form className="flex flex-col gap-[18px]" onSubmit={handleSubmit} noValidate>
            <Input label="Email address" name="email" type="email" autoComplete="email" required />
            <Input
              label="Password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
            />

            {problem && (
              <div
                role="alert"
                className="flex items-start gap-3 rounded-xl border border-status-overdue-text/20 bg-status-overdue-fill px-[17px] py-[15px]"
              >
                <WarningIcon />
                <div className="flex flex-col gap-[5px]">
                  <p className="m-0 text-[14px] font-semibold text-status-overdue-text">
                    {problem.title}
                  </p>
                  <p className="m-0 text-[13px] leading-5 text-ink-body">{problem.detail}</p>
                </div>
              </div>
            )}

            <Button type="submit" className="w-full !text-body !font-semibold" loading={loading}>
              Sign in
            </Button>
          </form>

          <div className="text-center">
            {/* P02 Forgot password is SCRUM-10. */}
            <Link to="/forgot" className="text-[13px] font-semibold text-link underline">
              I forgot my password
            </Link>
          </div>
          <p className="m-0 text-center text-meta text-ink-meta">
            New here? Your supervisor sends you an invite link by email.
          </p>
        </div>
      </main>
      <BrandPanel />
    </div>
  );
}
