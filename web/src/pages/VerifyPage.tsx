import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { Link, useParams } from 'react-router';
import { BrandPanel } from '../components/BrandPanel';
import { BylineMark } from '../components/BylineMark';
import { ProblemNotice, type Problem } from '../components/ProblemNotice';
import { Button } from '../components/ui/Button';
import {
  LINK_LIFETIME,
  UNREACHABLE,
  confirmedOn,
  resendProblem,
  resendVerification,
  verifyEmail,
  type Verification,
} from '../lib/verify';

// P04 Verify, built to the Figma frame (SCRUM-12). Route /verify/:token, public.
// Three screens, none of them a generic error: confirmed (then on to My Work or first run),
// expired (send a new link), already verified (sign in). An unknown link says to check the email.

type State =
  | { status: 'loading' }
  | { status: 'ready'; verification: Verification }
  | { status: 'missing' }
  | { status: 'unreachable' };

function CheckIcon() {
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
      className="mt-px shrink-0 text-status-approved-text"
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

const PRIMARY_LINK =
  'inline-flex h-btn items-center justify-center rounded-md bg-primary px-4 text-card-title text-primary-on no-underline hover:bg-primary/90';

function Heading({ children }: { children: ReactNode }) {
  return (
    <h1 className="m-0 text-[24px] font-semibold leading-[31px] tracking-[-0.01em] lg:text-[30px] lg:leading-[38px]">
      {children}
    </h1>
  );
}

// The left-ruled card from the Figma frame. The rule's colour tells the two non-success states apart.
function StateCard({
  rule,
  title,
  children,
}: {
  rule: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <div
      className={`rounded-[11px] border border-l-[3px] border-line bg-surface px-[15px] py-[13px] ${rule}`}
    >
      <p className="m-0 text-[14px] font-semibold text-ink">{title}</p>
      <p className="m-0 mt-1 text-[13px] leading-[21px] text-ink-body">{children}</p>
    </div>
  );
}

function Confirmed({ verification }: { verification: Verification }) {
  return (
    <>
      <Heading>Email confirmed</Heading>
      <div
        role="status"
        className="flex items-start gap-3 rounded-xl border border-status-approved-text/20 bg-status-approved-fill px-[17px] py-[15px]"
      >
        <CheckIcon />
        <div className="flex flex-col gap-[5px]">
          <p className="m-0 break-all text-[14px] font-semibold text-status-approved-text">
            {verification.email} is verified
          </p>
          <p className="m-0 text-[13px] leading-5 text-ink-body">
            You will be emailed when work is assigned to you, when feedback is left, and when work
            is approved.
          </p>
        </div>
      </div>
      {/* "/" shows My Work (P10) or first run (P11) depending on whether work exists. */}
      <Link to="/" className={`${PRIMARY_LINK} w-full`}>
        Go to my work
      </Link>
    </>
  );
}

function Expired({ verification, token }: { verification: Verification; token: string }) {
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [problem, setProblem] = useState<Problem | null>(null);

  // A form, like the other public pages, so the button needs no inline handler.
  async function sendNewLink(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSending(true);
    setProblem(null);
    try {
      const status = await resendVerification(token);
      if (status === 202) setSent(true);
      else setProblem(resendProblem(status));
    } catch {
      setProblem(UNREACHABLE);
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <Heading>This link has expired</Heading>
      <StateCard rule="border-l-status-changes-text" title="Nothing is lost">
        Verification links last {LINK_LIFETIME}. We can send a new one to{' '}
        <span className="break-all font-semibold text-ink">{verification.email}</span>.
      </StateCard>
      {problem && <ProblemNotice problem={problem} />}
      {sent ? (
        <p role="status" className="m-0 text-body text-ink-body">
          A new link is on its way to{' '}
          <span className="break-all font-semibold text-ink">{verification.email}</span>. It lasts{' '}
          {LINK_LIFETIME}.
        </p>
      ) : (
        <form onSubmit={sendNewLink}>
          <Button type="submit" className="w-full" loading={sending}>
            Send a new link
          </Button>
        </form>
      )}
    </>
  );
}

function AlreadyVerified({ verification }: { verification: Verification }) {
  const on = verification.verified_at ? ` on ${confirmedOn(verification.verified_at)}` : '';
  return (
    <>
      <Heading>Already verified</Heading>
      <StateCard rule="border-l-status-due-soon-text" title="Nothing more to do here">
        <span className="break-all">{verification.email}</span> was confirmed{on}.
      </StateCard>
      <Link to="/signin" className={PRIMARY_LINK}>
        Sign in
      </Link>
    </>
  );
}

function Message({ title, detail }: { title: string; detail: string }) {
  return (
    <div role="alert" className="flex flex-col gap-3">
      <Heading>{title}</Heading>
      <p className="m-0 text-body text-ink-body">{detail}</p>
      <Link to="/signin" className={PRIMARY_LINK}>
        Sign in
      </Link>
    </div>
  );
}

export default function VerifyPage() {
  const { token = '' } = useParams();
  const [state, setState] = useState<State>({ status: 'loading' });
  // The link is single-use, so it must be sent exactly once. React's dev mode runs effects twice;
  // keeping the request in a ref means the second run waits on the first instead of re-sending.
  const request = useRef<{ token: string; result: Promise<Verification | null> } | null>(null);

  useEffect(() => {
    if (request.current?.token !== token) {
      request.current = { token, result: verifyEmail(token) };
    }
    let current = true;
    request.current.result
      .then((verification) => {
        if (!current) return;
        setState(verification ? { status: 'ready', verification } : { status: 'missing' });
      })
      .catch(() => current && setState({ status: 'unreachable' }));
    return () => {
      current = false;
    };
  }, [token]);

  let content = null;
  if (state.status === 'missing') {
    content = (
      <Message
        title="This link is not valid"
        detail="Check the link in your email. If you already have an account, you can sign in."
      />
    );
  } else if (state.status === 'unreachable') {
    content = <Message title={UNREACHABLE.title} detail={UNREACHABLE.detail} />;
  } else if (state.status === 'ready') {
    const { verification } = state;
    content = {
      verified: <Confirmed verification={verification} />,
      expired: <Expired verification={verification} token={token} />,
      already_verified: <AlreadyVerified verification={verification} />,
    }[verification.state];
  }

  return (
    <div className="flex min-h-screen flex-col bg-page lg:flex-row">
      <header className="flex h-[55px] items-center justify-center border-b border-line bg-surface lg:hidden">
        <BylineMark />
      </header>
      <main className="relative flex flex-1 justify-center px-4 pb-10 pt-10 sm:px-14 lg:max-w-[840px] lg:items-center lg:py-10">
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
        eyebrow="Almost in"
        heading="Confirming your address is what turns email on."
        body="Most of our members read the email and never open the app that day. Getting this right is the difference between hearing about your work and not."
      />
    </div>
  );
}
