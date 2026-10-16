import { type ReactNode, useState } from 'react';
import { Icon } from './Icon';
export function StatusGroup({
  label,
  category,
  icon = 'layers',
  count,
  children,
  className = '',
  details,
}: {
  label: string;
  category?: string;
  icon?: string;
  count: number;
  children: ReactNode;
  className?: string;
  details?: ReactNode;
}) {
  const [open, setOpen] = useState(true);
  return (
    <section className={`tasks-issue-group tasks-status-block ${className}`}>
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
          <Icon name={open ? 'chevron-down' : 'chevron-right'} />
        </button>
        {category ? (
          <span className={`status-indicator status-${category}`}>{label}</span>
        ) : (
          <span className="tasks-issue-group-label">
            <Icon name={icon} />
            {label}
          </span>
        )}
        <span className="tasks-rail-count">{count}</span>
        {details}
      </header>
      {open ? children : null}
    </section>
  );
}
