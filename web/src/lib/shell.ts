// SCRUM-82: wording for the signed-in sidebar shell.
import { cohortStage, startDate, todayIn, type Home } from './home';
import { cohortWeeks } from './invite';

// Where the cohort is, for the "Cohort progress" block. percent is null when there is no bar to draw.
export type CohortProgress = { label: string; percent: number | null };

export function cohortProgress(
  cohort: Home['cohort'],
  timeZone: string,
  now: Date = new Date(),
): CohortProgress | null {
  if (!cohort?.starts_on) return null;
  const stage = cohortStage(cohort.starts_on, todayIn(timeZone, now));
  if (stage.kind === 'upcoming') {
    return { label: `Starts ${startDate(cohort.starts_on, true)}`, percent: 0 };
  }
  const week = stage.week ?? 1;
  const total = cohortWeeks(cohort.starts_on, cohort.ends_on);
  if (!total) return { label: `Week ${week}`, percent: null };
  if (week > total) return { label: 'Cohort complete', percent: 100 };
  return { label: `Week ${week} of ${total}`, percent: Math.round((week / total) * 100) };
}

// The one role to show under someone's name: the most senior they hold.
export function roleLabel(roles: string[]): string {
  if (roles.includes('admin')) return 'Admin';
  if (roles.includes('supervisor')) return 'Supervisor';
  return 'Intern';
}

// The page name for the top bar, from the address.
export function pageTitle(pathname: string): string {
  if (pathname === '/') return 'My work';
  if (pathname.startsWith('/byline')) return 'My byline';
  if (pathname.startsWith('/updates')) return 'Updates';
  if (pathname.startsWith('/s/')) return 'Submission';
  if (pathname.startsWith('/me')) return 'Profile & settings';
  return 'Byline';
}
