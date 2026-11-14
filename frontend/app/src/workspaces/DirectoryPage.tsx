import { Toolbar } from '../shared/DirectoryToolbar';
import { PageHeader } from '../shared/PageHeader';
import { EmptyState } from '../shared/EmptyState';
import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { Avatar } from '../shared/Avatar';
import { Icon } from '../shared/Icon';
import { LoadingOverlay } from '../shared/LoadingOverlay';
import { useNativeSubmitLoading } from '../shared/useNativeSubmitLoading';
import { LoadMore } from '../shared/LoadMore';
import { navigate, pageRequest, type Page, type PageProps } from '../shared/page';
import { errorMessage } from '../shared/api';
import { useDirtyGuard } from '../shared/useDirtyGuard';
import CreateDialog from './WorkspaceForm';
import SettingsPage from './SettingsPage';
import type { DirectoryData, Workspace } from './types';
import { FormDialog, type FormDialogData } from '../forms/FormDialog';
const columns = [
  ['name', 'Nazwa', 'briefcase-business'],
  ['code', 'Kod miejsca pracy', 'hash'],
  ['description', 'Opis', 'align-left'],
  ['members', 'Członkowie', 'users'],
  ['context', 'Twoja rola', 'panels-top-left'],
  ['status', 'Status', 'circle-dot'],
];
export default function DirectoryPage(props: PageProps) {
  const [data, setData] = useState(props.initial.data as DirectoryData),
    [query, setQuery] = useState(''),
    [limit, setLimit] = useState(20),
    [selected, setSelected] = useState<Set<string>>(new Set()),
    [create, setCreate] = useState(data.create_open),
    [deleteDialog, setDeleteDialog] = useState<FormDialogData | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('');
  const life = useRef(new AbortController()),
    sending = useRef(false),
    all = useRef<HTMLInputElement>(null),
    search = useRef<HTMLInputElement>(null),
    deleteReturnFocus = useRef<HTMLElement | null>(null);
  const switching = useNativeSubmitLoading();
  useEffect(() => () => life.current.abort(), []);
  useDirtyGuard(false, busy);
  const filtered = data.rows.filter((row) =>
      [
        row.name,
        row.code,
        row.description,
        String(row.members),
        row.role,
        row.active ? 'Aktywny' : 'Dostępny',
        row.is_default ? 'Domyślny' : '',
      ]
        .join(' ')
        .toLocaleLowerCase('pl')
        .includes(query.trim().toLocaleLowerCase('pl')),
    ),
    visible = filtered.slice(0, limit),
    selectedRows = visible.filter((row) => selected.has(row.id)),
    count = selectedRows.length,
    selectedWorkspace = count === 1 ? selectedRows[0] : null;
  const editTitle =
    count !== 1
      ? 'Zaznacz jeden Workspace.'
      : !selectedWorkspace?.can_manage
        ? 'Nie masz uprawnień do edycji tego Workspace.'
        : undefined;
  const deleteTitle =
    count !== 1
      ? 'Zaznacz jeden Workspace.'
      : !selectedWorkspace?.can_delete
        ? selectedWorkspace?.delete_disabled_reason ||
          'Nie masz uprawnień do usunięcia tego Workspace.'
        : undefined;
  useLayoutEffect(() => {
    if (all.current) all.current.indeterminate = count > 0 && count < visible.length;
  }, [count, visible.length]);
  async function load(url: string) {
    const response = await pageRequest<Page>(
      props.initial.api_url,
      url,
      props.csrfToken,
      life.current.signal,
    );
    if (response.type !== 'workspace-directory')
      throw new Error('Nie udało się odczytać Workspace.');
    if (!life.current.signal.aborted) setData(response.data as DirectoryData);
    return response.data as DirectoryData;
  }
  function toggle(id: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }
  async function switchTo(row: Workspace) {
    if (sending.current || !switching.start()) return;
    sending.current = true;
    setBusy(true);
    setError('');
    try {
      const result = await pageRequest<{ redirect: string }>(
        props.initial.api_url,
        row.switch_url,
        props.csrfToken,
        life.current.signal,
        new FormData(),
      );
      if (life.current.signal.aborted) return;
      flushSync(() => setBusy(false));
      if ((await navigate(result.redirect)) === false) switching.reset();
    } catch (e) {
      switching.reset();
      if (!life.current.signal.aborted) setError(errorMessage(e));
    } finally {
      sending.current = false;
      setBusy(false);
    }
  }
  async function openDelete(row: Workspace, trigger: HTMLElement) {
    if (sending.current || !row.can_delete || !row.delete_url) return;
    deleteReturnFocus.current = trigger;
    sending.current = true;
    setBusy(true);
    setError('');
    try {
      const result = await pageRequest<Page>(
        props.initial.api_url,
        row.delete_url,
        props.csrfToken,
        life.current.signal,
      );
      if (life.current.signal.aborted) return;
      if (result.type !== 'workspace-form') throw new Error('Nie udało się otworzyć formularza.');
      setDeleteDialog(result.data as FormDialogData);
    } catch (exception) {
      if (!life.current.signal.aborted) setError(errorMessage(exception));
    } finally {
      sending.current = false;
      if (!life.current.signal.aborted) setBusy(false);
    }
  }
  if (data.edit_open && data.team) {
    return (
      <SettingsPage
        key={data.team.id}
        team={data.team}
        initialTab={data.tab}
        backUrl={data.base_url}
        addOpen={data.add_open}
        api={props.initial.api_url}
        token={props.csrfToken}
        onClose={() => void navigate(data.base_url)}
        onSaved={navigate}
        reload={async (url) => {
          await load(url);
        }}
      />
    );
  }
  return (
    <div
      className="workplaces-page workplaces-settings-page workplaces-management"
      data-react-screen="workspace-directory"
      aria-busy={busy}
    >
      <LoadingOverlay active={switching.pending} label="Przełączanie Workspace…" />
      <a className="workplaces-skip-link" href="#workplaces-page-title">
        Przejdź do listy miejsc pracy
      </a>
      <main className="workplaces-settings-main">
        <section
          className="workplaces-workspace workplaces-console"
          aria-labelledby="workplaces-page-title"
        >
          <h1 id="workplaces-page-title" className="u-sr-only">
            Workspace
          </h1>
          <PageHeader
            className="workplaces-task-topbar"
            heading={
              <>
                <span className="tasks-topbar-title">Workspace</span>
              </>
            }
            actions={
              <>
                <button
                  type="button"
                  className="tasks-tag-topbar-button tasks-tag-topbar-button--project-add workplaces-create-button"
                  aria-haspopup="dialog"
                  aria-expanded={create}
                  disabled={busy}
                  onClick={() => setCreate(true)}
                >
                  <Icon name="plus" />
                  <span>Dodaj Workspace</span>
                </button>
              </>
            }
          />
          <Toolbar
            className="tasks-filterbar--project-directory workplaces-management__toolbar"
            actions={
              <>
                <button
                  type="button"
                  className="tasks-filter-button"
                  disabled={busy || !selectedWorkspace?.can_manage || !selectedWorkspace.edit_url}
                  title={editTitle}
                  data-workplaces-edit-selected=""
                  onClick={() => selectedWorkspace && void navigate(selectedWorkspace.edit_url)}
                >
                  <Icon name="pencil" />
                  Edytuj
                </button>
                <button
                  type="button"
                  className="tasks-filter-button"
                  disabled={busy || !selectedWorkspace?.can_delete || !selectedWorkspace.delete_url}
                  title={deleteTitle}
                  aria-haspopup="dialog"
                  data-workplaces-delete-selected=""
                  onClick={(event) =>
                    selectedWorkspace && void openDelete(selectedWorkspace, event.currentTarget)
                  }
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
                  ref={search}
                  type="search"
                  placeholder="Szukaj Workspace"
                  aria-label="Szukaj Workspace"
                  autoComplete="off"
                  disabled={busy}
                  value={query}
                  onChange={(e) => {
                    setQuery(e.target.value);
                    setLimit(20);
                    setSelected(new Set());
                  }}
                />
              </label>
            }
          />
          {error ? (
            <div className="tasks-modal__errors" role="alert">
              {error}
            </div>
          ) : null}
          <div className="workplaces-console__body">
            {filtered.length ? (
              <section className="workplaces-directory" aria-label="Lista miejsc pracy">
                <div className="workplaces-directory__table tasks-table-wrap tasks-board tasks-directory-board tasks-directory-sheet tasks-project-sheet tasks-project-sheet--selectable workplaces-project-sheet app-data-table">
                  <section
                    className="tasks-issue-group tasks-directory-group"
                    role="table"
                    aria-label="Workspace"
                  >
                    <div
                      className="workplaces-directory__head tasks-directory-header tasks-directory-sheet__header tasks-project-sheet__header app-table-header"
                      role="row"
                    >
                      <span
                        className="workplaces-directory__cell tasks-directory-header-select tasks-directory-sheet__cell tasks-project-sheet__cell"
                        data-column="select"
                        role="columnheader"
                        onClick={(e) => {
                          if (e.target === e.currentTarget) all.current?.click();
                        }}
                      >
                        <input
                          ref={all}
                          type="checkbox"
                          className="tasks-row-checkbox"
                          aria-label="Zaznacz wszystkie miejsca pracy"
                          checked={!!visible.length && count === visible.length}
                          disabled={busy || !visible.length}
                          onChange={(e) => {
                            const checked = e.target.checked;
                            setSelected((current) => {
                              const next = new Set(current);
                              visible.forEach((row) =>
                                checked ? next.add(row.id) : next.delete(row.id),
                              );
                              return next;
                            });
                          }}
                        />
                      </span>
                      <span
                        className="workplaces-directory__cell tasks-directory-sheet__cell tasks-project-sheet__cell"
                        data-column="action"
                        role="columnheader"
                        aria-label="Przełącz miejsce pracy"
                      >
                        <span className="u-sr-only">Przełącz miejsce pracy</span>
                      </span>

                      {columns.map(([key, label, icon]) => (
                        <span
                          key={key}
                          className="workplaces-directory__cell tasks-directory-sheet__cell tasks-project-sheet__cell"
                          data-column={key}
                          role="columnheader"
                        >
                          {label}
                          <Icon name={icon} />
                        </span>
                      ))}
                    </div>
                    <div
                      className="workplaces-directory__body tasks-issue-list tasks-project-list tasks-directory-list"
                      role="rowgroup"
                    >
                      {visible.map((row) => (
                        <article
                          key={row.id}
                          className={
                            'workplace-row tasks-issue-row tasks-project-row tasks-directory-row tasks-directory-sheet__row tasks-project-sheet__row app-table-row ' +
                            (row.active ? 'is-active ' : '') +
                            (selected.has(row.id) ? 'checked' : '')
                          }
                          role="row"
                          tabIndex={0}
                          aria-label={'Zarządzaj ' + row.name}
                          aria-current={row.active ? 'true' : undefined}
                          onClick={(e) => {
                            if (
                              !busy &&
                              !e.defaultPrevented &&
                              e.button === 0 &&
                              !e.ctrlKey &&
                              !e.metaKey &&
                              !e.altKey &&
                              !e.shiftKey &&
                              !(e.target as Element).closest(
                                'a,button,input,select,textarea,label,[data-column=select],[data-column=action]',
                              ) &&
                              !getSelection()?.toString()
                            )
                              void navigate(data.base_url + '?workspace=' + row.id + '&tab=main');
                          }}
                          onKeyDown={(e) => {
                            if (
                              !busy &&
                              e.target === e.currentTarget &&
                              ['Enter', ' '].includes(e.key)
                            ) {
                              e.preventDefault();
                              void navigate(data.base_url + '?workspace=' + row.id + '&tab=main');
                            }
                          }}
                        >
                          <span
                            className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                            data-column="select"
                            role="cell"
                            onClick={(e) => {
                              if (!busy && e.target === e.currentTarget) toggle(row.id);
                            }}
                          >
                            <input
                              type="checkbox"
                              className="tasks-row-checkbox"
                              aria-label={'Zaznacz miejsce pracy ' + row.name}
                              checked={selected.has(row.id)}
                              disabled={busy}
                              onChange={() => toggle(row.id)}
                            />
                          </span>
                          <div
                            className="workplaces-directory__cell workplace-row__open tasks-project-sheet__action tasks-directory-sheet__cell tasks-project-sheet__cell"
                            data-column="action"
                            role="cell"
                          >
                            <button
                              type="button"
                              className={
                                'tasks-project-sheet__edit-button workplace-table-icon-button ' +
                                (row.active ? 'workplace-table-icon-button--current' : '')
                              }
                              disabled={row.active || busy}
                              aria-label={
                                row.active
                                  ? row.name + ' — bieżący workspace'
                                  : 'Przełącz na ' + row.name
                              }
                              onClick={() => void switchTo(row)}
                            >
                              <Icon name={row.active ? 'check' : 'arrow-up-right'} />
                            </button>
                          </div>

                          <span
                            className="workplaces-directory__cell workplace-row__name tasks-directory-name tasks-row-title tasks-project-row-title tasks-directory-sheet__cell tasks-project-sheet__cell"
                            data-column="name"
                            role="cell"
                          >
                            <Avatar
                              space
                              data={row.avatar}
                              className="profile-avatar--workplace workplace-row__avatar"
                            />
                            <span className="tasks-row-title-main">
                              <a
                                className="tasks-row-title-text workplaces-management__select"
                                href={data.base_url + '?workspace=' + row.id + '&tab=main'}
                                aria-label={'Zarządzaj ' + row.name}
                              >
                                {row.name}
                              </a>
                              {row.active ? (
                                <span className="workplace-row__current-badge">Bieżący</span>
                              ) : null}
                              {row.is_default ? (
                                <span
                                  className="workplace-row__current-badge"
                                  title="Domyślny Workspace"
                                >
                                  Domyślny
                                </span>
                              ) : null}
                            </span>
                          </span>
                          <span
                            className="workplaces-directory__cell workplace-row__code tasks-project-sheet__company tasks-directory-sheet__cell tasks-project-sheet__cell"
                            data-column="code"
                            role="cell"
                            title={row.code}
                          >
                            {row.code || '—'}
                          </span>
                          <span
                            className="workplaces-directory__cell workplace-row__description tasks-project-sheet__company tasks-directory-sheet__cell tasks-project-sheet__cell"
                            data-column="description"
                            role="cell"
                          >
                            {row.description || '—'}
                          </span>
                          <span
                            className="workplaces-directory__cell workplace-row__members tasks-directory-assignee tasks-directory-sheet__cell tasks-project-sheet__cell"
                            data-column="members"
                            role="cell"
                          >
                            <Icon name="users" />
                            <a
                              href={data.base_url + '?workspace=' + row.id}
                              aria-label={'Zespół ' + row.name}
                            >
                              {row.members} {row.members === 1 ? 'członek' : 'członków'}
                            </a>
                          </span>
                          <span
                            className="workplaces-directory__cell workplace-row__context tasks-project-sheet__company tasks-directory-sheet__cell tasks-project-sheet__cell"
                            data-column="context"
                            role="cell"
                          >
                            {row.role}
                          </span>
                          <span
                            className={
                              'workplaces-directory__cell workplace-row__status tasks-project-sheet__status tasks-directory-sheet__cell tasks-project-sheet__cell ' +
                              (row.active ? 'is-active' : '')
                            }
                            data-column="status"
                            role="cell"
                          >
                            <span aria-hidden="true" />
                            {row.active ? 'Aktywny' : 'Dostępny'}
                          </span>
                        </article>
                      ))}
                    </div>
                  </section>
                  <LoadMore
                    loaded={visible.length}
                    total={filtered.length}
                    hasMore={visible.length < filtered.length}
                    onLoad={() => setLimit((current) => current + 20)}
                  />
                </div>
              </section>
            ) : (
              <EmptyState
                illustration="spaces"
                title={
                  data.rows.length ? 'Nie znaleziono Workspace.' : 'Nie masz jeszcze miejsca pracy.'
                }
                description={
                  data.rows.length
                    ? 'Zmień wyszukiwaną nazwę lub wyczyść wyszukiwanie.'
                    : 'Dodaj pierwsze miejsce pracy.'
                }
              />
            )}
          </div>
        </section>
      </main>
      {create ? (
        <CreateDialog
          schema={data.create_form}
          api={props.initial.api_url}
          token={props.csrfToken}
          action={data.base_url}
          onClose={() => setCreate(false)}
          onSaved={navigate}
        />
      ) : null}
      {deleteDialog ? (
        <FormDialog
          data={deleteDialog}
          api={props.initial.api_url}
          csrfToken={props.csrfToken}
          returnFocus={deleteReturnFocus.current}
          onClose={() => setDeleteDialog(null)}
          onSaved={(url) => {
            // Deletion can replace the active Workspace and invalidate its scoped API.
            window.location.assign(url);
          }}
        />
      ) : null}
    </div>
  );
}
