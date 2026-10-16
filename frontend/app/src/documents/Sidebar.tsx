import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { Icon } from '../shared/Icon';
import { DriveIcon } from './Icons';
import type { DirectoryData } from './types';
export function useSidebar() {
  const [compact, setCompact] = useState(() => matchMedia('(max-width: 1100px)').matches),
    [open, setOpen] = useState(false),
    [collapsed, setCollapsed] = useState(() => {
      try {
        return localStorage.getItem('ancore:documents:sidebar-collapsed:v1') === 'true';
      } catch {
        return false;
      }
    });
  const toggleRef = useRef<HTMLButtonElement>(null),
    panel = useRef<HTMLElement>(null);
  const expanded = compact ? open : !collapsed;
  useEffect(() => {
    const media = matchMedia('(max-width: 1100px)'),
      changed = () => {
        setCompact(media.matches);
        setOpen(false);
      };
    media.addEventListener('change', changed);
    return () => media.removeEventListener('change', changed);
  }, []);
  useLayoutEffect(() => {
    if (panel.current) {
      if (!expanded && panel.current.contains(document.activeElement)) toggleRef.current?.focus();
      panel.current.inert = !expanded;
    }
  }, [expanded]);
  useLayoutEffect(() => {
    if (compact && open)
      panel.current?.querySelector<HTMLButtonElement>('.documents-sidebar-close')?.focus();
  }, [compact, open]);
  function close() {
    setOpen(false);
    requestAnimationFrame(() => toggleRef.current?.focus());
  }
  function toggle() {
    if (compact) {
      setOpen(!open);
    } else {
      setCollapsed(!collapsed);
      try {
        localStorage.setItem('ancore:documents:sidebar-collapsed:v1', String(!collapsed));
      } catch {}
    }
  }
  return { compact, open, collapsed, expanded, toggleRef, panel, close, toggle };
}
export default function Sidebar({
  data,
  state,
  openModal,
  drop,
}: {
  data: DirectoryData;
  state: ReturnType<typeof useSidebar>;
  openModal: (url: string) => void;
  drop: string | null;
}) {
  return (
    <>
      <aside
        ref={state.panel}
        className="documents-sidebar"
        id="documents-sidebar"
        aria-label="Panel dysków"
        role={state.compact && state.open ? 'dialog' : undefined}
        aria-modal={state.compact && state.open ? true : undefined}
        onKeyDown={(event) => {
          if (!state.compact || !state.open) return;
          if (event.key === 'Escape') {
            event.preventDefault();
            state.close();
          }
          if (event.key === 'Tab') {
            const controls = [
              ...event.currentTarget.querySelectorAll<HTMLElement>('a[href],button:not(:disabled)'),
            ];
            if (event.shiftKey && document.activeElement === controls[0]) {
              event.preventDefault();
              controls.at(-1)?.focus();
            } else if (!event.shiftKey && document.activeElement === controls.at(-1)) {
              event.preventDefault();
              controls[0]?.focus();
            }
          }
        }}
      >
        <header className="documents-sidebar-header">
          <h2>Dyski</h2>
          <div className="documents-actions">
            <button
              type="button"
              className="tasks-icon-button documents-icon-button"
              aria-label="Dodaj dysk"
              onClick={() => {
                state.close();
                openModal(data.base_url + 'libraries/create/');
              }}
            >
              <Icon name="plus" />
            </button>
            <button
              type="button"
              className="tasks-icon-button documents-icon-button documents-sidebar-close"
              aria-label="Zamknij panel dysków"
              onClick={state.close}
            >
              <Icon name="x" />
            </button>
          </div>
        </header>
        <nav className="documents-sidebar-nav" aria-label="Dyski">
          <a className="tasks-rail-link" href={data.base_url}>
            <Icon name="layout-list" />
            <span>Wszystkie dyski</span>
          </a>
          {data.sidebar.map((item) => (
            <a
              key={item.id}
              className={`tasks-rail-link documents-sidebar-library-link ${data.library?.id === item.id ? 'is-active' : ''} ${drop === item.target ? 'is-document-drop-target' : ''}`}
              href={item.url}
              title={item.name}
              aria-current={data.library?.id === item.id ? 'page' : undefined}
              data-doc-target={item.target}
              data-doc-label={item.name}
            >
              <span className="documents-library-icon">
                <DriveIcon color={item.color} />
              </span>
              <span>{item.name}</span>
            </a>
          ))}
          {!data.sidebar.length ? (
            <p className="documents-sidebar-empty">Utwórz dysk, aby dodać foldery i pliki.</p>
          ) : null}
        </nav>
      </aside>
      <button
        type="button"
        className="documents-sidebar-backdrop"
        aria-label="Zamknij panel dysków"
        hidden={!state.compact || !state.open}
        onClick={state.close}
      />
    </>
  );
}
