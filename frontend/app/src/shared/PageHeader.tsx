import type { ReactNode } from 'react';

export function PageHeader({
  heading,
  actions,
  navigation,
  label,
  className = '',
  groupClassName = '',
  as: Element = 'header',
}: {
  heading: ReactNode;
  actions?: ReactNode;
  navigation?: ReactNode;
  label?: string;
  className?: string;
  groupClassName?: string;
  as?: 'header' | 'div';
}) {
  const Titlebar = navigation ? 'div' : Element;
  const titlebar = (
    <Titlebar
      className={`tasks-topbar tasks-topbar--directory tasks-topbar--project-directory app-page-header ${className}`}
      aria-label={label}
    >
      <div className="tasks-titlebar-left">{heading}</div>
      {actions ? <div className="tasks-titlebar-actions">{actions}</div> : null}
    </Titlebar>
  );
  return navigation ? (
    <Element className={`app-page-header-group ${groupClassName}`}>
      {titlebar}
      {navigation}
    </Element>
  ) : (
    titlebar
  );
}
