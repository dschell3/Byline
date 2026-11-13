import { describe, expect, test } from 'vitest';
import { describeLatePolicy, type AssignmentLateRules } from './latePolicy';

// Due Fri 25 Sep 2026, 11:59 PM in India (18:29 UTC).
const DUE_IN_INDIA = '2026-09-25T18:29:00Z';

function assignment(rules: Partial<AssignmentLateRules>): AssignmentLateRules {
  return {
    due_at: DUE_IN_INDIA,
    late_policy: 'accepted_full_points',
    late_cutoff_hours: null,
    ...rules,
  };
}

describe('describeLatePolicy', () => {
  test('writes the Figma sentence for half points up to 48 hours late', () => {
    const halfPointsFor48Hours = assignment({
      late_policy: 'accepted_half_points',
      late_cutoff_hours: 48,
    });
    expect(describeLatePolicy(halfPointsFor48Hours, 'Asia/Kolkata')).toBe(
      'Accepted up to 48 hours late at half points. After Sun 27 Sep, 11:59 PM it can no longer be submitted.',
    );
  });

  test('shows the last moment in the viewer’s own timezone', () => {
    const halfPointsFor48Hours = assignment({
      late_policy: 'accepted_half_points',
      late_cutoff_hours: 48,
    });
    expect(describeLatePolicy(halfPointsFor48Hours, 'America/Los_Angeles')).toBe(
      'Accepted up to 48 hours late at half points. After Sun 27 Sep, 11:29 AM it can no longer be submitted.',
    );
  });

  test('says when late work is not accepted at all', () => {
    expect(describeLatePolicy(assignment({ late_policy: 'not_accepted' }), 'UTC')).toBe(
      'Late work is not accepted. It can no longer be submitted after the due date.',
    );
  });

  test('says when late work is accepted with no cutoff', () => {
    expect(describeLatePolicy(assignment({ late_policy: 'accepted_full_points' }), 'UTC')).toBe(
      'Late work is accepted at full points, with no cutoff.',
    );
  });

  test('says "1 hour", not "1 hours"', () => {
    const oneHourGrace = assignment({ late_cutoff_hours: 1 });
    expect(describeLatePolicy(oneHourGrace, 'UTC')).toContain('up to 1 hour late at full points');
  });

  test('says nothing when there is no due date to be late for', () => {
    expect(describeLatePolicy(assignment({ due_at: null }), 'UTC')).toBeNull();
  });
});
