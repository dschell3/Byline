import { useEffect, useRef, useState, type ReactNode } from 'react';
import { NavLink, Outlet, useLocation, useNavigate, useOutletContext } from 'react-router';
import { signOut, type CurrentUser } from '../lib/auth';
import { fetchHome, firstName, initials, type Home } from '../lib/home';
import { cohortProgress, pageTitle, roleLabel } from '../lib/shell';
import { BylineMark } from './BylineMark';

// SCRUM-82: the signed-in shell from the Figma app chrome (P10 sidebar + top bar).
// Sits inside RequireAuth, so the signed-in person is always known here.
// Phones: the sidebar becomes a drawer opened from the top bar (X11).

type IconProps = { children: ReactNode };

function Icon({ children }: IconProps) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

const LINKS = [
  {
    to: '/',
    label: 'My work',
    icon: (
      <Icon>
        <rect x="4" y="4" width="16" height="16" rx="3" />
        <path d="m9 12 2 2 4-4" />
      </Icon>
    ),
  },
  {
    to: '/byline',
    label: 'My byline',
    icon: (
      <Icon>
        <path d="M5 4h14v16H5zM9 9h6M9 13h6M9 17h3" />
      </Icon>
    ),
  },
  {
    to: '/updates',
    label: 'Updates',
    icon: (
      <Icon>
        <path d="M6 16V11a6 6 0 1 1 12 0v5l1.5 2h-15L6 16zM10 20.5a2 2 0 0 0 4 0" />
      </Icon>
    ),
  },
];

function itemClass({ isActive }: { isActive: boolean }) {
  return `relative flex h-11 items-center gap-3 rounded-lg px-3 text-[14px] font-medium no-underline ${
    isActive
      ? 'bg-surface-recessed font-semibold text-ink before:absolute before:inset-y-2 before:left-0 before:w-[3px] before:rounded-sm before:bg-primary'
      : 'text-ink-body hover:bg-surface-recessed hover:text-ink'
  }`;
}

function MenuIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M4 7h16M4 12h16M4 17h16"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function BellIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M6 16V11a6 6 0 1 1 12 0v5l1.5 2h-15L6 16zM10 20.5a2 2 0 0 0 4 0"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CohortProgress({ home }: { home: Home | null }) {
  const progress = home ? cohortProgress(home.cohort, home.timezone) : null;
  if (!progress) return null;
  return (
    <div className="mx-3 rounded-lg bg-surface-recessed p-3">
      <p className="text-meta font-semibold text-ink">Cohort progress</p>
      <p className="mt-1 text-meta text-ink-meta">{progress.label}</p>
      {progress.percent !== null && (
        <div
          role="progressbar"
          aria-label="Cohort progress"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progress.percent}
          className="mt-2 h-1.5 overflow-hidden rounded-full bg-line"
        >
          <div
            className="h-full rounded-full bg-primary"
            style={{ width: `${progress.percent}%` }}
          />
        </div>
      )}
    </div>
  );
}

