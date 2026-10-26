import { useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { BrandPanel } from '../components/BrandPanel';
import { BylineMark } from '../components/BylineMark';
import { ProblemNotice, type Problem } from '../components/ProblemNotice';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { safeNext, signIn } from '../lib/auth';

// P01 Sign in, built to the Figma frame (SCRUM-8 layout, SCRUM-13 return-after-sign-in).
// Below 1024px the navy panel is dropped and the form takes the screen, as on a phone.

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

            {problem && <ProblemNotice problem={problem} />}

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
      <BrandPanel
        eyebrow="A record of real work"
        heading="Every approved piece, credited to you by name."
        body="Byline turns twelve weeks of unpaid work into something you can hand to an employer."
        quote="“I finished my internship with a spreadsheet row and no proof I had done anything.”"
        quoteBy="why this exists"
      />
    </div>
  );
}
