import { useEffect, useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router';
import { BrandPanel } from '../components/BrandPanel';
import { BylineMark } from '../components/BylineMark';
import { ProblemNotice, type Problem } from '../components/ProblemNotice';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';

// P03: password reset with distinct expired and used link states (SCRUM-10).
type ResetState = 'checking' | 'valid' | 'expired' | 'used' | 'invalid' | 'success' | 'unreachable';

const MIN_PASSWORD_LENGTH = 10;

export default function ResetPasswordPage() {
  const { token = '' } = useParams();
  const [state, setState] = useState<ResetState>('checking');
  const [loading, setLoading] = useState(false);
  const [problem, setProblem] = useState<Problem | null>(null);

  const url = `/api/auth/reset-password/${encodeURIComponent(token)}`;

  useEffect(() => {
    if (!token) {
      return;
    }

    let active = true;

    fetch(`/api/auth/reset-password/${encodeURIComponent(token)}`, {
      credentials: 'same-origin',
      cache: 'no-store',
    })
      .then(async (response) => {
        if (!response.ok) throw new Error('Could not check reset link');
        const data: { state: string } = await response.json();

        if (!active) return;

        if (data.state === 'valid' || data.state === 'expired' || data.state === 'used') {
          setState(data.state);
        } else {
          setState('invalid');
        }
      })
      .catch(() => {
        if (active) setState('unreachable');
      });

    return () => {
      active = false;
    };
  }, [token]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const form = new FormData(event.currentTarget);
    const newPassword = String(form.get('new_password'));
    const confirmPassword = String(form.get('confirm_password'));

    setProblem(null);

    if (newPassword.length < MIN_PASSWORD_LENGTH) {
      setProblem({
        title: 'Password is too short',
        detail: 'Use at least 10 characters.',
      });
      return;
    }

    if (newPassword !== confirmPassword) {
      setProblem({
        title: 'Passwords do not match',
        detail: 'Enter the same password in both fields.',
      });
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(url, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          new_password: newPassword,
          confirm_password: confirmPassword,
        }),
      });

      if (response.ok) {
        setState('success');
        return;
      }

      if (response.status === 410) {
        const data = await response.json();
        const status = data?.detail?.state;

        if (status === 'expired' || status === 'used') {
          setState(status);
          return;
        }
      }

      if (response.status === 404) {
        setState('invalid');
        return;
      }

      setProblem({
        title: 'Could not reset your password',
        detail:
          response.status === 422 ? 'Check your password and try again.' : 'Please try again.',
      });
    } catch {
      setProblem({
        title: 'Byline could not be reached',
        detail: 'Check your connection and try again.',
      });
    } finally {
      setLoading(false);
    }
  }

  let content;

  if (state === 'checking') {
    content = (
      <p role="status" className="text-body text-ink-body">
        Checking your reset link...
      </p>
    );
  } else if (state === 'valid') {
    content = (
      <>
        <h1 className="m-0 text-[30px] font-semibold leading-[38px]">Create a new password</h1>
        <p className="m-0 text-body text-ink-body">
          Choose a new password for your Byline account.
        </p>

        <form className="flex flex-col gap-[18px]" onSubmit={handleSubmit}>
          <Input
            label="New password"
            name="new_password"
            type="password"
            autoComplete="new-password"
            minLength={MIN_PASSWORD_LENGTH}
            maxLength={1024}
            placeholder="At least 10 characters"
            required
          />

          <Input
            label="Confirm new password"
            name="confirm_password"
            type="password"
            autoComplete="new-password"
            required
          />

          {problem && <ProblemNotice problem={problem} />}

          <Button type="submit" className="w-full !text-body !font-semibold" loading={loading}>
            Reset password
          </Button>
        </form>
      </>
    );
  } else if (state === 'success') {
    content = (
      <>
        <h1 className="m-0 text-[30px] font-semibold leading-[38px]">Password updated</h1>
        <p role="status" className="m-0 text-body text-ink-body">
          Your password has been changed successfully. You can now sign in with your new password.
        </p>
        <Link to="/signin" className="font-semibold text-link underline">
          Go to sign in
        </Link>
      </>
    );
  } else {
    const messages = {
      expired: {
        title: 'This reset link has expired',
        detail: 'Reset links are valid for one hour. Request a new link to continue.',
      },
      used: {
        title: 'This reset link was already used',
        detail:
          'Your password was already reset using this link. You can sign in or request another link.',
      },
      invalid: {
        title: 'This reset link is invalid',
        detail: 'Check the link in your email or request a new password reset.',
      },
      unreachable: {
        title: 'Could not check your reset link',
        detail: 'Please check your connection and try again.',
      },
    }[state];

    content = (
      <>
        <h1 className="m-0 text-[30px] font-semibold leading-[38px]">{messages.title}</h1>
        <p role="alert" className="m-0 text-body text-ink-body">
          {messages.detail}
        </p>
        <Link to="/forgot" className="font-semibold text-link underline">
          Request a new reset link
        </Link>
        <Link to="/signin" className="text-[13px] font-semibold text-link underline">
          Back to sign in
        </Link>
      </>
    );
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
          {content}
        </div>
      </main>

      <BrandPanel
        eyebrow="Account security"
        heading="Your work stays yours."
        body="Secure password recovery keeps your Byline account and achievements protected."
        quote="“A record of real work, always connected to your name.”"
        quoteBy="Byline"
      />
    </div>
  );
}
