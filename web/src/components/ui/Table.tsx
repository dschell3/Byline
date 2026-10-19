import { useState, type ReactNode } from 'react';

// SCRUM-72: table from the Figma foundations page. Recessed header, hairline rows.
// Columns with a sortValue get a clickable header; an empty table shows a message instead of nothing.
export type Column<T> = {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  sortValue?: (row: T) => string | number;
};

export type TableProps<T> = {
  columns: Column<T>[];
  rows: T[];
  getRowKey: (row: T) => string;
  caption?: string;
  emptyMessage?: string;
};

type Sort = { key: string; dir: 'asc' | 'desc' };

export function Table<T>({
  columns,
  rows,
  getRowKey,
  caption = '',
  emptyMessage = 'Nothing here yet.',
}: TableProps<T>) {
  const [sort, setSort] = useState<Sort | null>(null);

  function toggleSort(key: string) {
    setSort((current) => {
      if (!current || current.key !== key) return { key, dir: 'asc' };
      return { key, dir: current.dir === 'asc' ? 'desc' : 'asc' };
    });
  }

  let sortedRows = rows;
  const getValue = sort ? columns.find((c) => c.key === sort.key)?.sortValue : undefined;
  if (sort && getValue) {
    const factor = sort.dir === 'asc' ? 1 : -1;
    sortedRows = [...rows].sort((a, b) => {
      const av = getValue(a);
      const bv = getValue(b);
      const result =
        typeof av === 'number' && typeof bv === 'number'
          ? av - bv
          : String(av).localeCompare(String(bv));
      return result * factor;
    });
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-line bg-surface">
      <table className="w-full text-left text-body">
        {caption ? <caption className="sr-only">{caption}</caption> : null}
        <thead className="bg-surface-recessed">
          <tr>
            {columns.map((c) => {
              const headerClass = 'text-meta font-semibold uppercase tracking-wider text-ink-meta';
              if (!c.sortValue) {
                return (
                  <th key={c.key} scope="col" className={`px-4 py-3 ${headerClass}`}>
                    {c.header}
                  </th>
                );
              }
              const isSorted = sort?.key === c.key;
              let ariaSort: 'ascending' | 'descending' | 'none' = 'none';
              let arrow = '↕';
              if (isSorted && sort?.dir === 'asc') {
                ariaSort = 'ascending';
                arrow = '↑';
              } else if (isSorted) {
                ariaSort = 'descending';
                arrow = '↓';
              }
              return (
                <th key={c.key} scope="col" aria-sort={ariaSort} className="px-4 py-3">
                  <button
                    type="button"
                    onClick={() => toggleSort(c.key)}
                    className={`inline-flex items-center gap-1 rounded-sm hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary ${headerClass}`}
                  >
                    {c.header}
                    <span aria-hidden="true">{arrow}</span>
                  </button>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sortedRows.length === 0 ? (
            <tr className="border-t border-line">
              <td colSpan={columns.length} className="px-4 py-10 text-center text-ink-meta">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            sortedRows.map((row) => (
              <tr key={getRowKey(row)} className="border-t border-line">
                {columns.map((c) => (
                  <td key={c.key} className="px-4 py-3 align-middle text-ink">
                    {c.render(row)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
