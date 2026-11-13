import { useEffect, useRef, useState } from 'react';
import { Icon } from '../shared/Icon';
import { LoadMore } from '../shared/LoadMore';
import { RightSidebarContent } from '../shared/RightSidebarContent';
import { errorMessage } from '../shared/api';
import { type Page, PageError, pageRequest } from '../shared/page';
import { DriveIcon } from './Icons';
import type { DirectoryData } from './types';

export default function Sidebar({
  data,
  api,
  token,
  readOnly,
  busy,
  openModal,
  drop,
}: {
  data: DirectoryData;
  api: string;
  token: string;
  readOnly: boolean;
  busy: boolean;
  openModal: (url: string) => void;
  drop: string | null;
}) {
  const [items, setItems] = useState(data.sidebar),
    [pagination, setPagination] = useState(data.sidebar_window),
    [loading, setLoading] = useState(false),
    [error, setError] = useState('');
  const pending = useRef<AbortController>();
  useEffect(() => {
    setItems(data.sidebar);
    setPagination(data.sidebar_window);
    setLoading(false);
    setError('');
    return () => {
      pending.current?.abort();
      pending.current = undefined;
    };
  }, [data.sidebar, data.sidebar_window, api, token]);

  async function more() {
    if (pending.current || busy || !pagination?.has_next) return;
    const controller = new AbortController();
    pending.current = controller;
    setLoading(true);
    setError('');
    try {
      const result = await pageRequest<Page>(api, pagination.next_url, token, controller.signal);
      if (controller.signal.aborted || pending.current !== controller) return;
      if (result.type !== 'document-directory' || (result.data as DirectoryData).office)
        throw new Error('Nie udało się odczytać listy dysków.');
      const next = result.data as DirectoryData;
      setItems(next.sidebar);
      setPagination(next.sidebar_window);
    } catch (exception) {
      if (controller.signal.aborted || pending.current !== controller) return;
      if (exception instanceof PageError && [401, 403, 404].includes(exception.status)) {
        setItems([]);
      }
      setError(errorMessage(exception));
    } finally {
      if (pending.current === controller) {
        pending.current = undefined;
        setLoading(false);
      }
    }
  }

  return (
    <RightSidebarContent>
      <aside
        className="documents-sidebar documents-sidebar--global"
        id="documents-sidebar"
        aria-label="Panel dysków"
        aria-busy={loading}
      >
        <header className="documents-sidebar-header">
          <h2>Dyski</h2>
          {!readOnly ? (
            <button
              type="button"
              className="tasks-icon-button documents-icon-button"
              aria-label="Dodaj dysk"
              disabled={busy}
              onClick={() => openModal(data.base_url + 'libraries/create/')}
            >
              <Icon name="plus" />
            </button>
          ) : null}
        </header>
        <nav className="documents-sidebar-nav" aria-label="Dyski">
          {items.map((item) => (
            <a
              key={item.id}
              className={`tasks-rail-link documents-sidebar-library-link ${data.library?.id === item.id ? 'is-active' : ''} ${drop === item.target ? 'is-document-drop-target' : ''}`}
              href={item.url}
              title={item.name}
              aria-current={data.library?.id === item.id ? 'page' : undefined}
              data-doc-target={readOnly ? undefined : item.target}
              data-doc-label={item.name}
            >
              <span className="documents-library-icon">
                <DriveIcon color={item.color} />
              </span>
              <span>{item.name}</span>
            </a>
          ))}
          {!items.length && !error ? (
            <p className="documents-sidebar-empty">Brak dysków w tym Workspace.</p>
          ) : null}
          {pagination ? (
            <LoadMore
              label="Dyski w panelu"
              loaded={items.length}
              total={pagination.count}
              hasMore={pagination.has_next}
              loading={loading}
              disabled={busy}
              error={error}
              onLoad={() => void more()}
            />
          ) : null}
        </nav>
      </aside>
    </RightSidebarContent>
  );
}
