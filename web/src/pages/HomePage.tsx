import { useEffect, useState, type ReactNode } from 'react';
import { Card } from '../components/ui/Card';
import {
  cohortStage,
  dateRange,
  fetchHome,
  firstName,
  inDays,
  initials,
  startDate,
  timeZoneLabel,
  todayIn,
  type Home,
} from '../lib/home';

// "/" for a member. SCRUM-16: until anything is assigned this is the first-run screen (P11,
// X11 on phones); once work exists it gives way to My Work (P10), which SCRUM-14 builds.

type State = { status: 'loading' } | { status: 'ready'; home: Home | null } | { status: 'error' };

function ClockIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8" />
      <path d="M12 7.5V12l3 2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

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

const SECTION_TITLE = 'm-0 font-serif text-[18px] font-semibold leading-7 text-ink';
const EYEBROW = 'm-0 text-meta uppercase tracking-[0.06em] text-ink-meta';
// A card on phones; on desktop the two side sections share one card (P11), so they drop their own.
const SIDE_SECTION =
  'flex flex-col gap-3 rounded-xl border border-line bg-surface p-6 lg:rounded-none lg:border-0 lg:bg-transparent lg:p-0';

function Row({
  label,
  value,
  className = '',
}: {
  label: string;
  value: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`flex items-baseline justify-between gap-4 border-b border-line py-3 ${className}`}
    >
      <span className="text-meta text-ink-meta">{label}</span>
      <span className="text-right text-[14px] font-semibold text-ink">{value}</span>
    </div>
  );
}

function StartCard({ home, today }: { home: Home; today: string }) {
  const { cohort, supervisor } = home;
  const stage = cohortStage(cohort?.starts_on ?? null, today);
  const lead = supervisor ? firstName(supervisor.full_name) : 'Your supervisor';
  const cohortName = cohort?.name ?? 'Your cohort';

  if (stage.kind === 'upcoming' && cohort?.starts_on) {
    return (
      <Card className="!p-6">
        <p className={`${EYEBROW} hidden lg:block`}>The cohort has not started</p>
        <div className="flex items-center gap-4 lg:mt-4">
          <span className="text-primary lg:flex lg:h-[52px] lg:w-[52px] lg:items-center lg:justify-center lg:rounded-xl lg:border lg:border-line lg:bg-surface-recessed">
            <ClockIcon />
          </span>
          <div>
            <p className="m-0 text-[17px] font-semibold leading-[22px] text-ink">
              {cohortName} starts{' '}
              <span className="hidden lg:inline">{startDate(cohort.starts_on)}</span>
              <span className="lg:hidden">{startDate(cohort.starts_on, true)}</span>
            </p>
            <p className="m-0 hidden text-meta text-ink-meta lg:block">
              That is {inDays(stage.daysUntil)}. Your timezone: {timeZoneLabel(home.timezone)}.
            </p>
          </div>
        </div>
        <p className="m-0 mt-3 text-body text-ink-body lg:hidden">
          {inDays(stage.daysUntil).replace(/^./, (c) => c.toUpperCase())}, your time.
        </p>
        <p className="m-0 mt-4 hidden text-body text-ink-body lg:block">
          Nothing to do until then. Read your onboarding pack if you would like a head start.
        </p>
      </Card>
    );
  }

  const week =
    stage.kind === 'running' && stage.week ? ` is in week ${stage.week}` : ' is under way';
  return (
    <Card className="!p-6">
      <p className={EYEBROW}>Cohort running, nothing assigned to you yet</p>
      <p className="m-0 mt-4 text-body text-ink-body">
        {cohortName}
        {week}. {lead} has not assigned anything to you yet — that is normal in your first days.
        {supervisor ? ` When ${lead} does,` : ' When they do,'} it appears here and we email you.
      </p>
      {supervisor && (
        <a
          href={`mailto:${supervisor.email}`}
          className="mt-4 inline-flex h-btn-sm items-center rounded-md border border-line bg-surface px-3.5 text-[13px] font-semibold text-link no-underline hover:bg-surface-recessed"
        >
          Message {lead}
        </a>
      )}
    </Card>
  );
}

function WhatHappensNext({ lead }: { lead: string }) {
  const steps = [
    [`${lead} posts your first assignment`, 'You get an email and it appears here.'],
    [
      'You submit — text, a file, a link or a pull request',
      'Your typing is saved even if an upload fails.',
    ],
    [
      `${lead} approves it or asks for a change`,
      'If a change is asked for, the reason is written out for you.',
    ],
    [
      'Approved work is credited to you, permanently',
      'It goes on your byline page, which is yours to keep.',
    ],
  ];
  return (
    <Card className="!p-6 hidden lg:block">
      <h2 className={SECTION_TITLE}>What happens next</h2>
      <ol className="m-0 mt-4 flex list-none flex-col gap-4 p-0">
        {steps.map(([title, detail], index) => (
          <li key={title} className="flex gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-meta font-semibold text-primary-on">
              {index + 1}
            </span>
            <div>
              <p className="m-0 text-[14px] font-semibold leading-[22px] text-ink">{title}</p>
              <p className="m-0 mt-0.5 text-meta text-ink-meta">{detail}</p>
            </div>
          </li>
        ))}
      </ol>
    </Card>
  );
}

