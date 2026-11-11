// SCRUM-23: an assignment's late policy in words, as P12 shows it under "Late policy".
// The rules themselves live on the server (api/late_policy.py); this only describes them.
import { formatInstant } from './time';

export type LatePolicy = 'not_accepted' | 'accepted_full_points' | 'accepted_half_points';

// The fields the API sends with every assignment.
export type AssignmentLateRules = {
  due_at: string | null;
  late_policy: LatePolicy;
  late_cutoff_hours: number | null;
};

const ONE_HOUR_IN_MS = 60 * 60 * 1000;

function hours(count: number): string {
  return `${count} hour${count === 1 ? '' : 's'}`;
}

// For example: "Accepted up to 48 hours late at half points. After Sun 27 Sep, 11:59 PM it
// can no longer be submitted." The last moment is shown in the viewer's own timezone.
// Returns null when there is no due date, because nothing can be late.
export function describeLatePolicy(
  assignment: AssignmentLateRules,
  timeZone: string,
): string | null {
  const { due_at: dueAt, late_policy: policy, late_cutoff_hours: cutoffHours } = assignment;
  if (!dueAt) return null;
  if (policy === 'not_accepted') {
    return 'Late work is not accepted. It can no longer be submitted after the due date.';
  }

  const worth = policy === 'accepted_half_points' ? 'half points' : 'full points';
  if (cutoffHours === null) return `Late work is accepted at ${worth}, with no cutoff.`;

  const lastMomentToHandIn = new Date(new Date(dueAt).getTime() + cutoffHours * ONE_HOUR_IN_MS);
  const { date, time } = formatInstant(lastMomentToHandIn.toISOString(), timeZone);
  return (
    `Accepted up to ${hours(cutoffHours)} late at ${worth}. ` +
    `After ${date}, ${time} it can no longer be submitted.`
  );
}
