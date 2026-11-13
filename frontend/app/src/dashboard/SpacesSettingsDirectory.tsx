import { useEffect, useRef, useState } from 'react';
import { Avatar, type AvatarData } from '../shared/Avatar';
import { DirectoryToolbar } from '../shared/DirectoryToolbar';
import { EmptyState } from '../shared/EmptyState';
import { Icon } from '../shared/Icon';
import { LoadMore } from '../shared/LoadMore';
import { PageHeader } from '../shared/PageHeader';
import type { PaginationData } from '../shared/Pagination';
import { navigate, pageRequest, type Page, type PageProps } from '../shared/page';
import { useLoadMorePage } from '../shared/useLoadMorePage';
import { errorMessage } from '../shared/api';
import { FormDialog, type FormDialogData } from '../forms/FormDialog';

interface Space {
  id: number;
  name: string;
  url: string;
  avatar: AvatarData;
  key: string;
  description: string;
  kind_label: string;
  template_label: string;
  item_count: number;
  can_manage: boolean;
  edit_url: string;
  delete_url: string;
}
interface Data {
  query: string;
  settings_spaces_url: string;
  create_url: string;
  pagination: PaginationData;
  spaces: Space[];
}
const headings = [
  ['name', 'NAZWA', 'layers'],
  ['key', 'KLUCZ', 'hash'],
  ['description', 'OPIS', 'align-left'],
  ['kind', 'RODZAJ', 'shapes'],
  ['template', 'SZABLON', 'layout-dashboard'],
  ['tasks_count', 'ZADANIA', 'list-checks'],
];
const cellClass = 'tasks-directory-sheet__cell tasks-project-sheet__cell';

