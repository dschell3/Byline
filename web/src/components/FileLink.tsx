import { useState } from 'react';
import { fileSize } from '../lib/assignment';
import { downloadUrl } from '../lib/files';

// SCRUM-83: the download URL is short-lived, so it is fetched on the click. The API sends the
// file as an attachment, so the browser saves it without leaving this page.

type Props = { fileId: number; name: string; sizeBytes: number };

export function FileLink({ fileId, name, sizeBytes }: Props) {
  const [state, setState] = useState<'idle' | 'fetching' | 'refused'>('idle');

  async function open() {
    if (state === 'fetching') return;
    setState('fetching');
    const url = await downloadUrl(fileId);
    if (url) {
      setState('idle');
      window.location.assign(url);
    } else {
      setState('refused');
    }
  }

  return (
    <span className="inline-flex flex-wrap items-baseline gap-x-2">
      <button
        type="button"
        onClick={() => void open()}
        aria-busy={state === 'fetching' || undefined}
        className="m-0 border-0 bg-transparent p-0 text-left text-body text-link underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
      >
        {name}
      </button>
      <span className="text-meta text-ink-meta">{fileSize(sizeBytes)}</span>
      {state === 'fetching' && <span className="text-meta text-ink-meta">Opening…</span>}
      {state === 'refused' && (
        <span role="alert" className="text-meta text-status-overdue-text">
          Could not open this file. Reload and try again.
        </span>
      )}
    </span>
  );
}
