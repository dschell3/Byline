import { formatInstant } from '../lib/time';

// One instant as the viewer reads it: "Sat 7 Nov, 3:23 PM", with the long form as a tooltip.
// Shared by the submission page (P14, SCRUM-22) and the resubmit screen (P13, SCRUM-21).
export function When({ iso, timeZone }: { iso: string; timeZone: string }) {
  const at = formatInstant(iso, timeZone);
  return (
    <time dateTime={iso} title={at.full}>
      {at.date}, {at.time}
    </time>
  );
}
