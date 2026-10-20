import { type ReactNode } from 'react';
import { Icon } from '../shared/Icon';

export function SpaceHeader({
  heading,
  actions,
  navigation,
  currentView,
}: {
  heading: ReactNode;
  actions: ReactNode;
  navigation: { key: string; label: string; icon: string; url: string }[];
  currentView: string;
}) {
  return (
    <header className="work-space-header">
      <div className="tasks-topbar tasks-topbar--directory tasks-topbar--project-directory">
        <div className="tasks-titlebar-left">{heading}</div>
        <div className="tasks-titlebar-actions">{actions}</div>
      </div>
      <nav
        className="notifications-tabs work-tabs work-tabs--views"
        aria-label="Widoki przestrzeni"
      >
        {navigation.map((nav) => (
          <a
            key={nav.key}
            href={nav.url}
            aria-current={currentView === nav.key ? 'page' : undefined}
          >
            <Icon name={nav.icon} />
            {nav.label}
          </a>
        ))}
      </nav>
    </header>
  );
}
