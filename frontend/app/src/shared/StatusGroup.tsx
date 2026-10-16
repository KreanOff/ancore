import { type DragEventHandler, type ReactNode, useState } from 'react';
import { Icon } from './Icon';
export function StatusGroup({
  label,
  category,
  icon = 'layers',
  count,
  children,
  className = '',
  details,
  labelSuffix,
  onDragOver,
  onDrop,
}: {
  label: string;
  category?: string;
  icon?: string;
  count: number;
  children: ReactNode;
  className?: string;
  details?: ReactNode;
  labelSuffix?: string;
  onDragOver?: DragEventHandler<HTMLElement>;
  onDrop?: DragEventHandler<HTMLElement>;
}) {
  const [open, setOpen] = useState(true);
  return (
    <section
      className={`tasks-issue-group tasks-status-block ${className}`}
      aria-label={label}
      onDragOver={onDragOver}
      onDrop={onDrop}
    >
      <header
        className={`tasks-issue-group-header ${category ? `tasks-status-block-header tasks-status-block-header--${category}` : ''}`}
      >
        <button
          type="button"
          className="tasks-group-caret"
          aria-label={`${open ? 'Zwiń' : 'Rozwiń'} ${category ? 'status ' : ''}${label}`}
          aria-expanded={open}
          onClick={() => setOpen(!open)}
        >
          <Icon name="chevron-down" />
        </button>
        {category ? (
          <span className={`status-indicator status-${category}`}>
            {label}
            {labelSuffix ? ` · ${labelSuffix}` : ''}
          </span>
        ) : (
          <span className="tasks-issue-group-label">
            <Icon name={icon} />
            {label}
            {labelSuffix ? ` · ${labelSuffix}` : ''}
          </span>
        )}
        {details}
        <span className="tasks-rail-count">{count}</span>
      </header>
      {open ? children : null}
    </section>
  );
}
