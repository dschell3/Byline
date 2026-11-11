import { Card } from './ui/Card';
import { Table, type Column } from './ui/Table';
import { When } from './When';
import { decisionLabel, scoreTotal, type Review, type Score } from '../lib/submission';

// One review: who decided what and when, the written reason, and the score per criterion.
// Used on P14 (SCRUM-22) and above the resubmit form on P13 (SCRUM-21).
const scoreColumns: Column<Score>[] = [
  { key: 'criterion', header: 'Criterion', render: (s) => s.text },
  {
    key: 'score',
    header: 'Score',
    render: (s) => (
      <span className="whitespace-nowrap font-semibold text-ink">
        {s.score} / {s.max_points}
      </span>
    ),
  },
  { key: 'note', header: 'Note', render: (s) => s.note ?? '' },
];

export function ReviewCard({ review, timeZone }: { review: Review; timeZone: string }) {
  return (
    <Card className="!p-5">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
        <p className="m-0 text-card-title text-ink">{decisionLabel(review)}</p>
        <p className="m-0 text-meta text-ink-meta">
          <When iso={review.created_at} timeZone={timeZone} />
          {review.scores.length > 0 && ` · ${scoreTotal(review.scores)}`}
        </p>
      </div>
      {review.reason && (
        <p className="m-0 mt-3 whitespace-pre-line text-body text-ink-body">{review.reason}</p>
      )}
      {review.scores.length > 0 && (
        <div className="mt-4">
          <Table
            columns={scoreColumns}
            rows={review.scores}
            getRowKey={(s) => String(s.criterion_id)}
            caption="Scores against the assessment criteria"
          />
        </div>
      )}
    </Card>
  );
}
