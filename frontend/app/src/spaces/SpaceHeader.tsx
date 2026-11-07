import { type ReactNode } from 'react';
import { Icon } from '../shared/Icon';
import { PageHeader } from '../shared/PageHeader';
import { PageTabs } from '../shared/PageTabs';

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
    <PageHeader
      groupClassName="work-space-header"
      heading={heading}
      actions={actions}
      navigation={
        navigationContent ??
        (navigation ? (
          <PageTabs className="work-tabs--views" label="Widoki przestrzeni">
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
          </PageTabs>
        ) : null)
      }
    />
  );
}