export default function AppLayout() {
  const user = useOutletContext<CurrentUser>();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [home, setHome] = useState<Home | null>(null);
  const menuButton = useRef<HTMLButtonElement>(null);
  const sidebar = useRef<HTMLElement>(null);

  // The org and cohort cards are a nicety: if this fails the shell still works.
  useEffect(() => {
    let current = true;
    fetchHome()
      .then((value) => current && setHome(value))
      .catch(() => undefined);
    return () => {
      current = false;
    };
  }, []);

  // Phone drawer: focus moves in on open, Tab stays inside it, Escape closes and
  // hands focus back to the menu button, and the page behind stops scrolling.
  useEffect(() => {
    if (!menuOpen) return;
    const drawer = sidebar.current;
    const focusable = () =>
      Array.from(drawer?.querySelectorAll<HTMLElement>('a[href], button') ?? []);
    focusable()[0]?.focus();
    const scroll = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setMenuOpen(false);
        menuButton.current?.focus();
        return;
      }
      if (event.key !== 'Tab') return;
      const items = focusable();
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = scroll;
    };
  }, [menuOpen]);

  async function handleSignOut() {
    await signOut();
    navigate('/signin', { replace: true });
  }

  const close = () => setMenuOpen(false);

  return (
    <div className="min-h-screen bg-page lg:flex">
      {menuOpen && (
        <button
          type="button"
          aria-label="Close menu"
          tabIndex={-1}
          className="fixed inset-0 z-20 bg-ink/40 lg:hidden"
          onClick={close}
        />
      )}

      <aside
        id="app-sidebar"
        ref={sidebar}
        className={`${
          menuOpen ? 'fixed flex' : 'hidden'
        } inset-y-0 left-0 z-30 w-[245px] flex-col gap-4 overflow-y-auto border-r border-line bg-surface py-5 lg:sticky lg:top-0 lg:flex lg:h-screen lg:shrink-0`}
      >
        <div className="px-5">
          <NavLink to="/" aria-label="Byline home" className="no-underline" onClick={close}>
            <BylineMark />
          </NavLink>
        </div>

        {home && (
          <div className="mx-3 rounded-lg border border-line p-3">
            <p className="text-[14px] font-semibold text-ink">{home.organization.name}</p>
            {home.cohort && <p className="mt-0.5 text-meta text-ink-meta">{home.cohort.name}</p>}
          </div>
        )}

        <nav aria-label="Main" className="flex flex-col gap-1 px-3">
          {LINKS.map((link) => (
            <NavLink key={link.to} to={link.to} end className={itemClass} onClick={close}>
              {link.icon}
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto flex flex-col gap-4">
          <CohortProgress home={home} />

          <div className="flex flex-col gap-1 px-3">
            <NavLink to="/me" className={itemClass} onClick={close}>
              <Icon>
                <circle cx="12" cy="8" r="3.5" />
                <path d="M5 20a7 7 0 0 1 14 0" />
              </Icon>
              Profile &amp; settings
            </NavLink>
            <button
              type="button"
              onClick={handleSignOut}
              className="flex h-11 items-center gap-3 rounded-lg px-3 text-left text-[14px] font-medium text-ink-body hover:bg-surface-recessed hover:text-ink"
            >
              <Icon>
                <path d="M10 5H5v14h5M14 8l4 4-4 4M18 12H9" />
              </Icon>
              Sign out
            </button>
          </div>

          <div className="mx-3 flex items-center gap-3 border-t border-line pt-4">
            <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-meta font-semibold text-primary-on">
              {initials(user.full_name)}
            </span>
            <span className="min-w-0">
              <span className="block truncate text-[14px] font-semibold text-ink">
                {user.full_name}
              </span>
              <span className="block text-meta text-ink-meta">{roleLabel(user.roles)}</span>
            </span>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-[55px] items-center justify-between border-b border-line bg-surface px-4 lg:h-[75px] lg:px-10">
          <button
            ref={menuButton}
            type="button"
            className="-ml-2 p-2 text-ink lg:hidden"
            aria-label="Menu"
            aria-controls="app-sidebar"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            <MenuIcon />
          </button>
          <NavLink to="/" aria-label="Byline home" className="no-underline lg:hidden">
            <BylineMark />
          </NavLink>
          <p className="hidden text-[14px] text-ink-meta lg:block">
            Workspace <span aria-hidden="true">›</span>{' '}
            <span className="font-semibold text-ink">{pageTitle(pathname)}</span>
          </p>
          <div className="flex items-center gap-3">
            <NavLink to="/updates" aria-label="Updates" className="p-2 text-ink">
              <BellIcon />
            </NavLink>
            <NavLink
              to="/me"
              aria-label={`${firstName(user.full_name)}, profile`}
              className="hidden h-[30px] w-[30px] items-center justify-center rounded-full bg-primary text-meta font-semibold text-primary-on no-underline lg:inline-flex"
            >
              {initials(user.full_name)}
            </NavLink>
          </div>
        </header>
        <Outlet context={user} />
      </div>
    </div>
  );
}
