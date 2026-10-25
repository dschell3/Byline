import { useEffect, useState } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router';
import { fetchCurrentUser, signInPath, type CurrentUser } from '../lib/auth';

type State = { status: 'checking' } | { status: 'in'; user: CurrentUser } | { status: 'out' };

// SCRUM-13: wrap signed-in routes in this. It asks the API on every navigation, so an expired
// session sends the person to sign-in with where they were going kept in ?next=.
// Child routes read the signed-in person with useOutletContext<CurrentUser>().
export default function RequireAuth() {
  const location = useLocation();
  const [state, setState] = useState<State>({ status: 'checking' });
  const [unreachable, setUnreachable] = useState(false);

  useEffect(() => {
    let current = true;
    fetchCurrentUser()
      .then((user) => {
        if (!current) return;
        setUnreachable(false);
        setState(user ? { status: 'in', user } : { status: 'out' });
      })
      .catch(() => {
        if (current) setUnreachable(true);
      });
    return () => {
      current = false;
    };
  }, [location.key]);

  if (unreachable) {
    return (
      <p role="alert" className="p-8 text-body text-ink">
        Byline could not be reached. Check your connection and reload the page.
      </p>
    );
  }
  if (state.status === 'out') {
    return (
      <Navigate to={signInPath(`${location.pathname}${location.search}${location.hash}`)} replace />
    );
  }
  if (state.status === 'checking') return null;
  return <Outlet context={state.user} />;
}
