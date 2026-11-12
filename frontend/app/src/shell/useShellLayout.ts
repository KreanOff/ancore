import { useEffect, useLayoutEffect, useRef, useState, type PointerEvent } from 'react';
import { read, write } from './storage';
import { acquireInert } from '../shared/inert';
import {
  RIGHT_SIDEBAR_MIN,
  RIGHT_SIDEBAR_STORAGE,
  rightSidebarDragWidth,
  savedRightSidebarWidth,
  sidebarWidths,
} from './sidebarSizing';

type PanelResize = {
  id: number;
  x: number;
  width: number;
  scale: number;
  value: number;
  target: HTMLDivElement;
  preference: number | null;
};

function shellMetrics() {
  const style = getComputedStyle(document.body);
  return {
    scale: Math.max(0.1, parseFloat(style.getPropertyValue('--app-ui-scale')) || 1),
    gap: parseFloat(style.getPropertyValue('--app-shell-gap')) || 0,
    collapsedWidth: parseFloat(style.getPropertyValue('--sidebar-collapsed-width')) || 64,
    rightDefault:
      parseFloat(style.getPropertyValue('--app-right-sidebar-default-width')) ||
      (document.querySelector('.work-task-page') ? 370 : 272),
  };
}

export function useShellLayout(mode: string) {
  const entitySettings = mode === 'space-settings' || mode === 'pulpit-settings';
  const [mobile, setMobile] = useState(innerWidth <= 767),
    [workspaceCollapsed, setWorkspaceCollapsed] = useState(
      () => read<boolean>('ancoreSidebarCollapsed', false) === true,
    ),
    [settingsCollapsed, setSettingsCollapsed] = useState(false),
    [opened, setOpened] = useState(false),
    [rightCollapsed, setRightCollapsed] = useState(
      () => read<boolean>('ancoreRightSidebarCollapsed', false) === true,
    ),
    [rightOpened, setRightOpened] = useState(false);
  const collapsed = entitySettings ? settingsCollapsed : workspaceCollapsed;
  const [width, setWidth] = useState(() => {
    const saved = Number(read<number>('ancoreSidebarWidth', 272));
    return Number.isFinite(saved) && saved > 0 ? saved : 272;
  });
  const [viewport, setViewport] = useState(innerWidth);
  const [rightWidth, setRightWidth] = useState(() =>
    savedRightSidebarWidth(read<unknown>(RIGHT_SIDEBAR_STORAGE, null)),
  );
  const [metrics, setMetrics] = useState(shellMetrics);
  const rightNarrow = viewport <= 1100;
  const rightExpanded = rightNarrow ? rightOpened : !rightCollapsed;
  const rightResizable = !rightNarrow && rightExpanded;
  const resize = useRef<PanelResize>();
  const rightResize = useRef<PanelResize>();
  const transition = useRef<ReturnType<typeof setTimeout>>();
  const {
    left: clamped,
    leftMax: max,
    right: rightClamped,
    rightMax,
  } = sidebarWidths({
    viewport,
    ...metrics,
    leftPreference: width,
    leftCollapsed: collapsed,
    rightPreference: rightWidth,
    rightVisible: rightResizable,
  });
  useLayoutEffect(() => {
    const measure = () => {
      const next = shellMetrics();
      setMetrics((previous) =>
        Object.keys(next).every(
          (key) => previous[key as keyof typeof next] === next[key as keyof typeof next],
        )
          ? previous
          : next,
      );
    };
    measure();
    const frame = requestAnimationFrame(measure);
    // A lazy initial task mount changes the panel token after the shell is ready.
    // Observe its effect on the content box without watching the whole DOM.
    const content = document.querySelector('.main-content');
    const observer = new ResizeObserver(measure);
    if (content) observer.observe(content);
    document.addEventListener('ancore:content-loaded', measure);
    window.addEventListener('resize', measure);
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      document.removeEventListener('ancore:content-loaded', measure);
      window.removeEventListener('resize', measure);
    };
  }, []);
  useEffect(() => {
    // Each visit starts with readable section names without changing the Workspace preference.
    if (!entitySettings) setSettingsCollapsed(false);
  }, [entitySettings]);
  useEffect(() => {
    const update = () => {
      stopResize(false);
      stopRightResize(false);
      if (
        document.getElementById('app-right-sidebar')?.contains(document.activeElement) ||
        document.activeElement?.matches('[data-right-sidebar-resizer]')
      )
        document
          .querySelector<HTMLElement>('[data-right-sidebar-toggle]')
          ?.focus({ preventScroll: true });
      setMobile(innerWidth <= 767);
      setViewport(innerWidth);
      setOpened(false);
      setRightOpened(false);
    };
    const closeRightDrawer = () => {
      stopResize(false);
      stopRightResize(false);
      setRightOpened(false);
    };
    const cancelResize = () => {
      stopResize(false);
      stopRightResize(false);
    };
    window.addEventListener('resize', update);
    window.addEventListener('blur', cancelResize);
    document.addEventListener('ancore:content-unloading', closeRightDrawer);
    for (const name of [
      'ancore:global-search-open',
      'ancore:notifications-open',
      'ancore:workspace-menu-open',
    ])
      window.addEventListener(name, closeRightDrawer);
    return () => {
      window.removeEventListener('resize', update);
      window.removeEventListener('blur', cancelResize);
      document.removeEventListener('ancore:content-unloading', closeRightDrawer);
      for (const name of [
        'ancore:global-search-open',
        'ancore:notifications-open',
        'ancore:workspace-menu-open',
      ])
        window.removeEventListener(name, closeRightDrawer);
      clearTimeout(transition.current);
      stopResize(false);
      stopRightResize(false);
      document.body.classList.remove(
        'sidebar-resizing',
        'right-sidebar-resizing',
        'sidebar-open',
        'right-sidebar-open',
      );
      document.documentElement.classList.remove(
        'sidebar-transitioning',
        'sidebar-is-collapsing',
        'sidebar-is-expanding',
      );
    };
  }, []);
  useLayoutEffect(() => {
    for (const target of [document.documentElement, document.body]) {
      target.classList.toggle('sidebar-collapsed', collapsed && !mobile);
      target.classList.toggle('right-sidebar-collapsed', rightCollapsed);
    }
    document.body.classList.toggle('sidebar-open', opened && mobile);
    document.body.classList.toggle('right-sidebar-open', rightOpened && rightNarrow);
    const rightPanel = document.getElementById('app-right-sidebar');
    if (rightPanel) {
      rightPanel.hidden = !rightExpanded;
      rightPanel.classList.toggle('app-right-sidebar--visible', rightOpened && rightNarrow);
      if (rightExpanded) window.AncoreCustomSelect?.refresh(rightPanel);
    }
    if (mobile) document.documentElement.style.removeProperty('--sidebar-width');
    else document.documentElement.style.setProperty('--sidebar-width', `${clamped}px`);
    if (rightWidth !== null || rightClamped !== metrics.rightDefault)
      document.documentElement.style.setProperty(
        '--app-right-sidebar-user-width',
        `${rightClamped}px`,
      );
    else document.documentElement.style.removeProperty('--app-right-sidebar-user-width');
  }, [
    collapsed,
    mobile,
    opened,
    clamped,
    rightCollapsed,
    rightOpened,
    rightNarrow,
    rightExpanded,
    rightWidth,
    rightClamped,
    metrics.rightDefault,
  ]);
  useEffect(() => {
    if (mobile || collapsed) stopResize(false);
    if (!rightResizable) {
      stopRightResize(false);
      if (document.activeElement?.matches('[data-right-sidebar-resizer]'))
        document
          .querySelector<HTMLElement>('[data-right-sidebar-toggle]')
          ?.focus({ preventScroll: true });
    }
  }, [mobile, collapsed, rightResizable]);
  useEffect(() => {
    const rightDrawer = rightNarrow && rightOpened;
    if (!(opened && mobile) && !rightDrawer) return;
    const releaseBackground = acquireInert(
      document.querySelectorAll<HTMLElement>(
        // Keep the modal host available to dialogs opened from the right drawer.
        rightDrawer
          ? '.main-content > .page-container > :not(#app-page-modals), #app-sidebar'
          : '.main-content',
      ),
    );
    if (rightDrawer) document.getElementById('app-right-sidebar')?.focus({ preventScroll: true });
    const trap = (event: KeyboardEvent) => {
      if (event.defaultPrevented || document.querySelector('.tasks-modal.is-open')) return;
      if (rightDrawer && event.key === 'Escape') {
        event.preventDefault();
        closeRight();
        return;
      }
      if (event.key !== 'Tab') return;
      const items = [
        ...document.querySelectorAll<HTMLElement>(
          rightDrawer
            ? '#app-right-sidebar :is(a[href], button, input, select, textarea, [tabindex], [contenteditable="true"]), [data-right-sidebar-toggle]'
            : '#app-sidebar a[href], #app-sidebar button, [data-sidebar-collapse-toggle]',
        ),
      ].filter(
        (element) =>
          element.getClientRects().length &&
          element.tabIndex >= 0 &&
          !element.matches(':disabled') &&
          !element.closest('[hidden], [inert], [aria-hidden="true"]'),
      );
      const first = items[0],
        last = items[items.length - 1];
      const outside = rightDrawer && !items.some((item) => item === document.activeElement);
      if (event.shiftKey && (document.activeElement === first || outside)) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && (document.activeElement === last || outside)) {
        event.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener('keydown', trap);
    return () => {
      releaseBackground();
      document.removeEventListener('keydown', trap);
    };
  }, [opened, mobile, rightOpened, rightNarrow]);
  function closeRight() {
    setRightOpened(false);
    document
      .querySelector<HTMLElement>('[data-right-sidebar-toggle]')
      ?.focus({ preventScroll: true });
  }
  function toggleRight() {
    window.dispatchEvent(new CustomEvent('ancore:sidebar-toggle'));
    setOpened(false);
    if (rightNarrow) {
      setRightOpened((value) => !value);
      return;
    }
    if (!rightCollapsed && document.activeElement?.matches('[data-right-sidebar-resizer]'))
      document
        .querySelector<HTMLElement>('[data-right-sidebar-toggle]')
        ?.focus({ preventScroll: true });
    const next = !rightCollapsed;
    setRightCollapsed(next);
    write('ancoreRightSidebarCollapsed', next);
  }
  function toggle() {
    window.dispatchEvent(new CustomEvent('ancore:sidebar-toggle'));
    setRightOpened(false);
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
  function stopResize(commit: boolean) {
    const drag = resize.current;
    if (!drag) return;
    resize.current = undefined;
    document.body.classList.remove('sidebar-resizing');
    if (drag.target.hasPointerCapture(drag.id)) drag.target.releasePointerCapture(drag.id);
    if (commit && drag.value !== drag.width) {
      setWidth(drag.value);
      write('ancoreSidebarWidth', Math.round(drag.value));
    } else setWidth(drag.preference ?? 272);
  }
  function persistRight(value: number) {
    const next = Math.min(rightMax, Math.max(RIGHT_SIDEBAR_MIN, value));
    setRightWidth(next);
    write(RIGHT_SIDEBAR_STORAGE, Math.round(next));
  }
  function stopRightResize(commit: boolean) {
    const drag = rightResize.current;
    if (!drag) return;
    rightResize.current = undefined;
    document.body.classList.remove('right-sidebar-resizing');
    if (drag.target.hasPointerCapture(drag.id)) drag.target.releasePointerCapture(drag.id);
    if (commit && drag.value !== drag.width) {
      setRightWidth(drag.value);
      write(RIGHT_SIDEBAR_STORAGE, Math.round(drag.value));
    } else setRightWidth(drag.preference);
  }
  function resetRightWidth() {
    stopRightResize(false);
    setRightWidth(null);
    try {
      localStorage.removeItem(RIGHT_SIDEBAR_STORAGE);
    } catch {
      /* UI works without storage. */
    }
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
    rightNarrow,
    rightExpanded,
    rightResizable,
    rightOpened,
    toggleRight,
    closeRight,
    rightLabel: rightNarrow
      ? rightOpened
        ? 'Zamknij prawy panel boczny'
        : 'Otwórz prawy panel boczny'
      : rightCollapsed
        ? 'Rozwiń prawy panel boczny'
        : 'Zwiń prawy panel boczny',
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
        stopRightResize(false);
        event.currentTarget.setPointerCapture(event.pointerId);
        resize.current = {
          id: event.pointerId,
          x: event.clientX,
          width: clamped,
          scale: metrics.scale,
          value: clamped,
          target: event.currentTarget,
          preference: width,
        };
        document.body.classList.add('sidebar-resizing');
      },
      onPointerMove: (event: PointerEvent<HTMLDivElement>) => {
        if (resize.current?.id === event.pointerId) {
          event.preventDefault();
          const next = Math.min(
            max,
            Math.max(
              220,
              resize.current.width + (event.clientX - resize.current.x) / resize.current.scale,
            ),
          );
          resize.current.value = next;
          setWidth(next);
        }
      },
      onPointerUp: (event: PointerEvent<HTMLDivElement>) => {
        if (resize.current?.id === event.pointerId) {
          stopResize(true);
        }
      },
      onPointerCancel: () => stopResize(false),
      onLostPointerCapture: () => stopResize(false),
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
    rightResizer: {
      role: 'separator',
      'aria-orientation': 'vertical' as const,
      'aria-controls': 'app-right-sidebar',
      'aria-label': 'Zmień szerokość prawego panelu',
      'aria-valuemin': RIGHT_SIDEBAR_MIN,
      'aria-valuemax': rightMax,
      'aria-valuenow': Math.round(rightClamped),
      'aria-valuetext': `${Math.round(rightClamped)} pikseli`,
      tabIndex: rightResizable ? 0 : -1,
      onDoubleClick: resetRightWidth,
      onPointerDown: (event: PointerEvent<HTMLDivElement>) => {
        if (!rightResizable || event.button || !event.isPrimary) return;
        event.preventDefault();
        stopResize(false);
        event.currentTarget.setPointerCapture(event.pointerId);
        rightResize.current = {
          id: event.pointerId,
          x: event.clientX,
          width: rightClamped,
          scale: metrics.scale,
          value: rightClamped,
          target: event.currentTarget,
          preference: rightWidth,
        };
        document.body.classList.add('right-sidebar-resizing');
      },
      onPointerMove: (event: PointerEvent<HTMLDivElement>) => {
        const drag = rightResize.current;
        if (drag?.id !== event.pointerId) return;
        event.preventDefault();
        drag.value = rightSidebarDragWidth(drag.width, drag.x, event.clientX, drag.scale, rightMax);
        setRightWidth(drag.value);
      },
      onPointerUp: (event: PointerEvent<HTMLDivElement>) => {
        if (rightResize.current?.id === event.pointerId) stopRightResize(true);
      },
      onPointerCancel: () => stopRightResize(false),
      onLostPointerCapture: () => stopRightResize(false),
      onKeyDown: (event: React.KeyboardEvent<HTMLDivElement>) => {
        if (!rightResizable) return;
        const value =
          event.key === 'Home'
            ? RIGHT_SIDEBAR_MIN
            : event.key === 'End'
              ? rightMax
              : event.key === 'ArrowLeft'
                ? rightClamped + (event.shiftKey ? 24 : 8)
                : event.key === 'ArrowRight'
                  ? rightClamped - (event.shiftKey ? 24 : 8)
                  : undefined;
        if (value !== undefined) {
          event.preventDefault();
          persistRight(value);
        }
      },
    },
  };
}
