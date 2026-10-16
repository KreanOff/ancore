import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react';
import { createPortal } from 'react-dom';
import { pageRequest } from '../shared/page';
import { errorMessage } from '../shared/api';
import { Icon } from '../shared/Icon';
import type { Link, ShellData } from './navigation-types';
interface Drag {
  key: string;
  origin: 'favorites' | 'workspace';
  x: number;
  y: number;
  target: 'add' | 'remove' | 'order' | '';
  before?: string;
}
export function useFavorites(
  data: ShellData,
  api: string,
  token: string,
  update: (items: Link[]) => void,
) {
  const life = useRef(new AbortController()),
    operation = useRef<Promise<unknown>>();
  const [busy, setBusy] = useState(false),
    [status, setStatus] = useState(''),
    [drag, setDrag] = useState<Drag>();
  const pointer = useRef<{
    id: number;
    x: number;
    y: number;
    element: HTMLElement;
    key: string;
    origin: Drag['origin'];
    active: boolean;
  }>();
  const currentDrag = useRef(drag);
  currentDrag.current = drag;
  const suppressClick = useRef(false);
  useEffect(() => {
    const wait = (event: Event) => {
      if (operation.current)
        (event as CustomEvent).detail.waitUntil(
          operation.current.then(
            () => true,
            () => true,
          ),
        );
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        const value = pointer.current;
        if (value) {
          value.element.draggable = true;
          if (value.element.hasPointerCapture(value.id))
            value.element.releasePointerCapture(value.id);
        }
        pointer.current = undefined;
        setDrag(undefined);
      }
    };
    document.addEventListener('ancore:before-navigate', wait);
    document.addEventListener('keydown', escape);
    return () => {
      life.current.abort();
      document.removeEventListener('ancore:before-navigate', wait);
      document.removeEventListener('keydown', escape);
    };
  }, []);
  async function mutate(target: string, body: Record<string, string>, message: string) {
    if (operation.current) return;
    setBusy(true);
    setStatus('Zapisywanie Favorites…');
    const focused = document.activeElement?.closest<HTMLElement>('[data-sidebar-favorite-item]')
      ?.dataset.sidebarFavoriteItem;
    const promise = pageRequest<{ favorites: Link[] }>(
      api,
      target,
      token,
      life.current.signal,
      body,
    );
    operation.current = promise;
    try {
      const result = await promise;
      if (!life.current.signal.aborted) {
        update(result.favorites);
        if (focused)
          requestAnimationFrame(() => {
            if (document.activeElement === document.body)
              document
                .querySelector<HTMLElement>(`[data-sidebar-favorite-item="${focused}"] a`)
                ?.focus({ preventScroll: true });
          });
        setStatus(message);
      }
    } catch (error) {
      if (!life.current.signal.aborted) {
        const message = errorMessage(error);
        setStatus(message);
        window.showNotification?.(message, 'error');
      }
    } finally {
      operation.current = undefined;
      if (!life.current.signal.aborted) setBusy(false);
    }
  }
  const toggle = (key: string, add: boolean) =>
    mutate(
      data.favorite_toggle_url,
      { item_key: key, favorite_action: add ? 'add' : 'remove' },
      add ? 'Dodano do Favorites.' : 'Usunięto z Favorites.',
    );
  const reorder = (keys: string[]) =>
    mutate(
      data.favorite_reorder_url,
      { item_order: JSON.stringify(keys) },
      'Kolejność Favorites została zapisana.',
    );
  function commit(value?: Drag) {
    if (!value) return;
    if (value.target === 'remove') void toggle(value.key, false);
    else if (value.target === 'add') void toggle(value.key, true);
    else if (value.target === 'order') {
      const keys = data.favorites.map((item) => item.key).filter((key) => key !== value.key);
      const index = value.before ? keys.indexOf(value.before) : keys.length;
      keys.splice(index < 0 ? keys.length : index, 0, value.key);
      if (keys.join() !== data.favorites.map((item) => item.key).join()) void reorder(keys);
    }
  }
  function targetAt(key: string, origin: Drag['origin'], x: number, y: number): Drag {
    const target = document
      .elementFromPoint(x, y)
      ?.closest('[data-sidebar-favorites-remove-dropzone], [data-sidebar-favorites-dropzone]');
    let destination: Drag['target'] = '';
    if (target?.hasAttribute('data-sidebar-favorites-remove-dropzone') && origin === 'favorites')
      destination = 'remove';
    else if (target?.hasAttribute('data-sidebar-favorites-dropzone'))
      destination = origin === 'favorites' ? 'order' : 'add';
    const rows = [...document.querySelectorAll<HTMLElement>('[data-sidebar-favorite-item]')].filter(
      (e) => e.dataset.sidebarFavoriteItem !== key,
    );
    const before =
      destination === 'order'
        ? rows.find((e) => {
            const rect = e.getBoundingClientRect();
            return y < rect.top + rect.height / 2;
          })?.dataset.sidebarFavoriteItem
        : undefined;
    return { key, origin, x, y, target: destination, before };
  }
  function start(event: ReactPointerEvent<HTMLElement>) {
    if (
      busy ||
      event.button ||
      !event.isPrimary ||
      (event.target as Element).closest('button, input, form')
    )
      return;
    if (
      event.pointerType === 'touch' &&
      !(event.target as Element).closest('.nav-icon, .sidebar-favorite-icon')
    )
      return;
    const element = (event.target as Element).closest<HTMLElement>(
      '[data-sidebar-favorite-item], [data-sidebar-source-item]',
    );
    const key = element?.dataset.sidebarFavoriteItem || element?.dataset.sidebarSourceItem;
    if (!element || !key || !data.links[key]) return;
    pointer.current = {
      id: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      key,
      element,
      origin: element.dataset.sidebarFavoriteItem ? 'favorites' : 'workspace',
      active: false,
    };
    element.draggable = false;
  }
  function move(event: ReactPointerEvent<HTMLElement>) {
    const value = pointer.current;
    if (!value || value.id !== event.pointerId) return;
    if (!value.active) {
      if (Math.hypot(value.x - event.clientX, value.y - event.clientY) < 6) return;
      value.active = true;
      value.element.setPointerCapture(event.pointerId);
    }
    event.preventDefault();
    setDrag(targetAt(value.key, value.origin, event.clientX, event.clientY));
    const nav = value.element.closest('nav');
    if (nav) {
      const bounds = nav.getBoundingClientRect();
      if (event.clientY < bounds.top + 36) nav.scrollTop -= 12;
      else if (event.clientY > bounds.bottom - 36) nav.scrollTop += 12;
    }
  }
  function finish(event: ReactPointerEvent<HTMLElement>, cancel = false) {
    const value = pointer.current;
    if (!value || value.id !== event.pointerId) return;
    pointer.current = undefined;
    value.element.draggable = true;
    if (value.element.hasPointerCapture(event.pointerId))
      value.element.releasePointerCapture(event.pointerId);
    if (value.active) {
      event.preventDefault();
      suppressClick.current = true;
      if (!cancel) commit(targetAt(value.key, value.origin, event.clientX, event.clientY));
      setTimeout(() => {
        suppressClick.current = false;
      }, 0);
    }
    setDrag(undefined);
  }
  const dragItem = drag && data.links[drag.key];
  return {
    busy,
    status,
    drag,
    toggle,
    reorder,
    handlers: {
      onPointerDown: start,
      onPointerMove: move,
      onPointerUp: (event: ReactPointerEvent<HTMLElement>) => finish(event),
      onPointerCancel: (event: ReactPointerEvent<HTMLElement>) => finish(event, true),
      onClickCapture: (event: React.MouseEvent<HTMLElement>) => {
        if (suppressClick.current) {
          event.preventDefault();
          event.stopPropagation();
        }
      },
      onDragStart: (event: React.DragEvent<HTMLElement>) => {
        const element = (event.target as Element).closest<HTMLElement>(
          '[data-sidebar-favorite-item], [data-sidebar-source-item]',
        );
        const key = element?.dataset.sidebarFavoriteItem || element?.dataset.sidebarSourceItem;
        if (!key || busy) {
          event.preventDefault();
          return;
        }
        event.dataTransfer.setData('text/plain', key);
        setDrag({
          key,
          origin: element?.dataset.sidebarFavoriteItem ? 'favorites' : 'workspace',
          x: event.clientX,
          y: event.clientY,
          target: '',
        });
      },
      onDragOver: (event: React.DragEvent<HTMLElement>) => {
        const value = currentDrag.current;
        if (!value) return;
        event.preventDefault();
        setDrag(targetAt(value.key, value.origin, event.clientX, event.clientY));
      },
      onDrop: (event: React.DragEvent<HTMLElement>) => {
        event.preventDefault();
        const value = currentDrag.current;
        if (value) commit(targetAt(value.key, value.origin, event.clientX, event.clientY));
        setDrag(undefined);
      },
      onDragEnd: () => setDrag(undefined),
      onKeyDown: (event: React.KeyboardEvent<HTMLElement>) => {
        if (!event.altKey || !['ArrowUp', 'ArrowDown'].includes(event.key)) return;
        const row = (event.target as Element).closest<HTMLElement>('[data-sidebar-favorite-item]');
        if (!row) return;
        const keys = data.favorites.map((item) => item.key),
          index = keys.indexOf(row.dataset.sidebarFavoriteItem!);
        const next = index + (event.key === 'ArrowUp' ? -1 : 1);
        if (next < 0 || next >= keys.length || busy) return;
        event.preventDefault();
        [keys[index], keys[next]] = [keys[next], keys[index]];
        void reorder(keys);
      },
    },
    preview: dragItem
      ? createPortal(
          <div
            className="sidebar-drag-preview"
            style={{
              left: Math.min(innerWidth - 180, Math.max(8, drag!.x + 14)),
              top: Math.min(innerHeight - 44, Math.max(8, drag!.y + 14)),
              maxWidth: 240,
            }}
            aria-hidden="true"
          >
            <span className="sidebar-drag-preview__icon">
              <Icon name={dragItem.icon} />
            </span>
            <span className="sidebar-drag-preview__label">{dragItem.label}</span>
          </div>,
          document.body,
        )
      : null,
  };
}
