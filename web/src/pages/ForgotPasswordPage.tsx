import { useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import { BrandPanel } from '../components/BrandPanel';
import { BylineMark } from '../components/BylineMark';
import { ProblemNotice, type Problem } from '../components/ProblemNotice';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';

// P02: Same confirmation for every valid email address (SCRUM-10).
const UNREACHABLE: Problem = {
  title: 'Could not request a reset link',
  detail: 'Please check your connection and try again.',
};

export default function ForgotPasswordPage() {
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [problem, setProblem] = useState<Problem | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const email = String(form.get('email')).trim();

    setLoading(true);
    setProblem(null);

    try {
      const response = await fetch('/api/auth/forgot-password', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      if (!response.ok) {
        setProblem({
          title: 'Could not request a reset link',
          detail: response.status === 422 ? 'Enter a valid email address.' : 'Please try again.',
        });
        return;
      }

      setSubmitted(true);
    } catch {
      setProblem(UNREACHABLE);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-page lg:flex-row">
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

          {submitted ? (
            <>
              <h1 className="m-0 text-[30px] font-semibold leading-[38px]">Check your email</h1>
              <p role="status" className="m-0 text-body text-ink-body">
                If a Byline account exists for that email address, a password-reset link will be
                sent. The link is valid for one hour.
              </p>
              <Link to="/signin" className="text-[13px] font-semibold text-link underline">
                Back to sign in
              </Link>
            </>
          ) : (
            <>
              <h1 className="m-0 text-[30px] font-semibold leading-[38px]">
                Forgot your password?
              </h1>
              <p className="m-0 text-body text-ink-body">
                Enter your email address and we&apos;ll help you reset your Byline password.
              </p>

              <form className="flex flex-col gap-[18px]" onSubmit={handleSubmit}>
                <Input
                  label="Email address"
                  name="email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@example.com"
                  required
                />

                {problem && <ProblemNotice problem={problem} />}

                <Button
                  type="submit"
                  className="w-full !text-body !font-semibold"
                  loading={loading}
                >
                  Send reset link
                </Button>
              </form>

              <Link
                to="/signin"
                className="text-center text-[13px] font-semibold text-link underline"
              >
                Back to sign in
              </Link>
            </>
          )}
        </div>
      </main>

      <BrandPanel
        eyebrow="Your work is safe"
        heading="Get back to the work that matters."
        body="A forgotten password shouldn't keep you from your work and achievements."
        quote="“Every approved piece, credited to you by name.”"
        quoteBy="Byline"
      />
    </div>
  );
}