function YouAreIn({ home }: { home: Home }) {
  const { organization, cohort, track, supervisor } = home;
  return (
    <section className={SIDE_SECTION}>
      <h2 className={SECTION_TITLE}>You are in</h2>
      <div>
        <Row label="Organization" value={organization.name} className="hidden lg:flex" />
        <Row label="Cohort" value={cohort?.name ?? 'Not set yet'} />
        <Row label="Track" value={track?.name ?? 'Not set yet'} />
        {cohort?.starts_on && cohort.ends_on && (
          <Row
            label="Runs"
            value={dateRange(cohort.starts_on, cohort.ends_on)}
            className="hidden lg:flex"
          />
        )}
        <Row
          label="Your timezone"
          value={timeZoneLabel(home.timezone)}
          className="hidden lg:flex"
        />
        <Row
          label="Supervisor"
          value={supervisor?.full_name ?? 'Not set yet'}
          className="lg:hidden"
        />
      </div>

      <div className="mt-2 hidden items-center gap-3 rounded-xl border border-line bg-surface-recessed px-4 py-3.5 lg:flex">
        <span className="flex h-[38px] w-[38px] shrink-0 items-center justify-center rounded-full bg-primary text-[15px] font-semibold text-primary-on">
          {supervisor ? initials(supervisor.full_name) : '?'}
        </span>
        <div className="min-w-0">
          <p className="m-0 text-[14px] font-semibold leading-[22px] text-ink">
            {supervisor?.full_name ?? 'Your supervisor'}
          </p>
          <p className="m-0 truncate text-meta text-ink-meta">
            {supervisor ? (
              <>
                Your supervisor ·{' '}
                <a href={`mailto:${supervisor.email}`} className="text-ink-meta">
                  {supervisor.email}
                </a>
              </>
            ) : (
              'Assigned when you join a team. Your organization will set this.'
            )}
          </p>
        </div>
      </div>
    </section>
  );
}

function OnboardingPack({ home }: { home: Home }) {
  const { track } = home;
  return (
    <section className={SIDE_SECTION}>
      <h2 className={`${SECTION_TITLE} lg:mt-1`}>Your onboarding pack</h2>
      {track?.onboarding_pack_url ? (
        <a
          href={track.onboarding_pack_url}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-2.5 rounded-[10px] py-2 text-ink no-underline lg:border lg:border-line lg:bg-surface-recessed lg:px-[13px] lg:py-[11px] lg:hover:border-primary/40"
        >
          <DocIcon />
          <span className="text-[14px] font-semibold">Welcome to the {track.name} track</span>
        </a>
      ) : (
        <p className="m-0 text-body text-ink-body">
          Your onboarding pack is on its way. Your organization adds it to your track.
        </p>
      )}
    </section>
  );
}

function FirstRun({ home }: { home: Home }) {
  const today = todayIn(home.timezone);
  const lead = home.supervisor ? firstName(home.supervisor.full_name) : 'Your supervisor';
  return (
    <main className="relative flex-1 px-4 pb-12 pt-6 lg:px-14 lg:pt-14">
      <div
        aria-hidden="true"
        className="ruled-page pointer-events-none absolute inset-y-0 right-0 hidden w-1/3 lg:block"
      />
      <div className="relative">
        <h1 className="m-0 text-page-title tracking-[-0.01em]">
          Welcome, {firstName(home.full_name)}
        </h1>
        <p className="m-0 mt-2 max-w-[760px] text-body text-ink-body">
          Nothing is assigned to you yet.
          <span className="hidden lg:inline">
            {' '}
            Here is who you are with, and what happens next.
          </span>
        </p>
        <div className="mt-6 grid gap-4 lg:mt-9 lg:grid-cols-[760fr_576fr] lg:gap-6">
          <div className="flex flex-col gap-4 lg:gap-6">
            <StartCard home={home} today={today} />
            <WhatHappensNext lead={lead} />
          </div>
          <div className="flex flex-col gap-4 self-start lg:gap-5 lg:rounded-xl lg:border lg:border-line lg:bg-surface lg:p-6">
            <YouAreIn home={home} />
            <OnboardingPack home={home} />
          </div>
        </div>
      </div>
    </main>
  );
}

// Placeholder until SCRUM-14 lands P10. Kept here so the hand-over point is obvious.
function MyWorkPlaceholder() {
  return (
    <main className="flex-1 px-4 py-10 lg:px-14">
      <h1 className="m-0 text-page-title">My work</h1>
      <p className="m-0 mt-2 text-body text-ink-body">Your assignments will be listed here.</p>
    </main>
  );
}

export default function HomePage() {
  const [state, setState] = useState<State>({ status: 'loading' });

  useEffect(() => {
    let current = true;
    fetchHome()
      .then((home) => current && setState({ status: 'ready', home }))
      .catch(() => current && setState({ status: 'error' }));
    return () => {
      current = false;
    };
  }, []);

  if (state.status === 'loading') return null;
  if (state.status === 'error') {
    return (
      <p role="alert" className="p-8 text-body text-ink">
        Your home page could not be loaded. Reload the page to try again.
      </p>
    );
  }
  if (!state.home) {
    return (
      <main className="flex-1 px-4 py-10 lg:px-14">
        <h1 className="m-0 text-page-title">Welcome to Byline</h1>
        <p className="m-0 mt-2 text-body text-ink-body">
          You are not part of an organization yet. Use the invite link your supervisor emailed you.
        </p>
      </main>
    );
  }
  return state.home.has_work ? <MyWorkPlaceholder /> : <FirstRun home={state.home} />;
}
