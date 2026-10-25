import { Fragment, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { Icon } from '../shared/Icon';
import type { Collection, CollectionRow, ReturnContext, ShellData } from './navigation-types';
import { CollectionContents, CollectionGroup } from './Collections';
import { read, write } from './storage';
import { useFavorites } from './useFavorites';
import type { useShellLayout } from './useShellLayout';
const settingsCategory = () =>
  ['account', 'security'].includes(location.hash.slice(1))
    ? 'account'
    : location.hash === '#workspace'
      ? 'workspace'
      : 'all';
export default function Sidebar({
  data,
  api,
  token,
  context,
  layout,
  updateFavorites,
  openForm,
  star,
  starBusy,
  picker,
}: {
  data: ShellData;
  api: string;
  token: string;
  context: ReturnContext | null;
  layout: ReturnType<typeof useShellLayout>;
  updateFavorites: Parameters<typeof useFavorites>[3];
  openForm: (url: string) => void;
  star: (row: CollectionRow) => void;
  starBusy: boolean;
  picker: (group: Collection, anchor: HTMLElement) => void;
}) {
  const [groups, setGroups] = useState(() => {
    const values = read<unknown>('ancoreSidebarCollapsedGroups', []);
    return new Set(Array.isArray(values) ? values.filter((item) => typeof item === 'string') : []);
  });
  const [favoritesCollapsed, setFavoritesCollapsed] = useState(
    () => read<boolean>('ancoreSidebarFavoritesCollapsed', false) === true,
  );
  const [flyout, setFlyout] = useState<{
    group: Collection;
    anchor: HTMLElement;
    keyboard: boolean;
  }>();
  const [category, setCategory] = useState(settingsCategory);
  const favorites = useFavorites(data, api, token, updateFavorites);
  const actions = {
    openForm: (url: string) => {
      setFlyout(undefined);
      openForm(url);
    },
    star,
    busy: starBusy,
    picker: (group: Collection, anchor: HTMLElement) => {
      const stable = document.querySelector<HTMLElement>(
        `[data-sidebar-group="${group.key}"] [data-sidebar-group-toggle]`,
      );
      setFlyout(undefined);
      picker(group, anchor.closest('#sidebar-collapsed-flyout') && stable ? stable : anchor);
    },
  };
  useEffect(() => {
    const controller = new AbortController(),
      { signal } = controller;
    const close = () => setFlyout(undefined);
    const sync = () => setCategory(settingsCategory());
    window.addEventListener('hashchange', sync, { signal });
    window.addEventListener('popstate', sync, { signal });
    window.addEventListener('ancore:settings-category', sync, { signal });
    for (const name of [
      'ancore:global-search-open',
      'ancore:notifications-open',
      'ancore:sidebar-toggle',
      'ancore:workspace-menu-open',
      'ancore:sidebar-picker-open',
    ])
      window.addEventListener(name, close, { signal });
    document.addEventListener(
      'ancore:content-unloading',
      () => {
        close();
        layout.close();
      },
      { signal },
    );
    document.addEventListener('ancore:content-loaded', sync, { signal });
    return () => controller.abort();
  }, []);
  useEffect(() => {
    setFlyout(undefined);
  }, [data.mode, layout.collapsed, layout.mobile]);
  useEffect(() => {
    if (!layout.opened) return;
    const close = () => layout.close();
    for (const name of [
      'ancore:global-search-open',
      'ancore:notifications-open',
      'ancore:workspace-menu-open',
    ])
      window.addEventListener(name, close);
    return () => {
      for (const name of [
        'ancore:global-search-open',
        'ancore:notifications-open',
        'ancore:workspace-menu-open',
      ])
        window.removeEventListener(name, close);
    };
  }, [layout.opened]);
  const mainLink = (key: string) => {
    const item = data.links[key];
    if (!item) return null;
    return (
      <Fragment key={key}>
        <a
          href={item.url}
          className={`nav-link sidebar-primary-link sidebar-primary-link--standalone${item.is_active ? ' active' : ''}`}
          aria-label={item.label}
          aria-current={item.is_active ? 'page' : undefined}
          title={item.label}
          data-sidebar-source-item={key}
          draggable={!favorites.busy}
        >
          <Icon name={item.icon} className="nav-icon" />
          <span className="nav-label">{item.label}</span>
        </a>
        <button
          type="button"
          className="u-sr-only"
          disabled={favorites.busy}
          onClick={() =>
            void favorites.toggle(key, !data.favorites.some((item) => item.key === key))
          }
        >
          {data.favorites.some((item) => item.key === key)
            ? `Usuń ${item.label} z Favorites`
            : `Dodaj ${item.label} do Favorites`}
        </button>
      </Fragment>
    );
  };
  const expanded = layout.collapsed || !favoritesCollapsed;
  const returnLink = (fallback: string, label: string) => (
    <a
      href={context?.url || fallback}
      className="nav-link sidebar-primary-link sidebar-primary-link--standalone"
      data-management-return={data.mode}
      data-default-return-url={fallback}
      title={context?.label || label}
    >
      <Icon name="arrow-left" className="nav-icon" />
      <span className="nav-label">{context?.label || label}</span>
    </a>
  );
  let management: ReactNode = null;
  if (data.mode === 'settings')
    management = (
      <>
        <h2 className="sidebar-menu-section-title">Ustawienia Ancore</h2>
        <a
          href={data.links.spaces?.url || data.links['for-you'].url}
          className="nav-link sidebar-primary-link sidebar-primary-link--standalone"
        >
          <Icon name="arrow-left" className="nav-icon" />
          <span className="nav-label">Wróć do przestrzeni</span>
        </a>
        {[
          ['all', 'Ogólne', 'settings'],
          ['account', 'Konto i dostęp', 'user-round'],
          ['workspace', 'Workspace', 'folder'],
        ].map(([key, label, icon]) => (
          <a
            key={key}
            href={data.settings_url + (key === 'all' ? '' : `#${key}`)}
            className={`nav-link sidebar-primary-link sidebar-primary-link--standalone${category === key ? ' active' : ''}`}
            data-settings-category={key}
            aria-current={category === key ? 'page' : undefined}
            title={label}
          >
            <Icon name={icon} className="nav-icon" />
            <span className="nav-label">{label}</span>
          </a>
        ))}
      </>
    );
  else if (data.mode === 'workplaces')
    management = (
      <>
        <h2 className="sidebar-menu-section-title">Zarządzanie Workspace</h2>
        {returnLink(data.default_pulpit_url, 'Wróć do Workspace')}
        <a
          href={data.workplaces_url}
          className="nav-link sidebar-primary-link sidebar-primary-link--standalone active"
          aria-current="page"
        >
          <Icon name="briefcase-business" className="nav-icon" />
          <span className="nav-label">Workspace</span>
        </a>
      </>
    );
  else if (data.mode === 'pulpit-editor')
    management = (
      <>
        <h2 className="sidebar-menu-section-title" title={data.editor.title}>
          {data.editor.title}
        </h2>
        {returnLink(data.editor.return_url, 'Wróć do pulpitów')}
        {data.editor.links.map((item) => (
          <a
            key={item.key}
            href={item.url}
            className={`nav-link sidebar-primary-link sidebar-primary-link--standalone${item.active ? ' active' : ''}`}
            data-pulpit-editor-section={item.key}
            aria-current={item.active ? 'page' : undefined}
            title={item.label}
          >
            <Icon name={item.icon} className="nav-icon" />
            <span className="nav-label">{item.label}</span>
          </a>
        ))}
      </>
    );
  return (
    <>
      <div
        id="sidebar-backdrop"
        className="sidebar-backdrop"
        aria-hidden="true"
        onClick={() => layout.close()}
      />
      <aside
        id="app-sidebar"
        className={`sidebar${layout.opened ? ' sidebar--visible' : ''}${favorites.drag ? ` is-dragging-from-${favorites.drag.origin}` : ''}`}
        data-sidebar-mode={data.mode}
        {...favorites.handlers}
        onClick={(event) => {
          if (
            (event.target as Element).closest('a[href]') &&
            !(event.target as Element).closest('button')
          )
            layout.close();
        }}
        onKeyDown={(event) => {
          favorites.handlers.onKeyDown(event);
          if (!event.defaultPrevented && event.key === 'Escape') {
            layout.close();
            document.querySelector<HTMLElement>('[data-sidebar-collapse-toggle]')?.focus();
          }
        }}
      >
        <nav
          className="sidebar-navigation"
          data-sidebar-navigation={data.mode}
          aria-label={data.mode === 'workspace' ? 'Główne menu' : 'Menu zarządzania'}
          onScroll={() => {
            setFlyout(undefined);
            window.dispatchEvent(new CustomEvent('ancore:sidebar-scroll'));
          }}
        >
          {data.mode === 'workspace' ? (
            <>
              <section
                className={`sidebar-menu-section sidebar-menu-section--favorites${!expanded ? ' is-collapsed' : ''}${favorites.drag?.target === 'add' ? ' is-drag-over' : ''}`}
                aria-labelledby="sidebar-favorites-title"
                data-sidebar-favorites-dropzone
                aria-busy={favorites.busy}
              >
                <h2 className="sidebar-menu-section-title">
                  <button
                    type="button"
                    className="sidebar-menu-section-toggle"
                    aria-label={`${expanded ? 'Zwiń' : 'Rozwiń'} sekcję Favorites`}
                    title={`${expanded ? 'Zwiń' : 'Rozwiń'} sekcję Favorites`}
                    aria-controls="sidebar-favorites-content"
                    aria-expanded={expanded}
                    onClick={() => {
                      setFavoritesCollapsed((value) => !value);
                      write('ancoreSidebarFavoritesCollapsed', !favoritesCollapsed);
                    }}
                  >
                    <span id="sidebar-favorites-title">Favorites</span>
                    <Icon name="chevron-down" className="sidebar-menu-section-chevron" />
                  </button>
                </h2>
                <div
                  id="sidebar-favorites-content"
                  className="sidebar-favorites-content"
                  hidden={!expanded}
                  aria-live="polite"
                >
                  <p id="sidebar-favorites-instructions" className="u-sr-only">
                    Przeciągnij element menu do Favorites, aby go dodać. Przeciągnij do pola Usuń z
                    Favorites, aby go usunąć. Alt i strzałka w górę albo w dół zmienia kolejność.
                  </p>
                  <div
                    className="sidebar-favorites-list"
                    data-sidebar-favorites-list
                    hidden={!data.favorites.length}
                  >
                    {data.favorites.map((item) => (
                      <Fragment key={item.key}>
                        {favorites.drag?.target === 'order' &&
                        favorites.drag.before === item.key ? (
                          <div className="sidebar-favorite-placeholder" aria-hidden="true" />
                        ) : null}
                        <div
                          className={`sidebar-favorite-row${favorites.drag?.key === item.key && favorites.drag.origin === 'favorites' ? ' is-dragging' : ''}`}
                          data-sidebar-favorite-item={item.key}
                          draggable={!favorites.busy}
                          aria-describedby="sidebar-favorites-instructions"
                        >
                          <a
                            href={item.url}
                            draggable={false}
                            className={`nav-link sidebar-favorite-link${data.links[item.key]?.is_active ? ' active' : ''}`}
                            aria-current={data.links[item.key]?.is_active ? 'page' : undefined}
                            aria-label={item.label}
                            title={item.label}
                            aria-keyshortcuts="Alt+ArrowUp Alt+ArrowDown"
                          >
                            <span className="sidebar-favorite-icon">
                              <Icon name={item.icon} />
                            </span>
                            <span className="nav-label">{item.label}</span>
                          </a>
                          <button
                            type="button"
                            className="u-sr-only"
                            disabled={favorites.busy}
                            onClick={() => void favorites.toggle(item.key, false)}
                          >
                            Usuń {item.label} z Favorites
                          </button>
                        </div>
                      </Fragment>
                    ))}
                    {favorites.drag?.target === 'order' && !favorites.drag.before ? (
                      <div className="sidebar-favorite-placeholder" aria-hidden="true" />
                    ) : null}
                  </div>
                  <p className="sidebar-favorites-message" hidden={!!data.favorites.length}>
                    Przeciągnij tutaj elementy menu
                  </p>
                </div>
                <div
                  className={`sidebar-favorites-remove-dropzone${favorites.drag?.target === 'remove' ? ' is-drag-over' : ''}`}
                  data-sidebar-favorites-remove-dropzone
                  aria-hidden="true"
                >
                  <Icon name="trash-2" />
                  <span>Usuń z Favorites</span>
                </div>
                <p className="u-sr-only" role="status">
                  {favorites.status}
                </p>
              </section>
              <section
                className="sidebar-menu-section sidebar-menu-section--workspace"
                aria-labelledby="sidebar-workspace-title"
              >
                <h2 id="sidebar-workspace-title" className="sidebar-menu-section-title">
                  Workspace
                </h2>
                {mainLink('for-you')}
                {data.collections.map((group) => (
                  <Fragment key={group.key}>
                    <CollectionGroup
                      group={group}
                      data={data}
                      actions={actions}
                      collapsed={groups.has(group.key)}
                      flyout={layout.collapsed}
                      flyoutOpen={flyout?.group.key === group.key}
                      onToggle={(anchor, keyboard) => {
                        if (layout.collapsed) {
                          setFlyout((value) =>
                            value?.group.key === group.key
                              ? undefined
                              : { group, anchor, keyboard },
                          );
                        } else {
                          const next = new Set(groups);
                          if (next.has(group.key)) next.delete(group.key);
                          else next.add(group.key);
                          setGroups(next);
                          write('ancoreSidebarCollapsedGroups', [...next]);
                        }
                      }}
                    />
                    <button
                      type="button"
                      className="u-sr-only"
                      disabled={favorites.busy}
                      onClick={() =>
                        void favorites.toggle(
                          group.key,
                          !data.favorites.some((item) => item.key === group.key),
                        )
                      }
                    >
                      {data.favorites.some((item) => item.key === group.key)
                        ? `Usuń ${group.label} z Favorites`
                        : `Dodaj ${group.label} do Favorites`}
                    </button>
                    {group.key === 'pulpits' ? (
                      <button
                        type="button"
                        className="u-sr-only"
                        disabled={favorites.busy}
                        onClick={() =>
                          void favorites.toggle(
                            'dashboard',
                            !data.favorites.some((item) => item.key === 'dashboard'),
                          )
                        }
                      >
                        {data.favorites.some((item) => item.key === 'dashboard')
                          ? 'Usuń Dashboard z Favorites'
                          : 'Dodaj Dashboard do Favorites'}
                      </button>
                    ) : null}
                  </Fragment>
                ))}
                {['calendar', 'documents', 'office'].map(mainLink)}
              </section>
              <div className="sidebar-menu-section sidebar-menu-section--bottom">
                {['resources', 'teams'].map(mainLink)}
              </div>
            </>
          ) : (
            <section className="sidebar-menu-section sidebar-menu-section--workspace">
              {management}
            </section>
          )}
        </nav>
        <div className="sidebar-resizer" data-sidebar-resizer {...layout.resizer} />
      </aside>
      {flyout ? (
        <Flyout
          group={flyout.group}
          anchor={flyout.anchor}
          keyboard={flyout.keyboard}
          onClose={(focus) => {
            if (focus) flyout.anchor.focus({ preventScroll: true });
            setFlyout(undefined);
          }}
        >
          <CollectionContents group={flyout.group} data={data} actions={actions} flyout />
        </Flyout>
      ) : null}
      {favorites.preview}
    </>
  );
}
function Flyout({
  group,
  anchor,
  keyboard,
  onClose,
  children,
}: {
  group: Collection;
  anchor: HTMLElement;
  keyboard: boolean;
  onClose: (focus?: boolean) => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const element = ref.current!,
      rect = anchor.getBoundingClientRect();
    element.style.left = `${Math.min(Math.max(rect.right, document.querySelector('.sidebar')!.getBoundingClientRect().right) + 8, innerWidth - element.offsetWidth - 12)}px`;
    element.style.top = `${Math.max(12, Math.min(rect.top, innerHeight - element.offsetHeight - 12))}px`;
    if (keyboard) element.querySelector<HTMLElement>('nav a, nav button')?.focus();
  }, []);
  useEffect(() => {
    const controller = new AbortController(),
      { signal } = controller;
    const outside = (event: Event) => {
      if (!ref.current?.contains(event.target as Node) && !anchor.contains(event.target as Node))
        onClose();
    };
    document.addEventListener('pointerdown', outside, { signal });
    document.addEventListener('focusin', outside, { signal });
    window.addEventListener('resize', () => onClose(), { signal });
    return () => controller.abort();
  }, [anchor, onClose]);
  return createPortal(
    <div
      ref={ref}
      id="sidebar-collapsed-flyout"
      className="sidebar-collapsed-flyout"
      role="dialog"
      aria-labelledby="sidebar-collapsed-flyout-title"
      onClick={(event) => {
        if ((event.target as Element).closest('a[href]')) onClose();
      }}
      onKeyDown={(event) => {
        if (event.defaultPrevented) return;
        if (event.key === 'Escape') {
          event.preventDefault();
          onClose(true);
        } else if (['ArrowDown', 'ArrowUp'].includes(event.key)) {
          event.preventDefault();
          const items = [
            ...ref.current!.querySelectorAll<HTMLElement>('a[href], button:not(:disabled)'),
          ].filter((item) => item.getClientRects().length);
          const index = items.indexOf(document.activeElement as HTMLElement);
          items[
            (index + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length
          ]?.focus();
        }
      }}
    >
      <header className="sidebar-collapsed-flyout__header">
        <strong id="sidebar-collapsed-flyout-title">{group.label}</strong>
        <button
          type="button"
          className="sidebar-collapsed-flyout__close"
          aria-label="Zamknij menu"
          onClick={() => onClose(true)}
        >
          <Icon name="x" />
        </button>
      </header>
      <nav className="sidebar-collapsed-flyout__links" aria-label="Podmenu">
        {children}
      </nav>
    </div>,
    document.body,
  );
}
