import type { ReactNode } from 'react';

export function ViewToolbar({
  children,
  actions,
  className = '',
}: {
  children: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <div className={`tasks-filterbar tasks-filterbar--directory work-view-toolbar ${className}`}>
      <div className="work-view-toolbar-controls">{children}</div>
      {actions ? <div className="work-view-toolbar-actions">{actions}</div> : null}
    </div>
  );
}
