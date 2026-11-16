// SCRUM-20: tell "too big" apart from "connection lost", and always say the text is still there.
import type { SubmissionKind } from './draft';

export const MAX_TEXT_CHARS = 20000;

export type SubmitFailure = 'too_large' | 'connection_lost' | 'signed_out' | 'server' | 'rejected';

// A Response means the request got there; anything thrown (fetch rejects, a killed request) means it did not.
export function classifyFailure(result: unknown): SubmitFailure {
  if (typeof Response !== 'undefined' && result instanceof Response) {
    if (result.status === 413) return 'too_large';
    if (result.status === 401) return 'signed_out';
    if (result.status >= 500) return 'server';
    return 'rejected';
  }
  return 'connection_lost';
}

export const FAILURE_MESSAGE: Record<SubmitFailure, string> = {
  too_large: 'That is too long to send. Shorten it and try again. What you typed is still here.',
  connection_lost:
    'Connection lost, so nothing was sent. What you typed is saved on this device. Try again when you are back online.',
  signed_out: 'You were signed out. Sign in again and your draft will be here.',
  server: 'Something went wrong on our side. What you typed is still here. Try again in a moment.',
  rejected: 'That could not be submitted. What you typed is still here.',
};

export function isTooLong(kind: SubmissionKind, content: string): boolean {
  return kind === 'text' && content.length > MAX_TEXT_CHARS;
}
