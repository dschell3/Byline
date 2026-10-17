import type { ReactNode } from 'react';

// SCRUM-72: table from the Figma foundations page. Recessed header, hairline rows.
// The no-unused-vars disables are for the base JS rule, which misreads parameter names in TypeScript types.
export type Column<T> = {
  key: string;
  header: string;
  // eslint-disable-next-line no-unused-vars
  render: (row: T) => ReactNode;
};

export type TableProps<T> = {
  columns: Column<T>[];
  rows: T[];
  // eslint-disable-next-line no-unused-vars
  getRowKey: (row: T) => string;
  // eslint-disable-next-line react/require-default-props
  caption?: string;
};

export function Table<T>({ columns, rows, getRowKey, caption }: TableProps<T>) {
  return (
    <div className="overflow-x-auto rounded-lg border border-line bg-surface">
      <table className="w-full text-left text-body">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead className="bg-surface-recessed">
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                scope="col"
                className="px-4 py-3 text-meta font-semibold uppercase tracking-wider text-ink-meta"
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={getRowKey(row)} className="border-t border-line">
              {columns.map((c) => (
                <td key={c.key} className="px-4 py-3 align-middle text-ink">
                  {c.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
