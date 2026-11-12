import { describe, expect, test } from 'vitest';
import { cohortProgress, pageTitle, roleLabel } from './shell';

const cohort = { name: 'Cohort 8', starts_on: '2026-10-05', ends_on: '2026-12-25' }; // 12 weeks

describe('cohortProgress', () => {
  test('shows the week and a bar while the cohort runs', () => {
    // Monday 26 Oct is the start of week 4.
    expect(cohortProgress(cohort, 'UTC', new Date('2026-10-26T12:00:00Z'))).toEqual({
      label: 'Week 4 of 12',
      percent: 33,
    });
  });

  test('says when the cohort starts if it has not begun', () => {
    expect(cohortProgress(cohort, 'UTC', new Date('2026-10-01T12:00:00Z'))).toEqual({
      label: 'Starts Mon 5 Oct',
      percent: 0,
    });
  });

  test('says complete once the last week has passed', () => {
    expect(cohortProgress(cohort, 'UTC', new Date('2027-01-20T12:00:00Z'))).toEqual({
      label: 'Cohort complete',
      percent: 100,
    });
  });

  test('has no bar when the end date is missing', () => {
    const open = { ...cohort, ends_on: null };
    expect(cohortProgress(open, 'UTC', new Date('2026-10-26T12:00:00Z'))).toEqual({
      label: 'Week 4',
      percent: null,
    });
  });

  test('shows nothing without a cohort or start date', () => {
    expect(cohortProgress(null, 'UTC')).toBeNull();
    expect(cohortProgress({ ...cohort, starts_on: null }, 'UTC')).toBeNull();
  });
});

describe('roleLabel', () => {
  test('picks the most senior role', () => {
    expect(roleLabel(['member'])).toBe('Intern');
    expect(roleLabel(['member', 'supervisor'])).toBe('Supervisor');
    expect(roleLabel(['supervisor', 'admin'])).toBe('Admin');
    expect(roleLabel([])).toBe('Intern');
  });
});

describe('pageTitle', () => {
  test('names the page from its address', () => {
    expect(pageTitle('/')).toBe('My work');
    expect(pageTitle('/byline')).toBe('My byline');
    expect(pageTitle('/updates')).toBe('Updates');
    expect(pageTitle('/me')).toBe('Profile & settings');
    expect(pageTitle('/s/42')).toBe('Submission');
    expect(pageTitle('/anything-else')).toBe('Byline');
  });
});
