import { useEffect, useLayoutEffect, useRef, useState, type PointerEvent } from 'react';
import { read, write } from './storage';
export function useShellLayout(mode: string) {
  const entitySettings = mode === 'space-settings' || mode === 'pulpit-settings';
  const [mobile, setMobile] = useState(innerWidth <= 767),
    [workspaceCollapsed, setWorkspaceCollapsed] = useState(
      () => read<boolean>('ancoreSidebarCollapsed', false) === true,
    ),
    [settingsCollapsed, setSettingsCollapsed] = useState(false),
    [opened, setOpened] = useState(false);
  const collapsed = entitySettings ? settingsCollapsed : workspaceCollapsed;
  const [width, setWidth] = useState(() => {
    const saved = Number(read<number>('ancoreSidebarWidth', 272));
    return Number.isFinite(saved) && saved > 0 ? saved : 272;
  });
  const [viewport, setViewport] = useState(innerWidth);
  const resize = useRef<{ id: number; x: number; width: number }>();
  const transition = useRef<ReturnType<typeof setTimeout>>();
  const max = Math.min(420, Math.max(220, viewport - 360));
  const clamped = Math.min(max, Math.max(220, width));
  useEffect(() => {
    // Each visit starts with readable section names without changing the Workspace preference.
    if (!entitySettings) setSettingsCollapsed(false);
  }, [entitySettings]);
  useEffect(() => {
    const update = () => {
      setMobile(innerWidth <= 767);
      setViewport(innerWidth);
      setOpened(false);
    };
    window.addEventListener('resize', update);
    return () => {
      window.removeEventListener('resize', update);
      clearTimeout(transition.current);
      document.body.classList.remove('sidebar-resizing', 'sidebar-open');
      document.documentElement.classList.remove(
        'sidebar-transitioning',
        'sidebar-is-collapsing',
        'sidebar-is-expanding',
      );
    };
  }, []);
  useLayoutEffect(() => {
    for (const target of [document.documentElement, document.body])
      target.classList.toggle('sidebar-collapsed', collapsed && !mobile);
    document.body.classList.toggle('sidebar-open', opened && mobile);
    if (mobile) document.documentElement.style.removeProperty('--sidebar-width');
    else document.documentElement.style.setProperty('--sidebar-width', `${clamped}px`);
  }, [collapsed, mobile, opened, clamped]);
  useEffect(() => {
    if (!opened || !mobile) return;
    const main = document.querySelector<HTMLElement>('.main-content');
    const wasInert = Boolean(main?.inert);
    if (main) main.inert = true;
    const trap = (event: KeyboardEvent) => {
      if (event.key !== 'Tab' || document.querySelector('.tasks-modal.is-open')) return;
      const items = [
        ...document.querySelectorAll<HTMLElement>(
          '#app-sidebar a[href], #app-sidebar button, [data-sidebar-collapse-toggle]',
        ),
      ].filter((e) => e.getClientRects().length && !e.matches(':disabled'));
      const first = items[0],
        last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener('keydown', trap);
    return () => {
      if (main?.isConnected) main.inert = wasInert;
      document.removeEventListener('keydown', trap);
    };
  }, [opened, mobile]);
  function toggle() {
    window.dispatchEvent(new CustomEvent('ancore:sidebar-toggle'));
    if (mobile) {
      setOpened((value) => !value);
      return;
    }
    const next = !collapsed;
    if (!matchMedia('(prefers-reduced-motion: reduce)').matches) {
      const root = document.documentElement;
      clearTimeout(transition.current);
      root.classList.remove('sidebar-is-collapsing', 'sidebar-is-expanding');
      root.classList.add(
        'sidebar-transitioning',
        next ? 'sidebar-is-collapsing' : 'sidebar-is-expanding',
      );
      transition.current = setTimeout(
        () =>
          root.classList.remove(
            'sidebar-transitioning',
            'sidebar-is-collapsing',
            'sidebar-is-expanding',
          ),
        440,
      );
    }
    if (entitySettings) setSettingsCollapsed(next);
    else {
      setWorkspaceCollapsed(next);
      write('ancoreSidebarCollapsed', next);
    }
  }
  function persist(value: number) {
    const next = Math.min(max, Math.max(220, value));
    setWidth(next);
    write('ancoreSidebarWidth', Math.round(next));
  }
  const label = mobile
    ? opened
      ? 'Zamknij menu boczne'
      : 'Otwórz menu boczne'
    : collapsed
      ? 'Rozwiń menu boczne'
      : 'Zwiń menu boczne';
  return {
    mobile,
    collapsed: collapsed && !mobile,
    opened,
    toggle,
    label,
    close: () => setOpened(false),
    resizer: {
      role: 'separator',
      'aria-orientation': 'vertical' as const,
      'aria-label': 'Zmień szerokość menu bocznego',
      'aria-valuemin': 220,
      'aria-valuemax': max,
      'aria-valuenow': Math.round(clamped),
      'aria-valuetext': `${Math.round(clamped)} pikseli`,
      tabIndex: mobile || collapsed ? -1 : 0,
      onDoubleClick: () => persist(272),
      onPointerDown: (event: PointerEvent<HTMLDivElement>) => {
        if (mobile || collapsed || event.button || !event.isPrimary) return;
        event.preventDefault();
        event.currentTarget.setPointerCapture(event.pointerId);
        resize.current = { id: event.pointerId, x: event.clientX, width: clamped };
        document.body.classList.add('sidebar-resizing');
      },
      onPointerMove: (event: PointerEvent<HTMLDivElement>) => {
        if (resize.current?.id === event.pointerId) {
          event.preventDefault();
          setWidth(
            Math.min(max, Math.max(220, resize.current.width + event.clientX - resize.current.x)),
          );
        }
      },
      onPointerUp: (event: PointerEvent<HTMLDivElement>) => {
        if (resize.current?.id === event.pointerId) {
          resize.current = undefined;
          document.body.classList.remove('sidebar-resizing');
          persist(clamped);
        }
      },
      onPointerCancel: () => {
        resize.current = undefined;
        document.body.classList.remove('sidebar-resizing');
      },
      onKeyDown: (event: React.KeyboardEvent<HTMLDivElement>) => {
        if (mobile || collapsed) return;
        const value =
          event.key === 'Home'
            ? 220
            : event.key === 'End'
              ? max
              : event.key === 'ArrowLeft'
                ? clamped - (event.shiftKey ? 24 : 8)
                : event.key === 'ArrowRight'
                  ? clamped + (event.shiftKey ? 24 : 8)
                  : undefined;
        if (value !== undefined) {
          event.preventDefault();
          persist(value);
        }
      },
    },
  };
}
