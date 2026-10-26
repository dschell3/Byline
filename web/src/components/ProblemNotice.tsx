// The red notice under a form (P01 "Email or password is not right"), shared by the public pages.
export type Problem = { title: string; detail: string };

function WarningIcon() {
  return (
    <svg
      width="19"
      height="19"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="mt-px shrink-0 text-status-overdue-text"
    >
      <path d="M12 3 2.5 20h19L12 3z" />
      <line x1="12" y1="10" x2="12" y2="14" />
      <circle cx="12" cy="17" r=".6" fill="currentColor" />
    </svg>
  );
}

export function ProblemNotice({ problem }: { problem: Problem }) {
  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-xl border border-status-overdue-text/20 bg-status-overdue-fill px-[17px] py-[15px]"
    >
      <WarningIcon />
      <div className="flex flex-col gap-[5px]">
        <p className="m-0 text-[14px] font-semibold text-status-overdue-text">{problem.title}</p>
        <p className="m-0 text-[13px] leading-5 text-ink-body">{problem.detail}</p>
      </div>
    </div>
  );
}
