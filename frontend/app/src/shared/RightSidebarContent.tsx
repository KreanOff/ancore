import type { HTMLAttributes, ReactNode } from 'react';
import { createPortal } from 'react-dom';

export function openRightSidebar() {
  document
    .querySelector<HTMLButtonElement>('[data-right-sidebar-toggle][aria-expanded="false"]')
    ?.click();
}

// The host lives outside both React roots, so initial shell mounting cannot replace it.
export function RightSidebarContent({ children }: { children: ReactNode }) {
  const host =
    typeof document === 'undefined' ? null : document.getElementById('app-right-sidebar-content');
  return host ? createPortal(children, host) : children;
}

export function RightSidebarNavigation({
  title,
  action,
  children,
  footer,
  busy,
  className = '',
  ...attributes
}: HTMLAttributes<HTMLElement> & {
  title: string;
  action?: ReactNode;
  footer?: ReactNode;
  busy?: boolean;
}) {
  return (
    <section {...attributes} className={`app-sidebar-navigation ${className}`.trimEnd()}>
      <header className="app-sidebar-navigation__header">
        <h2>{title}</h2>
        {action}
      </header>
      <nav className="app-sidebar-navigation__nav" aria-label={title} aria-busy={busy}>
        <ul className="app-sidebar-navigation__list">{children}</ul>
        {footer}
      </nav>
    </section>
  );
}
