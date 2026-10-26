import { useState } from 'react';
import { NavLink, Outlet, useNavigate, useOutletContext } from 'react-router';
import { signOut, type CurrentUser } from '../lib/auth';
import { firstName, initials } from '../lib/home';
import { BylineMark } from './BylineMark';

// The signed-in shell from the Figma app chrome (P11 header; X11 on phones).
// Sits inside RequireAuth, so the signed-in person is always known here.

const LINKS = [
  { to: '/', label: 'My work' },
  { to: '/byline', label: 'My byline' },
  { to: '/updates', label: 'Updates' },
];

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

function ChevronIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="m6 9 6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export default function AppLayout() {
  const user = useOutletContext<CurrentUser>();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  async function handleSignOut() {
    await signOut();
    navigate('/signin', { replace: true });
  }

  const desktopLink = ({ isActive }: { isActive: boolean }) =>
    `relative inline-flex h-16 items-center text-[14px] leading-5 ${
      isActive
        ? 'font-semibold text-ink after:absolute after:inset-x-0 after:bottom-0 after:h-0.5 after:rounded-sm after:bg-primary'
        : 'font-medium text-ink-body hover:text-ink'
    }`;

  return (
    <div className="flex min-h-screen flex-col bg-page">
      <header className="relative z-10 border-b border-line bg-surface">
        <div className="flex h-[55px] items-center justify-between px-4 lg:h-16 lg:px-10">
          <button
            type="button"
            className="-ml-2 p-2 text-ink lg:hidden"
            aria-label="Menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            <MenuIcon />
          </button>
          <NavLink to="/" aria-label="Byline home" className="no-underline">
            <BylineMark />
          </NavLink>
          <NavLink to="/updates" aria-label="Updates" className="-mr-2 p-2 text-ink lg:hidden">
            <BellIcon />
          </NavLink>

          <nav aria-label="Main" className="hidden items-center gap-[22px] lg:flex">
            {LINKS.map((link) => (
              <NavLink key={link.to} to={link.to} end className={desktopLink}>
                {link.label}
              </NavLink>
            ))}
            <span aria-hidden="true" className="h-6 w-px bg-line" />
            <div className="relative">
              <button
                type="button"
                className="flex items-center gap-2 text-ink-body"
                aria-expanded={menuOpen}
                onClick={() => setMenuOpen((open) => !open)}
              >
                <span className="inline-flex h-[30px] w-[30px] items-center justify-center rounded-full bg-primary text-meta font-semibold text-primary-on">
                  {initials(user.full_name)}
                </span>
                <span className="text-meta">{firstName(user.full_name)}</span>
                <ChevronIcon />
              </button>
              {menuOpen && (
                <div className="absolute right-0 top-full mt-2 w-44 rounded-xl border border-line bg-surface p-1 shadow-lg">
                  <button
                    type="button"
                    onClick={handleSignOut}
                    className="w-full rounded-md px-3 py-2 text-left text-[14px] font-medium text-ink hover:bg-surface-recessed"
                  >
                    Sign out
                  </button>
                </div>
              )}
            </div>
          </nav>
        </div>

        {menuOpen && (
          <nav aria-label="Main" className="border-t border-line px-4 py-2 lg:hidden">
            {LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end
                onClick={() => setMenuOpen(false)}
                className={({ isActive }) =>
                  `block py-3 text-[15px] ${isActive ? 'font-semibold text-ink' : 'font-medium text-ink-body'}`
                }
              >
                {link.label}
              </NavLink>
            ))}
            <button
              type="button"
              onClick={handleSignOut}
              className="block w-full py-3 text-left text-[15px] font-medium text-ink-body"
            >
              Sign out
            </button>
          </nav>
        )}
      </header>
      <Outlet context={user} />
    </div>
  );
}
