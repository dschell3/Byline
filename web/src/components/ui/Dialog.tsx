import { useEffect, useId, useRef, type ReactNode } from 'react';

// SCRUM-72: modal dialog from the Figma screens (e.g. "Create twelve weekly assignments").
export type DialogProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  // eslint-disable-next-line react/require-default-props
  actions?: ReactNode;
};

export function Dialog({ open, onClose, title, children, actions }: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      onClose={onClose}
      className="w-[calc(100%-2rem)] max-w-md rounded-lg border border-line bg-surface p-6 text-ink-body shadow-xl backdrop:bg-black/40"
    >
      <h2 id={titleId} className="font-sans text-card-title text-ink">
        {title}
      </h2>
      <div className="mt-2 text-body">{children}</div>
      {actions && <div className="mt-6 flex justify-end gap-3">{actions}</div>}
    </dialog>
  );
}