export function SpacesSettingsDirectory({ initial, csrfToken }: PageProps) {
  const more = useLoadMorePage<Data>({ initial, csrfToken }, (value) => value.pagination.next);
  const { data } = more;
  const [selected, setSelected] = useState<Set<number>>(() => new Set());
  const [modal, setModal] = useState<FormDialogData | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const request = useRef<AbortController | null>(null);
  const returnFocus = useRef<HTMLElement | null>(null);
  const selectAll = useRef<HTMLInputElement>(null);
  const selectedSpaces = data.spaces.filter((space) => selected.has(space.id));
  const selectedCount = selectedSpaces.length;
  const selectedSpace = selectedCount === 1 ? selectedSpaces[0] : null;
  const canManage = !!selectedSpace?.can_manage && !initial.read_only;
  const actionTitle =
    selectedCount !== 1
      ? 'Zaznacz jedną przestrzeń.'
      : !canManage
        ? 'Nie masz uprawnień do zarządzania tą przestrzenią.'
        : undefined;
  useEffect(() => {
    setSelected(new Set());
    setModal(null);
    setBusy(false);
    setError('');
    return () => {
      request.current?.abort();
      request.current = null;
    };
  }, [initial]);
  useEffect(() => {
    if (selectAll.current)
      selectAll.current.indeterminate = selectedCount > 0 && selectedCount < data.spaces.length;
  }, [selectedCount, data.spaces.length]);

  function toggleSelection(id: number, checked = !selected.has(id)) {
    setSelected((current) => {
      const next = new Set(current);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  }

  async function openForm(url: string, trigger: HTMLElement) {
    if (!url || request.current || initial.read_only) return;
    returnFocus.current = trigger;
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    setError('');
    try {
      const result = await pageRequest<Page>(initial.api_url, url, csrfToken, controller.signal);
      if (controller.signal.aborted || request.current !== controller) return;
      if (result.type !== 'form') throw new Error('Nie udało się otworzyć formularza.');
      setModal(result.data as FormDialogData);
    } catch (exception) {
      if (!controller.signal.aborted && request.current === controller)
        setError(errorMessage(exception));
    } finally {
      if (request.current === controller) {
        request.current = null;
        setBusy(false);
      }
    }
  }

  return (
    <div
      className="tasks-page work-page settings-spaces-directory"
      data-react-screen="settings"
      data-settings-spaces-directory=""
      aria-busy={busy}
    >
      <PageHeader
        heading={
          <h1 className="tasks-topbar-title" id="settings-spaces-title">
            {initial.title}
          </h1>
        }
        actions={
          <button
            type="button"
            className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
            disabled={busy || more.loading || !!initial.read_only || !data.create_url}
            aria-haspopup="dialog"
            onClick={(event) => void openForm(data.create_url, event.currentTarget)}
          >
            <Icon name="plus" />
            Utwórz przestrzeń
          </button>
        }
      />
      <DirectoryToolbar
        method="get"
        action={data.settings_spaces_url.split('?')[0]}
        className="tasks-filterbar--project-directory settings-spaces-toolbar"
        actions={
          <>
            <button
              type="button"
              className="tasks-filter-button"
              disabled={busy || more.loading || !canManage || !selectedSpace?.edit_url}
              title={actionTitle}
              onClick={() => selectedSpace && void navigate(selectedSpace.edit_url)}
              data-settings-spaces-edit=""
            >
              <Icon name="pencil" />
              Edytuj
            </button>
            <button
              type="button"
              className="tasks-filter-button"
              disabled={busy || more.loading || !canManage || !selectedSpace?.delete_url}
              title={actionTitle}
              aria-haspopup="dialog"
              onClick={(event) =>
                selectedSpace && void openForm(selectedSpace.delete_url, event.currentTarget)
              }
              data-settings-spaces-delete=""
            >
              <Icon name="trash-2" />
              Usuń
            </button>
          </>
        }
        search={
          <label className="tasks-search-field tasks-project-search">
            <Icon name="search" />
            <input
              key={data.query}
              type="search"
              name="q"
              defaultValue={data.query}
              placeholder="Szukaj przestrzeni"
              aria-label="Szukaj przestrzeni"
              maxLength={120}
              autoComplete="off"
              data-settings-spaces-search=""
            />
          </label>
        }
      >
        <input type="hidden" name="section" value="spaces" />
      </DirectoryToolbar>
      {error ? (
        <p className="work-alert" role="alert">
          {error}
        </p>
      ) : null}
      <div className="settings-spaces-directory__body">
        {data.spaces.length ? (
          <div className="app-data-table tasks-table-wrap tasks-board tasks-directory-board tasks-directory-sheet tasks-project-sheet tasks-project-sheet--selectable settings-spaces-sheet">
            <section
              className="tasks-issue-group tasks-directory-group"
              role="table"
              aria-label="Lista przestrzeni"
            >
              <div
                className="tasks-directory-header tasks-directory-sheet__header tasks-project-sheet__header app-table-header"
                role="row"
              >
                <span
                  className={`tasks-directory-header-select ${cellClass}`}
                  data-column="select"
                  role="columnheader"
                >
                  <input
                    ref={selectAll}
                    type="checkbox"
                    className="tasks-row-checkbox tasks-select-all-checkbox tasks-directory-select-all"
                    checked={selectedCount === data.spaces.length}
                    disabled={busy}
                    aria-label="Zaznacz wszystkie przestrzenie"
                    data-settings-spaces-select-all=""
                    onChange={(event) =>
                      setSelected(
                        event.target.checked
                          ? new Set(data.spaces.map((space) => space.id))
                          : new Set(),
                      )
                    }
                  />
                </span>
                {headings.map(([key, label, icon]) => (
                  <span key={key} className={cellClass} data-column={key} role="columnheader">
                    {label}
                    <Icon name={icon} />
                  </span>
                ))}
              </div>
              <div
                className="tasks-issue-list tasks-project-list tasks-directory-list"
                role="rowgroup"
              >
                {data.spaces.map((space) => (
                  <article
                    key={space.id}
                    className={`tasks-issue-row tasks-project-row tasks-directory-row tasks-directory-sheet__row tasks-project-sheet__row app-table-row settings-spaces-row${selected.has(space.id) ? ' checked' : ''}`}
                    role="row"
                    tabIndex={0}
                    aria-label={`Ustawienia przestrzeni ${space.name}`}
                    data-settings-spaces-row=""
                    data-settings-space-url={space.url}
                    onClick={(event) => {
                      if (
                        busy ||
                        event.ctrlKey ||
                        event.metaKey ||
                        event.altKey ||
                        event.shiftKey ||
                        event.button !== 0
                      )
                        return;
                      if (
                        (event.target as Element).closest(
                          'a,button,input,label,select,textarea,[data-column="select"]',
                        )
                      )
                        return;
                      if (window.getSelection()?.toString()) return;
                      void navigate(space.url);
                    }}
                    onKeyDown={(event) => {
                      if (
                        event.target !== event.currentTarget ||
                        busy ||
                        !['Enter', ' '].includes(event.key)
                      )
                        return;
                      event.preventDefault();
                      void navigate(space.url);
                    }}
                  >
                    <span
                      className={cellClass}
                      data-column="select"
                      role="cell"
                      onClick={(event) => {
                        if (busy) return;
                        if (!(event.target as Element).closest('input')) toggleSelection(space.id);
                      }}
                    >
                      <input
                        type="checkbox"
                        className="tasks-row-checkbox"
                        value={space.id}
                        checked={selected.has(space.id)}
                        disabled={busy}
                        aria-label={`Zaznacz przestrzeń ${space.name}`}
                        data-settings-spaces-select=""
                        onChange={(event) => toggleSelection(space.id, event.target.checked)}
                      />
                    </span>
                    <span
                      className={`tasks-directory-name tasks-row-title tasks-project-row-title ${cellClass}`}
                      data-column="name"
                      role="cell"
                    >
                      <Avatar data={space.avatar} space className="settings-spaces-avatar" />
                      <span className="tasks-row-title-main">
                        <a className="tasks-row-title-text" href={space.url} title={space.name}>
                          {space.name}
                        </a>
                      </span>
                    </span>
                    {[
                      ['key', space.key],
                      ['description', space.description || '—'],
                      ['kind', space.kind_label],
                      ['template', space.template_label],
                      ['tasks_count', String(space.item_count)],
                    ].map(([key, value]) => (
                      <span
                        key={key}
                        className={cellClass}
                        data-column={key}
                        role="cell"
                        title={value}
                      >
                        {value}
                      </span>
                    ))}
                  </article>
                ))}
              </div>
            </section>
            <LoadMore
              loaded={data.pagination.end}
              total={data.pagination.count}
              hasMore={!!data.pagination.next}
              loading={more.loading}
              error={more.error}
              disabled={busy}
              onLoad={() => void more.loadMore()}
              label="Przestrzenie"
            />
          </div>
        ) : (
          <EmptyState
            illustration="spaces"
            title={
              data.query
                ? 'Nie znaleziono przestrzeni.'
                : 'Brak dostępnych przestrzeni w tym Workspace.'
            }
            description={
              data.query ? 'Zmień wyszukiwanie lub wyczyść wyszukiwaną nazwę.' : undefined
            }
          />
        )}
      </div>
      {modal ? (
        <FormDialog
          data={modal}
          returnFocus={returnFocus.current}
          api={initial.api_url}
          csrfToken={csrfToken}
          onClose={() => setModal(null)}
          onSaved={async (url) => {
            await navigate(url);
            setModal(null);
          }}
        />
      ) : null}
    </div>
  );
}
