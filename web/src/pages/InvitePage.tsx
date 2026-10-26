import { useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { BrandPanel } from '../components/BrandPanel';
import { BylineMark } from '../components/BylineMark';
import { ProblemNotice, type Problem } from '../components/ProblemNotice';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { firstName, initials, startDate } from '../lib/home';
import {
  MIN_PASSWORD_LENGTH,
  UNREACHABLE,
  acceptInvite,
  acceptProblem,
  browserTimeZone,
  cohortWeeks,
  fetchInvite,
  linkHost,
  type Invite,
} from '../lib/invite';

// P05 Invite, built to the Figma frame (SCRUM-11). Route /invite/:token, public.
// Open: who invited you, what you join, one form that creates the account and signs you in.
// Expired / withdrawn: ask the inviter for a new one. Used: sign in. Unknown link: check the email.

type State =
  | { status: 'loading' }
  | { status: 'ready'; invite: Invite }
  | { status: 'missing' }
  | { status: 'unreachable' };

function DocIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M7 3h7l5 5v12a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zM14 3v5h5"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function Chip({ children }: { children: string }) {
  return (
    <span className="inline-flex h-7 items-center rounded-full border border-line bg-surface px-3 text-meta font-semibold text-ink">
      {children}
    </span>
  );
}

// Inviter, organization and the chips. Shown in every state so the person always knows who to ask.
function WhoAndWhere({ invite }: { invite: Invite }) {
  const { invited_by: inviter, organization, cohort, track } = invite;
  const weeks = cohortWeeks(cohort?.starts_on ?? null, cohort?.ends_on ?? null);
  return (
    <div className="flex flex-col gap-3.5">
      <div className="flex items-center gap-3">
        <span className="flex h-[38px] w-[38px] shrink-0 items-center justify-center rounded-full bg-primary text-[15px] font-semibold text-primary-on">
          {initials(inviter.full_name)}
        </span>
        <div className="min-w-0">
          <p className="m-0 text-meta text-ink-meta">{inviter.full_name} has invited you to join</p>
          <h1 className="m-0 text-[24px] font-semibold leading-[30px] tracking-[-0.01em]">
            {organization.name}
          </h1>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {cohort && <Chip>{cohort.name}</Chip>}
        {track && <Chip>{`Track: ${track.name}`}</Chip>}
        {cohort?.starts_on && <Chip>{`Starts ${startDate(cohort.starts_on, true)}`}</Chip>}
        {weeks && <Chip>{`${weeks} weeks`}</Chip>}
      </div>
    </div>
  );
}

function OnboardingPack({ invite }: { invite: Invite }) {
  const { track } = invite;
  return (
    <section className="flex flex-col gap-2.5 border-t border-line pt-5">
      <h2 className="m-0 font-sans text-meta uppercase tracking-[0.06em] text-ink-meta">
        Your onboarding pack
      </h2>
      {track?.onboarding_pack_url ? (
        <a
          href={track.onboarding_pack_url}
          target="_blank"
          rel="noreferrer"
          className="flex items-center justify-between gap-3 rounded-[10px] border border-line bg-surface-recessed px-[13px] py-[11px] text-ink no-underline hover:border-primary/40"
        >
          <span className="flex items-center gap-2.5">
            <DocIcon />
            <span className="text-[14px] font-semibold">Welcome to the {track.name} track</span>
          </span>
          <span className="text-meta text-ink-meta">{linkHost(track.onboarding_pack_url)}</span>
        </a>
      ) : (
        <p className="m-0 text-body text-ink-body">
          Your onboarding pack is on its way. Your organization adds it to your track.
        </p>
      )}
    </section>
  );
}

