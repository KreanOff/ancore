import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Avatar, type AvatarData } from '../shared/Avatar';
import { Icon } from '../shared/Icon';
import { pageRequest } from '../shared/page';
import type { Collection } from './navigation-types';
interface Results {
  results: { id: string; name: string; url: string; avatar?: AvatarData; detail?: string }[];
  has_more: boolean;
}
export default function CollectionPicker({
  collection,
  anchor,
  api,
  token,
  onClose,
}: {
  collection: Collection;
  anchor: HTMLElement;
  api: string;
  token: string;
  onClose: (focus?: boolean) => void;
}) {
  const panel = useRef<HTMLDivElement>(null),
    input = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState(''),
    [data, setData] = useState<Results>(),
    [state, setState] = useState(''),
    [retry, setRetry] = useState(0);
  const id = `sidebar-${collection.key}-picker`;
  const directory = new URL(collection.directory_url, location.origin);
  if (query.trim()) directory.searchParams.set('q', query.trim());
  function position() {
    const element = panel.current;
    if (!element) return;
    const rect = element.getBoundingClientRect(),
      from = anchor.getBoundingClientRect();
    const scale = rect.width / element.offsetWidth || 1,
      margin = 8;
    const left =
      innerWidth <= 767
        ? margin
        : Math.min(
            Math.max(
              from.right,
              document.querySelector('.sidebar')?.getBoundingClientRect().right || 0,
            ) + margin,
            innerWidth - rect.width - margin,
          );
    element.style.left = `${Math.max(margin, left) / scale}px`;
    element.style.top = `${Math.max(margin, Math.min(innerWidth <= 767 ? from.bottom + margin : from.top, innerHeight - rect.height - margin)) / scale}px`;
  }
  useLayoutEffect(() => {
    panel.current?.showPopover();
    position();
    input.current?.focus({ preventScroll: true });
    return () => {
      panel.current?.hidePopover();
    };
  }, []);
  useLayoutEffect(position, [data, state]);
  useEffect(() => {
    const controller = new AbortController();
    setData(undefined);
    setState(query.trim() ? 'Wyszukiwanie…' : '');
    if (!query.trim()) return () => controller.abort();
    const timer = setTimeout(async () => {
      const target = new URL(collection.search_url, location.origin);
      target.searchParams.set('q', query.trim());
      try {
        const result = await pageRequest<Results>(api, target.href, token, controller.signal);
        if (!controller.signal.aborted) {
          setData(result);
          setState(result.results.length ? '' : 'Brak pasujących wyników.');
        }
      } catch {
        if (!controller.signal.aborted) setState('Nie udało się pobrać wyników.');
      }
    }, 200);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query, retry, collection.search_url, api, token]);
  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;
    const outside = (event: Event) => {
      if (!panel.current?.contains(event.target as Node) && !anchor.contains(event.target as Node))
        onClose();
    };
    document.addEventListener('pointerdown', outside, { signal });
    document.addEventListener('focusin', outside, { signal });
    window.addEventListener('resize', () => onClose(), { signal });
    return () => controller.abort();
  }, [anchor, onClose]);
  return createPortal(
    <div
      ref={panel}
      {...{ popover: 'manual' }}
      id={id}
      className="sidebar-workspace-menu sidebar-space-picker"
      role="dialog"
      aria-labelledby={`${id}-title`}
      data-react-collection-picker={collection.key}
      onClick={(event) => {
        if ((event.target as Element).closest('a[href]')) onClose();
      }}
      onKeyDown={(event) => {
        if (event.key === 'Escape') {
          event.preventDefault();
          event.stopPropagation();
          onClose(true);
        }
        if (['ArrowDown', 'ArrowUp'].includes(event.key)) {
          event.preventDefault();
          const items = [
            ...panel.current!.querySelectorAll<HTMLElement>('input, a[href], button'),
          ].filter((e) => e.getClientRects().length);
          const index = items.indexOf(document.activeElement as HTMLElement);
          items[
            (index + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length
          ]?.focus();
        }
      }}
    >
      <header className="sidebar-collapsed-flyout__header">
        <strong id={`${id}-title`}>{collection.label}</strong>
        <button
          type="button"
          className="sidebar-collapsed-flyout__close"
          aria-label="Zamknij panel"
          onClick={() => onClose(true)}
        >
          <Icon name="x" />
        </button>
      </header>
      <form
        className="sidebar-workspace-search"
        role="search"
        action={directory.pathname}
        onSubmit={(event) => {
          event.preventDefault();
          const link = panel.current?.querySelector<HTMLAnchorElement>('[data-picker-directory]');
          link?.click();
        }}
      >
        <label>
          <Icon name="search" />
          <input
            ref={input}
            type="search"
            name="q"
            aria-label={`Wyszukaj: ${collection.label}`}
            placeholder={`Wyszukaj: ${collection.label}`}
            maxLength={120}
            autoComplete="off"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            aria-controls={`${id}-results`}
          />
        </label>
      </form>
      {state ? (
        <p className="sidebar-workspace-search__empty" role="status">
          {state}
          {state.startsWith('Nie udało') ? (
            <>
              {' '}
              <button
                type="button"
                className="tasks-project-menu-button"
                onClick={() => setRetry((value) => value + 1)}
              >
                Spróbuj ponownie
              </button>
            </>
          ) : null}
        </p>
      ) : null}
      <nav
        id={`${id}-results`}
        className="sidebar-workspace-menu__list"
        aria-label="Wyniki wyszukiwania"
        aria-busy={state === 'Wyszukiwanie…'}
        hidden={!data?.results.length}
      >
        {data?.results.map((row) => (
          <a
            key={row.id}
            href={row.url}
            className="sidebar-workspace-option sidebar-space-picker__result"
            title={[row.name, row.detail].filter(Boolean).join(' · ')}
          >
            {row.avatar ? <Avatar data={row.avatar} space /> : <Icon name={collection.icon} />}
            <span>{row.name}</span>
          </a>
        ))}
        {data?.has_more ? (
          <p className="sidebar-workspace-search__empty">Więcej wyników znajdziesz w katalogu.</p>
        ) : null}
      </nav>
      <a
        href={directory.pathname + directory.search}
        className="sidebar-workspace-manage"
        data-picker-directory
      >
        <Icon name="align-left" />
        <span>Wyświetl wszystkie: {collection.label.toLocaleLowerCase('pl')}</span>
      </a>
    </div>,
    document.body,
  );
}
