import { type DragEventHandler, type ReactNode, useState } from 'react';
import { Icon } from './Icon';
import { statusHeaderStyle } from './status-color';
export function StatusGroup({
  label,
  category,
  color,
  icon = 'layers',
  count,
  children,
  className = '',
  headerClassName = '',
  details,
  labelSuffix,
  onDragOver,
  onDrop,
  dropGroup,
}: {
  label: string;
  category?: string;
  color?: string;
  icon?: string | null;
  count: number;
  children: ReactNode;
  className?: string;
  headerClassName?: string;
  details?: ReactNode;
  labelSuffix?: string;
  onDragOver?: DragEventHandler<HTMLElement>;
  onDrop?: DragEventHandler<HTMLElement>;
  dropGroup?: string;
}) {
  const [open, setOpen] = useState(true);
  return (
    <section
      className={`tasks-issue-group tasks-status-block ${className}`}
      aria-label={label}
      data-work-drop-group={dropGroup}
      onDragOver={onDragOver}
      onDrop={onDrop}
    >
      <header
        style={statusHeaderStyle(color)}
        className={`tasks-issue-group-header ${category ? `tasks-status-block-header tasks-status-block-header--${category}` : ''}${headerClassName ? ` ${headerClassName}` : ''}`}
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
          <span className="tasks-issue-group-label" title={label}>
            {icon ? <Icon name={icon} /> : null}
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
