import { type ReactNode } from 'react';
import { Icon } from '../shared/Icon';

export function SpaceHeader({
  heading,
  actions,
  navigation,
  navigationContent,
  currentView,
  onSettings,
}: {
  heading: ReactNode;
  actions: ReactNode;
  navigation?: { key: string; label: string; icon: string; url: string }[];
  navigationContent?: ReactNode;
  currentView?: string;
  onSettings?: () => void;
}) {
  return (
    <header className="work-space-header">
      <div className="tasks-topbar tasks-topbar--directory tasks-topbar--project-directory">
        <div className="tasks-titlebar-left">{heading}</div>
        <div className="tasks-titlebar-actions">{actions}</div>
      </div>
      {navigationContent ??
        (navigation ? (
          <nav
            className="notifications-tabs work-tabs work-tabs--views"
            aria-label="Widoki przestrzeni"
          >
            {navigation.map((nav) => (
              <a
                key={nav.key}
                href={nav.url}
                onClick={
                  nav.key === 'settings' && onSettings
                    ? (event) => {
                        if (
                          event.button ||
                          event.metaKey ||
                          event.ctrlKey ||
                          event.shiftKey ||
                          event.altKey
                        )
                          return;
                        event.preventDefault();
                        onSettings();
                      }
                    : undefined
                }
                aria-current={currentView === nav.key ? 'page' : undefined}
              >
                <Icon name={nav.icon} />
                {nav.label}
              </a>
            ))}
          </nav>
        ) : null)}
    </header>
  );
}
