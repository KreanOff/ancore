import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { Avatar } from '../shared/Avatar';
import { Icon } from '../shared/Icon';
import { pageRequest, type Page } from '../shared/page';
import { request, errorMessage } from '../shared/api';
import type { FormDialogData } from '../forms/FormDialog';
import type { PanelsConfig } from './types';
import type { Collection, CollectionRow, ReturnContext, ShellData } from './navigation-types';
import { startNavigation } from './navigation';
import { useShellLayout } from './useShellLayout';
import GlobalPanels from './GlobalPanels';
import Sidebar from './Sidebar';
import WorkspaceMenu from './WorkspaceMenu';
import Toasts from './Toasts';
const Picker = lazy(() => import('./CollectionPicker'));
const Dialog = lazy(() =>
  import('../forms/FormDialog').then((module) => ({ default: module.FormDialog })),
);
export default function Shell({ config, token }: { config: PanelsConfig; token: string }) {
  const [data, setData] = useState(config.shell),
    [context, setContext] = useState<ReturnContext | null>(null),
    [ready, setReady] = useState(false);
  const [picker, setPicker] = useState<{ group: Collection; anchor: HTMLElement }>();
  const [modal, setModal] = useState<FormDialogData>();
  const [starBusy, setStarBusy] = useState(false),
    [formBusy, setFormBusy] = useState(false);
  const life = useRef(new AbortController()),
    pending = useRef<Promise<unknown>>(),
    refreshRequest = useRef<AbortController>();
  const layout = useShellLayout(data.mode);
  const dataRef = useRef(data);
  dataRef.current = data;
  useEffect(() => {
    setReady(true);
    const stop = startNavigation(config.shell, token, (shell, context) => {
      setData(shell);
      setContext(context);
    });
    const wait = (event: Event) => {
      if (pending.current)
        (event as CustomEvent).detail.waitUntil(
          pending.current.then(
            () => true,
            () => true,
          ),
        );
    };
    const close = () => {
      setPicker(undefined);
      setModal(undefined);
    };
    const settingsSaved = (event: Event) => {
      const { name, canConfigure } = (
        event as CustomEvent<{ name: string; canConfigure?: boolean }>
      ).detail;
      const key =
        event.type === 'ancore:space-settings-saved' ? 'space_settings' : 'pulpit_settings';
      setData((previous) =>
        previous[key]
          ? {
              ...previous,
              [key]: {
                ...previous[key],
                name,
                links:
                  key === 'space_settings' && canConfigure === false
                    ? previous[key].links.filter((link) => link.key !== 'types')
                    : previous[key].links,
              },
            }
          : previous,
      );
      if (key === 'pulpit_settings')
        void refresh().catch(() => {
          // A fresh navigation still reloads the collection when this background read fails.
        });
    };
    window.addEventListener('ancore:space-settings-saved', settingsSaved);
    window.addEventListener('ancore:pulpit-settings-saved', settingsSaved);
    document.addEventListener('ancore:before-navigate', wait);
    document.addEventListener('ancore:content-unloading', close);
    return () => {
      stop();
      life.current.abort();
      refreshRequest.current?.abort();
      document.removeEventListener('ancore:before-navigate', wait);
      document.removeEventListener('ancore:content-unloading', close);
      window.removeEventListener('ancore:space-settings-saved', settingsSaved);
      window.removeEventListener('ancore:pulpit-settings-saved', settingsSaved);
    };
  }, []);
  useEffect(() => {
    const open = (event: MouseEvent) => {
      if (
        event.defaultPrevented ||
        event.button ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
      )
        return;
      const link =
        event.target instanceof Element ? event.target.closest<HTMLAnchorElement>('a[href]') : null;
      if (
        !link ||
        link.hasAttribute('download') ||
        (link.target && link.target !== '_self') ||
        link.closest('[data-app-full-navigation]')
      )
        return;
      const url = new URL(link.href, location.href);
      const filter = /^\/(?:workplaces\/[^/]+\/)?filters\/(?:manage\/)?\d+\/edit\/$/.test(
        url.pathname,
      );
      if (url.origin !== location.origin || !filter) return;
      // Filter pages already open their own FormDialog; the shell handles links outside them.
      if (filter && link.closest('[data-react-screen]')) return;
      const workspace = /^\/workplaces\/([^/]+)\//.exec(url.pathname)?.[1];
      if (workspace && workspace !== /^\/workplaces\/([^/]+)\//.exec(config.api_url)?.[1]) return;
      if (document.querySelector('.tasks-modal.is-open')) return;
      event.preventDefault();
      if (pending.current) return;
      setPicker(undefined);
      setFormBusy(true);
      const promise = (async () => {
        const page = await pageRequest<Page>(config.api_url, url.href, token, life.current.signal);
        await window.AncoreReactRuntime?.preparePage({
          page,
          shell: dataRef.current,
          csrf_token: token,
          messages: [],
        });
        if (life.current.signal.aborted) return;
        const dialog = (page.data as { modal?: FormDialogData }).modal;
        if (!dialog?.filter_settings) throw new Error('Nie udało się otworzyć ustawień filtra.');
        setModal(dialog);
      })();
      pending.current = promise;
      void promise
        .catch((exception) => {
          if (!life.current.signal.aborted)
            window.showNotification?.(errorMessage(exception), 'error');
        })
        .finally(() => {
          pending.current = undefined;
          if (!life.current.signal.aborted) setFormBusy(false);
        });
    };
    document.addEventListener('click', open, true);
    return () => document.removeEventListener('click', open, true);
  }, [config.api_url, token]);
  const closePicker = useCallback(
    (focus = false) =>
      setPicker((previous) => {
        if (focus) previous?.anchor.focus({ preventScroll: true });
        return undefined;
      }),
    [],
  );
  useEffect(() => {
    const controller = new AbortController(),
      { signal } = controller;
    for (const name of [
      'ancore:global-search-open',
      'ancore:notifications-open',
      'ancore:workspace-menu-open',
      'ancore:sidebar-toggle',
      'ancore:sidebar-scroll',
    ])
      window.addEventListener(name, () => closePicker(), { signal });
    return () => controller.abort();
  }, [closePicker]);
  async function refresh() {
    refreshRequest.current?.abort();
    const controller = new AbortController();
    refreshRequest.current = controller;
    const result = await request<
      Pick<ShellData, 'account_id' | 'workplace_id' | 'collections' | 'favorites'>
    >(
      `${dataRef.current.refresh_url}?url=${encodeURIComponent(location.pathname + location.search)}`,
      token,
      controller.signal,
    );
    if (controller.signal.aborted || life.current.signal.aborted) return;
    if (
      result.account_id !== dataRef.current.account_id ||
      result.workplace_id !== dataRef.current.workplace_id
    ) {
      location.reload();
      return;
    }
    setData((previous) => ({
      ...previous,
      collections: result.collections.map((group) => ({
        ...group,
        starred: group.starred.map((row) => ({
          ...row,
          active: [
            ...previous.collections.find((item) => item.key === group.key)!.starred,
            ...previous.collections.find((item) => item.key === group.key)!.recent,
          ].some((old) => old.id === row.id && old.active),
        })),
        recent: group.recent.map((row) => ({
          ...row,
          active: [
            ...previous.collections.find((item) => item.key === group.key)!.starred,
            ...previous.collections.find((item) => item.key === group.key)!.recent,
          ].some((old) => old.id === row.id && old.active),
        })),
      })),
      favorites: result.favorites,
    }));
  }
  async function star(row: CollectionRow) {
    if (pending.current) return;
    setStarBusy(true);
    const groupKey = dataRef.current.collections.find((group) =>
      [...group.starred, ...group.recent].some((item) => item.favorite_url === row.favorite_url),
    )?.key;
    const promise = (async () => {
      await pageRequest(config.api_url, row.favorite_url, token, life.current.signal, {
        next: location.pathname + location.search,
        return_to: location.pathname + location.search,
      });
      await refresh();
      requestAnimationFrame(() => {
        const group = document.querySelector<HTMLElement>(`[data-sidebar-group="${groupKey}"]`);
        const target =
          group?.querySelector<HTMLElement>(
            `[data-sidebar-collection-row="${row.id}"] .sidebar-space-row__toggle`,
          ) || group?.querySelector<HTMLElement>('[data-sidebar-group-toggle]');
        target?.focus({ preventScroll: true });
      });
    })();
    pending.current = promise;
    try {
      await promise;
    } catch (error) {
      if (!life.current.signal.aborted) window.showNotification?.(errorMessage(error), 'error');
    } finally {
      pending.current = undefined;
      if (!life.current.signal.aborted) setStarBusy(false);
    }
  }
  async function openForm(url: string) {
    if (pending.current || modal || document.querySelector('.tasks-modal.is-open')) return;
    setPicker(undefined);
    setFormBusy(true);
    const promise = (async () => {
      const page = await pageRequest<Page>(config.api_url, url, token, life.current.signal);
      await window.AncoreReactRuntime?.preparePage({
        page,
        shell: dataRef.current,
        csrf_token: token,
        messages: [],
      });
      const dialog =
        page.type === 'form'
          ? (page.data as FormDialogData)
          : (page.data as { modal?: FormDialogData }).modal;
      if (!dialog) throw new Error('Nie udało się otworzyć formularza.');
      if (!life.current.signal.aborted) setModal(dialog);
    })();
    pending.current = promise;
    try {
      await promise;
    } catch (error) {
      if (!life.current.signal.aborted) window.showNotification?.(errorMessage(error), 'error');
    } finally {
      pending.current = undefined;
      if (!life.current.signal.aborted) setFormBusy(false);
    }
  }
  return (
    <>
      <header className="app-topbar" aria-label="Narzędzia aplikacji" data-app-topbar>
        <div className="app-topbar__start">
          <button
            type="button"
            className="tasks-icon-button app-topbar__action app-topbar__collapse"
            aria-label={layout.label}
            title={layout.label}
            aria-controls="app-sidebar"
            aria-expanded={layout.mobile ? layout.opened : !layout.collapsed}
            data-sidebar-collapse-toggle
            onClick={layout.toggle}
          >
            <Icon name="panel-left" />
          </button>
          <div className="app-topbar__workspace">
            <WorkspaceMenu data={data} token={token} />
          </div>
        </div>
        <div id="app-global-search-host" style={{ display: 'contents' }} />
        <nav className="app-topbar__actions" aria-label="Notatka, powiadomienia i konto">
          <span id="app-global-actions-host" style={{ display: 'contents' }} />
          <a
            href={data.settings_url}
            className={`nav-link tasks-icon-button app-topbar__action${data.settings_active ? ' active' : ''}`}
            aria-label="Ustawienia Ancore"
            title="Ustawienia Ancore"
          >
            <Icon name="settings" />
          </a>
          <a
            href={data.profile.url}
            className={`nav-link app-topbar__profile${data.profile.active ? ' active' : ''}`}
            aria-label={`Profil użytkownika: ${data.profile.name}`}
            title="Profil użytkownika"
          >
            <Avatar data={data.profile.avatar} className="app-topbar__avatar" />
            <span className="app-topbar__username">{data.profile.name}</span>
          </a>
        </nav>
      </header>
      <Sidebar
        data={data}
        context={context}
        api={config.api_url}
        token={token}
        layout={layout}
        updateFavorites={(items) => setData((previous) => ({ ...previous, favorites: items }))}
        openForm={(url) => void openForm(url)}
        star={(row) => void star(row)}
        starBusy={starBusy || formBusy}
        picker={(group, anchor) => {
          window.dispatchEvent(new CustomEvent('ancore:sidebar-picker-open'));
          setPicker({ group, anchor });
        }}
      />
      {ready ? <GlobalPanels config={config} token={token} /> : null}
      {ready ? <Toasts initial={config.messages} /> : null}
      <div id="app-shell-modals" style={{ display: 'contents' }} />
      <Suspense fallback={null}>
        {picker ? (
          <Picker
            collection={picker.group}
            anchor={picker.anchor}
            api={config.api_url}
            token={token}
            onClose={closePicker}
          />
        ) : null}
        {modal ? (
          <Dialog
            data={modal}
            api={config.api_url}
            csrfToken={token}
            hostId="app-shell-modals"
            onClose={() => setModal(undefined)}
            onSaved={(url) => {
              flushSync(() => setModal(undefined));
              void window.AncoreApp?.navigate(
                modal.filter_settings === 'edit' ? location.pathname + location.search : url,
              );
            }}
          />
        ) : null}
      </Suspense>
    </>
  );
}
