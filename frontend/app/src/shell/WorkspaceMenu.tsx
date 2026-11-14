import { useEffect, useRef, useState } from 'react';
import { Avatar } from '../shared/Avatar';
import { Icon } from '../shared/Icon';
import { LoadingOverlay } from '../shared/LoadingOverlay';
import { useNativeSubmitLoading } from '../shared/useNativeSubmitLoading';
import type { ShellData } from './navigation-types';
import { normalize } from './storage';
export default function WorkspaceMenu({ data, token }: { data: ShellData; token: string }) {
  const [open, setOpen] = useState(false),
    [query, setQuery] = useState('');
  const root = useRef<HTMLDivElement>(null),
    input = useRef<HTMLInputElement>(null),
    toggle = useRef<HTMLButtonElement>(null);
  const switching = useNativeSubmitLoading(() => toggle.current);
  const current = data.workplaces.find((item) => item.id === data.workplace_id);
  useEffect(() => {
    const controller = new AbortController(),
      { signal } = controller;
    const close = () => setOpen(false);
    for (const name of [
      'ancore:global-search-open',
      'ancore:notifications-open',
      'ancore:sidebar-toggle',
      'ancore:sidebar-picker-open',
    ])
      window.addEventListener(name, close, { signal });
    document.addEventListener('ancore:content-unloading', close, { signal });
    document.addEventListener(
      'pointerdown',
      (event) => {
        if (!root.current?.contains(event.target as Node)) close();
      },
      { signal },
    );
    document.addEventListener(
      'focusin',
      (event) => {
        if (!root.current?.contains(event.target as Node)) close();
      },
      { signal },
    );
    return () => controller.abort();
  }, []);
  useEffect(() => {
    if (open) {
      window.dispatchEvent(new CustomEvent('ancore:workspace-menu-open'));
      input.current?.focus({ preventScroll: true });
    } else setQuery('');
  }, [open]);
  const matches = data.workplaces.filter((item) => normalize(item.name).includes(normalize(query)));
  return (
    <div ref={root} className="sidebar-workspace-switcher">
      <button
        ref={toggle}
        type="button"
        className="sidebar-workspace-toggle"
        aria-label={`Zmień Workspace. Bieżący: ${current?.name || 'Workspace'}`}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls="sidebar-workspace-menu"
        onClick={() => setOpen((value) => !value)}
      >
        {current ? (
          <Avatar data={current.avatar} space className="sidebar-workspace-avatar" />
        ) : (
          <Icon name="briefcase-business" />
        )}
        <span className="sidebar-workspace-name">{current?.name || 'Workspace'}</span>
      </button>
      <div
        id="sidebar-workspace-menu"
        className="sidebar-workspace-menu"
        role="menu"
        aria-label="Dostępne Workspace"
        hidden={!open}
        onKeyDown={(event) => {
          if (event.key === 'Escape') {
            event.preventDefault();
            event.stopPropagation();
            setOpen(false);
            toggle.current?.focus();
          }
          if (
            ['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key) &&
            !(event.target instanceof HTMLInputElement && ['Home', 'End'].includes(event.key))
          ) {
            const items = [
              ...root.current!.querySelectorAll<HTMLElement>('[role=menuitem]'),
            ].filter((e) => e.getClientRects().length);
            const index = items.indexOf(document.activeElement as HTMLElement);
            event.preventDefault();
            items[
              event.key === 'Home'
                ? 0
                : event.key === 'End'
                  ? items.length - 1
                  : index < 0
                    ? event.key === 'ArrowDown'
                      ? 0
                      : items.length - 1
                    : (index + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length
            ]?.focus();
          }
        }}
      >
        <span className="sidebar-workspace-menu__title">Workspace</span>
        <div className="sidebar-workspace-search" role="search">
          <label>
            <span className="u-sr-only">Szukaj Workspace</span>
            <Icon name="search" />
            <input
              ref={input}
              type="search"
              aria-label="Szukaj Workspace"
              placeholder="Szukaj Workspace"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              autoComplete="off"
              spellCheck={false}
            />
          </label>
          <p
            className="sidebar-workspace-search__empty"
            aria-live="polite"
            hidden={matches.length > 0}
          >
            Brak wyników
          </p>
        </div>
        <div className="sidebar-workspace-menu__list">
          {matches.map((item) => (
            <form
              key={item.id}
              method="post"
              action={item.switch_url}
              onSubmit={switching.onSubmit}
              aria-busy={switching.pending}
            >
              <input type="hidden" name="csrfmiddlewaretoken" value={token} />
              <button
                type="submit"
                className={`sidebar-workspace-option${item.id === data.workplace_id ? ' is-active' : ''}`}
                role="menuitem"
                disabled={switching.pending}
                aria-current={item.id === data.workplace_id ? 'true' : undefined}
              >
                <Avatar
                  data={item.avatar}
                  space
                  className="sidebar-workspace-avatar sidebar-workspace-avatar--option"
                />
                <span>{item.name}</span>
                {item.id === data.workplace_id ? (
                  <Icon name="check" className="sidebar-workspace-option__check" />
                ) : null}
              </button>
            </form>
          ))}
        </div>
        <a href={data.workplaces_url} role="menuitem" className="sidebar-workspace-manage">
          <Icon name="settings-2" />
          <span>Zarządzaj Workspace</span>
        </a>
      </div>
      <LoadingOverlay active={switching.pending} label="Przełączanie Workspace…" />
    </div>
  );
}
