import { lazy, Suspense, useEffect } from 'react';
import type { PageProps } from './shared/page';
const loaders: Record<string, () => Promise<{ default: React.ComponentType<PageProps> }>> = {
  calendar: () => import('./calendar/CalendarPage'),
  'for-you': () => import('./dashboard/ForYouPage'),
  settings: () => import('./dashboard/SettingsPage'),
  form: () => import('./forms/FormDialog'),
  'space-directory': () => import('./spaces/DirectoryPage'),
  'space-detail': () => import('./spaces/DetailPage'),
  'space-configuration': () => import('./spaces/ConfigurationPage'),
  'space-task': () => import('./tasks/TaskPage'),
  teams: () => import('./spaces/TeamsPage'),
  team: () => import('./spaces/TeamsPage'),
  'space-tags': () => import('./tags/TagsPage'),
  'filter-directory': () => import('./filters/DirectoryPage'),
  'filter-search': () => import('./filters/SearchPage'),
  'pulpit-directory': () => import('./pulpits/DirectoryPage'),
  'pulpit-detail': () => import('./pulpits/DetailPage'),
  'pulpit-edit': () => import('./pulpits/EditPage'),
  'workspace-directory': () => import('./workspaces/DirectoryPage'),
  'workspace-form': () => import('./forms/FormDialog'),
  'document-directory': () => import('./documents/DirectoryPage'),
  'office-text': () => import('./documents/TextPage'),
  'office-suite': () => import('./documents/SuitePage'),
  'account-auth': () => import('./accounts/AuthPage'),
  'account-workspace-picker': () => import('./accounts/WorkspacePickerPage'),
  'account-join': () => import('./workspaces/JoinPage'),
  'account-profile': () => import('./accounts/ProfilePage'),
};
const components = Object.fromEntries(
  Object.entries(loaders).map(([key, load]) => [key, lazy(load)]),
);
export async function preloadPage(type: string) {
  if (!loaders[type]) throw new Error('Nieobsługiwany ekran aplikacji.');
  await loaders[type]();
}
export default function PageApp(props: PageProps) {
  useEffect(() => {
    document.title = `${props.initial.title} | ancore`;
  }, [props.initial.title]);
  const Component = components[props.initial.type];
  if (!Component) throw new Error('Nieobsługiwany ekran aplikacji.');
  return (
    <Suspense
      fallback={
        <div role="status" className="tasks-empty-state">
          Wczytywanie…
        </div>
      }
    >
      <Component {...props} />
      {props.initial.read_only ? (
        <p className="workspace-read-only-hint" role="status">
          Gość · dostęp tylko do odczytu
        </p>
      ) : null}
    </Suspense>
  );
}