function JoinForm({ invite, token }: { invite: Invite; token: string }) {
  const navigate = useNavigate();
  const [problem, setProblem] = useState<Problem | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setProblem(null);
    setLoading(true);
    try {
      const response = await acceptInvite(token, {
        full_name: String(form.get('full_name')),
        password: String(form.get('password')),
        timezone: browserTimeZone(),
      });
      if (response.ok) {
        // Signed in by the cookie the API just set; the home page picks first-run or My Work.
        navigate('/', { replace: true });
        return;
      }
      setProblem(acceptProblem(response.status));
    } catch {
      setProblem(UNREACHABLE);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="flex flex-col gap-[18px]" onSubmit={handleSubmit} noValidate>
      <Input
        label="Your full name"
        name="full_name"
        autoComplete="name"
        placeholder="First and last name"
        required
      />
      <Input
        label="Email address"
        name="email"
        type="email"
        value={invite.email}
        hint="The address your invite was sent to"
        readOnly
      />
      <Input
        label="Create a password"
        name="password"
        type="password"
        autoComplete="new-password"
        placeholder={`At least ${MIN_PASSWORD_LENGTH} characters`}
        minLength={MIN_PASSWORD_LENGTH}
        required
      />

      {problem && <ProblemNotice problem={problem} />}

      <Button type="submit" className="w-full !text-body !font-semibold" loading={loading}>
        Join the program
      </Button>

      <p className="m-0 text-meta font-normal text-ink-meta">
        By joining you agree to the{' '}
        <Link to="/terms" className="font-semibold text-link underline">
          terms
        </Link>{' '}
        and the{' '}
        <Link to="/privacy" className="font-semibold text-link underline">
          privacy notice
        </Link>
        . Publishing your byline publicly is a separate choice, off by default, and you make it
        later.
      </p>
    </form>
  );
}

// Expired, withdrawn or used: a card instead of the form, with the one thing to do next.
function ClosedInvite({ invite }: { invite: Invite }) {
  const lead = firstName(invite.invited_by.full_name);
  const ask = `mailto:${invite.invited_by.email}?subject=${encodeURIComponent(
    `New Byline invite for ${invite.email}`,
  )}`;
  const copy = {
    expired: {
      title: 'This invite has expired',
      detail: `The link is the only thing that expired, not your place. Ask ${lead} for a new one and you are in.`,
    },
    revoked: {
      title: 'This invite was withdrawn',
      detail: `If you think that is a mistake, ask ${lead}.`,
    },
    used: {
      title: 'This invite was already used',
      detail: 'Your account exists. Sign in to continue.',
    },
    open: { title: '', detail: '' },
  }[invite.state];

  return (
    <section className="flex flex-col gap-3 rounded-xl border border-line bg-surface p-6">
      <h2 className="m-0 font-sans text-[17px] font-semibold leading-[22px]">{copy.title}</h2>
      <p className="m-0 text-body text-ink-body">{copy.detail}</p>
      {invite.state === 'used' ? (
        <Link
          to="/signin"
          className="inline-flex h-btn-sm w-fit items-center rounded-md bg-primary px-3.5 text-[13px] font-semibold text-primary-on no-underline hover:bg-primary/90"
        >
          Sign in
        </Link>
      ) : (
        <a
          href={ask}
          className="inline-flex h-btn-sm w-fit items-center rounded-md border border-line bg-surface px-3.5 text-[13px] font-semibold text-link no-underline hover:bg-surface-recessed"
        >
          Ask for a new invite
        </a>
      )}
    </section>
  );
}

function Message({ title, detail }: { title: string; detail: string }) {
  return (
    <div role="alert" className="flex flex-col gap-2">
      <h1 className="m-0 text-[24px] font-semibold leading-[30px] tracking-[-0.01em]">{title}</h1>
      <p className="m-0 text-body text-ink-body">{detail}</p>
    </div>
  );
}

export default function InvitePage() {
  const { token = '' } = useParams();
  const [state, setState] = useState<State>({ status: 'loading' });

  useEffect(() => {
    let current = true;
    fetchInvite(token)
      .then((invite) => {
        if (!current) return;
        setState(invite ? { status: 'ready', invite } : { status: 'missing' });
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
        title="This invite link is not valid"
        detail="Check the link in your email, or ask the person who invited you to send it again."
      />
    );
  } else if (state.status === 'unreachable') {
    content = <Message title={UNREACHABLE.title} detail={UNREACHABLE.detail} />;
  } else if (state.status === 'ready') {
    const { invite } = state;
    content = (
      <>
        <WhoAndWhere invite={invite} />
        {invite.state === 'open' ? (
          <JoinForm invite={invite} token={token} />
        ) : (
          <ClosedInvite invite={invite} />
        )}
        {invite.state === 'open' && <OnboardingPack invite={invite} />}
      </>
    );
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
        <div className="relative flex w-full max-w-[460px] flex-col gap-6">{content}</div>
      </main>
      <BrandPanel
        eyebrow="Day one"
        heading="This is the first thing a new intern ever sees."
        body="It creates the account and the membership in one action — and it says who invited you, which cohort you are joining and when it starts, before you type anything."
        quote="“Expired? Ask for a new one — the link is the only thing that expired, not your place.”"
        quoteBy="the expired-invite state"
      />
    </div>
  );
}
