import { Toolbar } from '../shared/DirectoryToolbar';
import { LoadMore } from '../shared/LoadMore';
import { PageHeader } from '../shared/PageHeader';
import { PageTabs } from '../shared/PageTabs';
import { RightSidebarContent } from '../shared/RightSidebarContent';
import { statusColorStyle } from '../shared/status-color';
import { setPageLocation } from '../shared/page';
import { useEffect, useRef, useState } from 'react';
import { FieldControl, FormDialog, type Field, type FormDialogData } from '../forms/FormDialog';
import { Avatar } from '../shared/Avatar';
import { Icon } from '../shared/Icon';
import { Members } from '../shared/Members';
import { StatusGroup } from '../shared/StatusGroup';
import { type Page, type PageProps, navigate, pageRequest } from '../shared/page';
import { errorMessage } from '../shared/api';
import { copyText } from '../shared/clipboard';
import { Priority, ItemType } from '../spaces/Item';
import { dateLabel, type Item } from '../spaces/types';
import { ActivityItem, Attachments } from './Activity';
import CommentComposer from './CommentComposer';
import { Description } from './Description';
import SchemaDialog, { type DialogData } from './SchemaDialog';
import { useTaskSave } from './useTaskSave';
import { TaskWorkflowActions, TaskWorkflowStatus } from './TaskWorkflow';
import type { TaskData } from './types';
const SIDE = [
  'visibility',
  'priority',
  'tags',
  'work_type',
  'task_type',
  'task_group',
  'assignee',
  'start_at',
  'due_at',
  'reminder_at',
];
const taskField = (field: Field) => ({
  ...field,
  errors: [],
  attrs: { ...field.attrs, form: 'space-task-form' },
});
export default function TaskPage(props: PageProps) {
  const { initial, csrfToken } = props;
  const [data, setData] = useState(initial.data as TaskData),
    [schema, setSchema] = useState(() => ({
      ...(initial.data as TaskData).form,
      fields: (initial.data as TaskData).form.fields.map(taskField),
    })),
    [tab, setTab] = useState((initial.data as TaskData).tab),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [logLoading, setLogLoading] = useState(false),
    [logError, setLogError] = useState(''),
    [refreshFailed, setRefreshFailed] = useState(false),
    [dialog, setDialog] = useState<DialogData | null>(null),
    [childEditor, setChildEditor] = useState<FormDialogData | null>(null),
    [selected, setSelected] = useState<Set<number>>(new Set()),
    [sort, setSort] = useState(false),
    [logSelected, setLogSelected] = useState<Set<number>>(new Set()),
    [uploads, setUploads] = useState<File[]>([]);
  const form = useRef<HTMLFormElement>(null),
    dialogReturnFocus = useRef<HTMLElement | null>(null),
    files = useRef<HTMLInputElement>(null),
    life = useRef(new AbortController()),
    workLogURL = useRef(initial.url),
    logRequest = useRef<AbortController>(),
    latest = useRef(data),
    actionPending = useRef(false);
  latest.current = data;
  const saveProps = { ...props, initial: { ...initial, url: workLogURL.current } };
  const auto = useTaskSave(form, saveProps, setData, (validation) => {
    // New configuration fields may appear while this editor has an unsaved draft.
    // Keep existing control objects stable so their values and focus survive errors.
    setSchema((current) => {
      const names = new Set(current.fields.map((field) => field.name));
      const added = validation.fields.filter((field) => !names.has(field.name));
      return added.length
        ? {
            ...current,
            fields: [...current.fields, ...added.map(taskField)],
          }
        : current;
    });
  });
  useEffect(() => {
    if (!auto.dirty && !auto.pending) setUploads([]);
  }, [auto.dirty, auto.pending]);
  useEffect(
    () => () => {
      life.current.abort();
      logRequest.current?.abort();
    },
    [],
  );
  useEffect(() => {
    document.title = `${data.item.key} · ${data.item.title} | ancore`;
  }, [data.item.key, data.item.title]);
  async function refresh() {
    const page = await pageRequest<Page>(
      initial.api_url,
      workLogURL.current,
      csrfToken,
      life.current.signal,
    );
    const next = page.data as TaskData;
    auto.synchronize(next);
    setData(next);
    setRefreshFailed(false);
    setError('');
  }
  async function loadWorkLog() {
    if (!data.work_log.next || logRequest.current || actionPending.current || auto.pending) return;
    const controller = new AbortController();
    logRequest.current = controller;
    const previous = data.work_log;
    setLogLoading(true);
    setLogError('');
    try {
      const page = await pageRequest<Page>(
        initial.api_url,
        previous.next,
        csrfToken,
        controller.signal,
      );
      if (controller.signal.aborted || life.current.signal.aborted) return;
      if (page.type !== initial.type) throw new Error('Nie udało się odczytać dziennika pracy.');
      if (latest.current.work_log !== previous) return;
      const next = (page.data as TaskData).work_log;
      workLogURL.current = previous.next;
      setData((current) =>
        current.work_log === previous ? { ...current, work_log: next } : current,
      );
      setLogSelected(
        (current) =>
          new Set([...current].filter((id) => next.results.some((log) => log.id === id))),
      );
      const url = new URL(location.href);
      url.searchParams.delete('work_log_page');
      url.searchParams.set('work_log_limit', String(next.results.length));
      setPageLocation(url);
    } catch (exception) {
      if (!controller.signal.aborted && !life.current.signal.aborted)
        setLogError(errorMessage(exception));
    } finally {
      if (logRequest.current === controller) {
        logRequest.current = undefined;
        setLogLoading(false);
      }
    }
  }
  function refreshError(exception: unknown) {
    if (life.current.signal.aborted) return;
    setRefreshFailed(true);
    setError(`Zapisano zmiany, ale nie udało się odświeżyć zadania. ${errorMessage(exception)}`);
  }
  async function retryRefresh() {
    if (actionPending.current) return;
    actionPending.current = true;
    setBusy(true);
    setError('');
    try {
      await refresh();
    } catch (exception) {
      refreshError(exception);
    } finally {
      actionPending.current = false;
      setBusy(false);
    }
  }
  async function act(values: Record<string, string> | FormData, url = initial.url) {
    if (actionPending.current) return false;
    actionPending.current = true;
    setBusy(true);
    setError('');
    setRefreshFailed(false);
    try {
      if (!(await auto.save())) return false;
      const body = values instanceof FormData ? values : new FormData();
      if (!(values instanceof FormData))
        Object.entries(values).forEach(([key, value]) => body.set(key, value));
      const result = await pageRequest<{ redirect?: string }>(
        initial.api_url,
        url,
        csrfToken,
        life.current.signal,
        body,
      );
      if (body.get('action') === 'delete') {
        navigate(result.redirect || data.back_url);
        return true;
      }
      // The mutation is committed even when its follow-up read fails.
      try {
        await refresh();
      } catch (exception) {
        refreshError(exception);
      }
      return true;
    } catch (exception) {
      if (!life.current.signal.aborted) setError(errorMessage(exception));
      return false;
    } finally {
      actionPending.current = false;
      setBusy(false);
    }
  }
  function confirm(title: string, message: string, action: () => void) {
    window.showConfirmModal({
      title,
      message: window.escapeHtmlForModal(message),
      confirmText: 'Usuń',
      cancelText: 'Anuluj',
      onConfirm: action,
    });
  }
  async function openDialog(value: DialogData) {
    if (busy) return;
    dialogReturnFocus.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    if (await auto.save()) setDialog(value);
  }
  async function editChild(item: Item) {
    if (!item.editable || actionPending.current) return;
    dialogReturnFocus.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    actionPending.current = true;
    setBusy(true);
    setError('');
    try {
      if (!(await auto.save())) return;
      const page = await pageRequest<Page>(
        initial.api_url,
        item.edit_url,
        csrfToken,
        life.current.signal,
      );
      if (page.type !== 'form') throw new Error('Nie udało się otworzyć edycji podzadania.');
      const editor = page.data as FormDialogData;
      setChildEditor({
        ...editor,
        title: `Edytuj podzadanie ${item.key}`,
      });
    } catch (exception) {
      if (!life.current.signal.aborted) setError(errorMessage(exception));
    } finally {
      actionPending.current = false;
      setBusy(false);
    }
  }
  async function childSaved() {
    setChildEditor(null);
    await retryRefresh();
  }
  function openLog() {
    void openDialog({
      kind: 'log',
      title: 'Dodaj czas',
      schema: data.log_form,
      action: 'add_work_log',
      url: initial.url,
    });
  }
  function switchTab(key: string) {
    setTab(key);
    const url = new URL(location.href);
    url.searchParams.set('tab', key);
    setPageLocation(url.pathname + url.search);
  }
  function choose(item: Item, checked: boolean) {
    setSelected((current) => {
      const next = new Set(current);
      if (checked) next.add(item.task_id);
      else next.delete(item.task_id);
      return next;
    });
  }
  function removeChildren() {
    if (!selected.size) return;
    confirm('Usuń podzadania', `Usunąć zaznaczone podzadania (${selected.size})?`, () => {
      const values = new FormData();
      values.set('action', 'delete_subtasks');
      selected.forEach((id) => values.append('subtask_ids', String(id)));
      void act(values).then((ok) => {
        if (ok) setSelected(new Set());
      });
    });
  }
  const title = schema.fields.find((field) => field.name === 'title')!,
    description = schema.fields.find((field) => field.name === 'description')!,
    planningFields = schema.fields.filter(
      (field) => !['title', 'description', ...SIDE].includes(field.name),
    );
  const visiblePlanningField = (value: Field) =>
    value.name.startsWith('custom_') || !!auto.errors[value.name]?.length;
  function field(name: string) {
    const value = schema.fields.find((field) => field.name === name);
    if (!value) return null;
    return (
      <div className="tasks-issue-field">
        <span className="tasks-issue-field-label">
          <label htmlFor={value.id}>{value.label}</label>
        </span>
        <FieldControl field={value} bare />
        {auto.errors[name]?.map((message, index) => (
          <span className="tasks-modal__errors" role="alert" key={index}>
            {message}
          </span>
        ))}
      </div>
    );
  }
  const errorBanner =
    error || auto.error ? (
      <div className="tasks-error-banner" role="alert">
        <span>{error || auto.error}</span>
        {error && refreshFailed ? (
          <button
            type="button"
            className="btn btn-secondary"
            disabled={busy}
            onClick={() => void retryRefresh()}
          >
            Odśwież zadanie
          </button>
        ) : auto.error ? (
          <button
            type="button"
            className="btn btn-secondary"
            disabled={auto.pending}
            onClick={() => void auto.save()}
          >
            Spróbuj ponownie
          </button>
        ) : null}
      </div>
    ) : null;
  return (
    <div
      className={`tasks-page tasks-issue-page work-task-page ${data.can_edit ? '' : 'tasks-issue-form--readonly'}`}
      data-react-screen="space-task"
    >
      <div className="tasks-issue-shell">
        <PageHeader
          groupClassName="work-space-header"
          heading={
            <>
              <a
                className="tasks-issue-close"
                href={data.back_url}
                aria-label="Wróć do przestrzeni"
                title="Wróć do przestrzeni"
              >
                <Icon name="arrow-left" />
              </a>
              <h1 className="tasks-topbar-title work-space-title">{data.item.title}</h1>
            </>
          }
          actions={
            <>
              {tab === 'work-log' && data.can_edit ? (
                <button
                  type="button"
                  className="tasks-filter-button tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
                  disabled={busy}
                  onClick={() => openLog()}
                >
                  <Icon name="plus" />
                  <span>Dodaj czas</span>
                </button>
              ) : null}
            </>
          }
          navigation={
            <PageTabs className="work-tabs--views" role="tablist" label="Widok zadania">
              {data.tabs.map((nav, index) => (
                <button
                  key={nav.key}
                  type="button"
                  role="tab"
                  id={`task-tab-${nav.key}`}
                  aria-controls={`task-${nav.key}`}
                  aria-selected={tab === nav.key}
                  tabIndex={tab === nav.key ? 0 : -1}
                  onClick={() => switchTab(nav.key)}
                  onKeyDown={(event) => {
                    if (['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) {
                      event.preventDefault();
                      const target =
                        event.key === 'Home'
                          ? 0
                          : event.key === 'End'
                            ? data.tabs.length - 1
                            : (index + (event.key === 'ArrowRight' ? 1 : -1) + data.tabs.length) %
                              data.tabs.length;
                      switchTab(data.tabs[target].key);
                      document.getElementById(`task-tab-${data.tabs[target].key}`)?.focus();
                    }
                  }}
                >
                  <Icon name={nav.icon} />
                  {nav.label}
                </button>
              ))}
            </PageTabs>
          }
        />
        <span className="u-sr-only" role="status" aria-live="polite">
          {auto.notice}
        </span>
        {errorBanner}
        <form
          ref={form}
          id="space-task-form"
          className="react-task-form"
          onSubmit={(event) => {
            event.preventDefault();
            void auto.save();
          }}
        >
          <div className="tasks-issue-main">
            <main className="tasks-issue-primary">
              <div className="tasks-issue-primary-body">
                <section
                  className="tasks-issue-content tasks-issue-overview"
                  aria-label="Temat i opis zadania"
                  hidden={tab !== 'main'}
                >
                  <div className="tasks-issue-title-field">
                    <label className="u-sr-only" htmlFor={title.id}>
                      Tytuł
                    </label>
                    <FieldControl field={title} bare />
                    {auto.errors.title?.map((message) => (
                      <p className="tasks-modal__errors" role="alert" key={message}>
                        {message}
                      </p>
                    ))}
                  </div>
                  <div className="tasks-issue-description-field">
                    <label className="u-sr-only" htmlFor={description.id}>
                      Opis zadania
                    </label>
                    <Description field={description} />
                    {auto.errors.description?.map((message) => (
                      <p className="tasks-modal__errors" role="alert" key={message}>
                        {message}
                      </p>
                    ))}
                  </div>
                </section>
                <section
                  id="task-main"
                  className="tasks-issue-content"
                  role="tabpanel"
                  aria-labelledby="task-tab-main"
                  hidden={tab !== 'main'}
                >
                  {data.can_edit ? (
                    <>
                      <div className="tasks-issue-tool-row" aria-label="Narzędzia zadania">
                        <button
                          type="button"
                          className="tasks-issue-tool tasks-issue-tool--labelled"
                          disabled={busy}
                          onClick={() => files.current?.click()}
                        >
                          <Icon name="paperclip" />
                          <span>Dodaj załącznik</span>
                        </button>
                      </div>
                      <input
                        ref={files}
                        type="file"
                        name="files"
                        accept={data.attachment_accept}
                        multiple
                        hidden
                        disabled={busy}
                        onChange={(event) => setUploads([...(event.target.files || [])])}
                      />
                    </>
                  ) : null}
                  {uploads.length ? (
                    <div className="tasks-file-list" aria-live="polite">
                      {uploads.map((file, index) => (
                        <span className="tasks-attachment-card" key={index}>
                          <span className="tasks-attachment-name">{file.name}</span>
                          <button
                            type="button"
                            className="tasks-delete-attach-btn"
                            disabled={auto.pending}
                            aria-label={`Usuń oczekujący plik ${file.name}`}
                            onClick={() => {
                              const remaining = uploads.filter((_, position) => position !== index);
                              const transfer = new DataTransfer();
                              remaining.forEach((file) => transfer.items.add(file));
                              files.current!.files = transfer.files;
                              setUploads(remaining);
                              files.current!.dispatchEvent(new Event('change', { bubbles: true }));
                            }}
                          >
                            <Icon name="x" />
                          </button>
                        </span>
                      ))}
                    </div>
                  ) : null}
                  <Attachments
                    files={data.files}
                    editable={data.can_edit && !busy}
                    remove={(file) =>
                      confirm(
                        'Usuń załącznik',
                        `Usunąć załącznik „${file.name}”?`,
                        () => void act({ action: 'delete_file', file_id: String(file.id) }),
                      )
                    }
                  />
                  <section className="tasks-issue-activity" aria-label="Czat zadania">
                    <div className="tasks-issue-activity-head">
                      <h2>
                        <Icon name="messages-square" />
                        Czat
                      </h2>
                    </div>
                    {data.can_edit ? (
                      <CommentComposer data={data} pending={busy} send={(body) => act(body)} />
                    ) : null}
                    <div className="tasks-issue-feed" tabIndex={0} aria-label="Czat zadania">
                      {data.comments.length ? (
                        data.comments.map((item) => <ActivityItem key={item.id} item={item} />)
                      ) : (
                        <p className="tasks-issue-empty-feed">Brak komentarzy w zadaniu.</p>
                      )}
                    </div>
                  </section>
                </section>
                <section
                  id="task-subtasks"
                  className="tasks-issue-content tasks-issue-subtasks"
                  role="tabpanel"
                  aria-labelledby="task-tab-subtasks"
                  tabIndex={0}
                  hidden={tab !== 'subtasks'}
                >
                  <Toolbar
                    className="tasks-subtasks-toolbar app-toolbar--embedded"
                    aria-label="Narzędzia podzadań"
                    filters={
                      <>
                        <h2 className="tasks-subtasks-title">
                          <span>Podzadania ({data.children.length})</span>
                        </h2>
                        <button
                          type="button"
                          className="tasks-filter-button tasks-issue-tool"
                          aria-label="Sortuj podzadania"
                          onClick={() => setSort(!sort)}
                        >
                          <Icon name="arrow-down-wide-narrow" />
                        </button>
                      </>
                    }
                    actions={
                      data.can_edit ? (
                        <div className="tasks-subtasks-actions">
                          <button
                            type="button"
                            className="tasks-filter-button tasks-issue-tool"
                            aria-label="Usuń zaznaczone podzadania"
                            disabled={busy}
                            onClick={removeChildren}
                          >
                            <Icon name="trash-2" />
                          </button>
                          <button
                            type="button"
                            className="tasks-filter-button tasks-issue-tool"
                            aria-label="Dodaj podzadanie"
                            disabled={busy}
                            onClick={() =>
                              void openDialog({
                                kind: 'subtask',
                                title: 'Dodaj podzadanie',
                                schema: data.subtask_form,
                                action: 'create_subtask_modal',
                                url: initial.url,
                              })
                            }
                          >
                            <Icon name="plus" />
                          </button>
                        </div>
                      ) : null
                    }
                  />
                  {data.children.length ? (
                    <div className="tasks-table-wrap tasks-board tasks-subtasks-board">
                      {data.statuses.map((status) => {
                        const children = data.children.filter((item) => item.status === status.key);
                        return children.length ? (
                          <StatusGroup
                            key={status.key}
                            label={status.label}
                            category={status.category}
                            color={status.color}
                            count={children.length}
                          >
                            <div className="tasks-issue-list">
                              {(sort
                                ? [...children].sort((a, b) => a.title.localeCompare(b.title, 'pl'))
                                : children
                              ).map((item) => (
                                <article
                                  className={`tasks-issue-row work-issue-row ${item.category === 'closed' ? 'completed' : ''} ${selected.has(item.task_id) ? 'checked' : ''}`}
                                  key={item.id}
                                >
                                  <input
                                    type="checkbox"
                                    className="tasks-row-checkbox"
                                    aria-label={`Zaznacz ${item.key} · ${item.title}`}
                                    checked={selected.has(item.task_id)}
                                    onChange={(event) => choose(item, event.target.checked)}
                                  />
                                  <Priority value={item.priority} label={item.priority_label} />
                                  <a
                                    href={item.editable ? item.edit_url : undefined}
                                    className="work-item-key"
                                    aria-haspopup={item.editable ? 'dialog' : undefined}
                                    aria-disabled={item.editable && busy ? true : undefined}
                                    title={
                                      item.editable ? `Edytuj podzadanie ${item.key}` : undefined
                                    }
                                    onClick={(event) => {
                                      event.preventDefault();
                                      void editChild(item);
                                    }}
                                  >
                                    {item.key}
                                  </a>
                                  <span
                                    className={`status-indicator status-${item.category}`}
                                    style={statusColorStyle(item.status_color)}
                                    title={item.status_label}
                                  />
                                  <a
                                    href={item.editable ? item.edit_url : undefined}
                                    className="tasks-row-title"
                                    aria-haspopup={item.editable ? 'dialog' : undefined}
                                    aria-disabled={item.editable && busy ? true : undefined}
                                    title={
                                      item.editable ? `Edytuj podzadanie ${item.key}` : undefined
                                    }
                                    onClick={(event) => {
                                      event.preventDefault();
                                      void editChild(item);
                                    }}
                                  >
                                    <span className="tasks-row-title-content">
                                      <span className="tasks-row-title-main">
                                        <span className="tasks-row-title-text">{item.title}</span>
                                      </span>
                                    </span>
                                  </a>
                                  <ItemType item={item} />
                                  <span
                                    className="tasks-row-tags"
                                    title={`Tagi: ${item.tags_count}`}
                                  >
                                    <Icon name="tag" />
                                    {item.tags_count}
                                  </span>
                                  <span
                                    className="tasks-row-attachments"
                                    title={`Załączniki: ${item.attachments_count}`}
                                  >
                                    <Icon name="paperclip" />
                                    {item.attachments_count}
                                  </span>
                                  <span
                                    className={`tasks-row-date tasks-row-due tasks-row-due--${item.due_urgency}`}
                                    title={
                                      item.due_at ? dateLabel(item.due_at, true) : 'Brak terminu'
                                    }
                                  >
                                    {item.due_at ? <Icon name="flame" /> : null}
                                  </span>
                                </article>
                              ))}
                            </div>
                          </StatusGroup>
                        ) : null;
                      })}
                    </div>
                  ) : (
                    <p className="tasks-issue-empty-feed">Brak podzadań.</p>
                  )}
                </section>
                <section
                  id="task-work-log"
                  className="tasks-work-log tasks-issue-content"
                  role="tabpanel"
                  aria-labelledby="task-tab-work-log"
                  tabIndex={0}
                  hidden={tab !== 'work-log'}
                >
                  <div className="tasks-work-log-summary">
                    <span>
                      Łącznie: <strong>{data.work_log.total_minutes} min</strong> (
                      {data.work_log.total_label})
                    </span>
                    <span>Wpisy: {data.work_log.count}</span>
                  </div>
                  {data.work_log.results.length ? (
                    <div
                      className={`tasks-table-wrap tasks-board app-data-table tasks-directory-board tasks-directory-sheet tasks-project-sheet tasks-project-sheet--selectable tasks-work-log-sheet ${data.can_edit ? '' : 'tasks-work-log-sheet--readonly'}`}
                    >
                      <section
                        className="tasks-directory-group"
                        role="table"
                        aria-label="Wpisy dziennika pracy"
                      >
                        <div className="app-table-header tasks-directory-header" role="row">
                          <span
                            className="tasks-directory-header-select tasks-directory-sheet__cell tasks-project-sheet__cell"
                            data-column="select"
                            role="columnheader"
                          >
                            <input
                              type="checkbox"
                              className="tasks-row-checkbox"
                              aria-label="Zaznacz wszystkie wpisy w widocznej liście"
                              checked={data.work_log.results.every((log) =>
                                logSelected.has(log.id),
                              )}
                              onChange={(event) =>
                                setLogSelected(
                                  event.target.checked
                                    ? new Set(data.work_log.results.map((log) => log.id))
                                    : new Set(),
                                )
                              }
                            />
                          </span>

                          {[
                            ['author', 'Kto dodał czas', 'user-round'],
                            ['duration', 'Czas (min)', 'clock'],
                            ['started_at', 'Rozpoczęcie', 'calendar-days'],
                            ['ended_at', 'Zakończenie', 'calendar-clock'],
                            ['description', 'Opis', 'align-left'],
                          ].map(([key, label, icon]) => (
                            <span
                              key={key}
                              className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                              data-column={key}
                              role="columnheader"
                            >
                              <Icon name={icon} />
                              {label}
                            </span>
                          ))}
                        </div>
                        <div className="tasks-issue-list tasks-directory-list" role="rowgroup">
                          {data.work_log.results.map((log) => (
                            <article
                              className={`tasks-issue-row app-table-row tasks-directory-row ${logSelected.has(log.id) ? 'checked' : ''}`}
                              role="row"
                              key={log.id}
                            >
                              <span
                                data-column="select"
                                className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                                role="cell"
                              >
                                <input
                                  type="checkbox"
                                  className="tasks-row-checkbox"
                                  aria-label={`Zaznacz wpis z ${dateLabel(log.started_at, true)} — ${log.author}`}
                                  checked={logSelected.has(log.id)}
                                  onChange={(event) =>
                                    setLogSelected((current) => {
                                      const next = new Set(current);
                                      if (event.target.checked) next.add(log.id);
                                      else next.delete(log.id);
                                      return next;
                                    })
                                  }
                                />
                              </span>

                              <div
                                data-column="author"
                                role="cell"
                                className="tasks-directory-sheet__cell tasks-project-sheet__cell tasks-directory-assignee"
                              >
                                <Avatar data={log.avatar} className="tasks-directory-avatar" />
                                <span className="tasks-row-title-text">{log.author}</span>
                              </div>
                              <span
                                data-column="duration"
                                role="cell"
                                className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                              >
                                {log.duration_minutes} min
                              </span>
                              <time
                                data-column="started_at"
                                role="cell"
                                className="tasks-directory-sheet__cell tasks-project-sheet__cell tasks-project-sheet__date"
                                dateTime={log.started_at}
                              >
                                {dateLabel(log.started_at, true)}
                              </time>
                              <time
                                data-column="ended_at"
                                role="cell"
                                className="tasks-directory-sheet__cell tasks-project-sheet__cell tasks-project-sheet__date"
                                dateTime={log.ended_at}
                              >
                                {dateLabel(log.ended_at, true)}
                              </time>
                              <span
                                data-column="description"
                                role="cell"
                                className="tasks-directory-sheet__cell tasks-project-sheet__cell tasks-project-sheet__description"
                              >
                                <span className="tasks-row-title-text" title={log.description}>
                                  {log.description}
                                </span>
                              </span>
                            </article>
                          ))}
                        </div>
                      </section>
                    </div>
                  ) : (
                    <div className="documents-empty tasks-work-log-empty">
                      <h3>Brak wpisów w dzienniku pracy</h3>
                      <p>Dodaj czas, aby zapisać pracę wykonaną nad tym zadaniem.</p>
                    </div>
                  )}
                  <LoadMore
                    loaded={data.work_log.results.length}
                    total={data.work_log.count}
                    hasMore={!!data.work_log.next}
                    loading={logLoading}
                    disabled={busy || auto.pending}
                    error={logError}
                    onLoad={() => void loadWorkLog()}
                    label="wpisy"
                  />
                </section>
                <section
                  id="task-members"
                  className="tasks-issue-content"
                  role="tabpanel"
                  aria-labelledby="task-tab-members"
                  hidden={tab !== 'members'}
                >
                  <Toolbar
                    className="workplace-edit-modal__team-toolbar app-toolbar--embedded"
                    filters={
                      <span className="workplaces-management__count">
                        {data.item.title} · Członkowie: {data.team.members.length}
                      </span>
                    }
                    actions={
                      data.team.can_manage ? (
                        <button
                          type="button"
                          className="tasks-filter-button"
                          disabled={busy || data.visibility === 'public'}
                          onClick={() =>
                            void openDialog({
                              kind: 'share',
                              title: 'Udostępnij zadanie',
                              schema: data.team.share_form,
                              action: 'share',
                              url: data.team_url,
                            })
                          }
                        >
                          <Icon name="plus" />
                          <span>Udostępnij</span>
                        </button>
                      ) : null
                    }
                  />
                  {data.visibility === 'public' ? (
                    <p className="workplace-team__hint">
                      Zadanie publiczne dziedziczy dostęp z przestrzeni i zadania nadrzędnego. Aby
                      udostępniać wybranym osobom, zapisz widoczność „Prywatne” w prawym panelu.
                    </p>
                  ) : null}
                  <Members members={data.team.members} busy={busy} />
                </section>
                <section
                  id="task-history"
                  className="tasks-issue-content"
                  role="tabpanel"
                  aria-labelledby="task-tab-history"
                  tabIndex={0}
                  hidden={tab !== 'history'}
                >
                  <div className="tasks-issue-feed" tabIndex={0} aria-label="Historia zadania">
                    {data.history.length ? (
                      data.history.map((item) => <ActivityItem key={item.id} item={item} />)
                    ) : (
                      <p className="tasks-issue-empty-feed">Brak historii zmian w zadaniu.</p>
                    )}
                  </div>
                </section>
              </div>
            </main>
            <RightSidebarContent>
              <div
                className={`work-task-sidebar ${data.can_edit ? '' : 'tasks-issue-form--readonly'}`}
              >
                <aside className="tasks-issue-sidebar" aria-label="Szczegóły zadania">
                  <div className="work-task-sidebar__feedback">{errorBanner}</div>
                  <TaskWorkflowActions
                    item={data.item}
                    canEdit={data.can_edit}
                    disabled={busy || auto.pending || auto.refreshRequired}
                    pending={auto.pending && !!auto.requestedStatus}
                    requestedStatus={auto.requestedStatus}
                    onTransition={(status) => void auto.changeStatus(status)}
                    errors={auto.errors.status}
                  />
                  <section className="tasks-issue-side-section" aria-label="Widoczność zadania">
                    {field('visibility')}
                  </section>
                  <section className="tasks-issue-side-section" aria-label="Właściwości zadania">
                    <TaskWorkflowStatus item={data.item} />
                    {['priority', 'assignee', 'work_type', 'task_type', 'task_group', 'tags'].map(
                      (name) => (
                        <div key={name} className="react-field-slot">
                          {field(name)}
                        </div>
                      ),
                    )}
                  </section>
                  <section
                    className="tasks-issue-side-section"
                    aria-label="Pola dodatkowe i planowanie"
                    hidden={!planningFields.some(visiblePlanningField)}
                  >
                    {planningFields.map((value) => (
                      <div hidden={!visiblePlanningField(value)} key={value.name}>
                        {field(value.name)}
                      </div>
                    ))}
                  </section>
                  <section className="tasks-issue-side-section" aria-label="Terminy zadania">
                    {field('start_at')}
                    {field('due_at')}
                    {field('reminder_at')}
                  </section>
                  <section className="tasks-issue-side-section" aria-label="Informacje o zadaniu">
                    <div className="tasks-issue-field">
                      <span className="tasks-issue-field-label">ID zadania</span>
                      <strong className="tasks-issue-code">
                        <span className="tasks-issue-code__value">{data.item.key}</span>
                        <span className="tasks-issue-code__actions">
                          <button
                            type="button"
                            className="tasks-issue-code__button"
                            aria-label="Kopiuj ID zadania"
                            onClick={() => {
                              void copyText(data.item.key)
                                .then(() =>
                                  window.showNotification?.('Skopiowano ID zadania.', 'success'),
                                )
                                .catch(() => setError('Nie udało się skopiować ID.'));
                            }}
                          >
                            <Icon name="copy" />
                          </button>
                        </span>
                      </strong>
                    </div>
                    <div className="tasks-issue-field">
                      <span className="tasks-issue-field-label">Utworzył</span>
                      <strong className="tasks-issue-person">
                        {data.created_by ? (
                          <>
                            <Avatar
                              data={data.created_by.avatar}
                              className="tasks-issue-mini-avatar"
                            />
                            {data.created_by.name}
                          </>
                        ) : (
                          'System'
                        )}
                      </strong>
                    </div>
                    <div className="tasks-issue-field">
                      <span className="tasks-issue-field-label">Utworzono</span>
                      <strong>{dateLabel(data.created_at, true)}</strong>
                    </div>
                    <div className="tasks-issue-field">
                      <span className="tasks-issue-field-label">Zamknięto</span>
                      <strong className="tasks-issue-muted">
                        {dateLabel(data.completion_date, true) || 'Nie zamknięto'}
                      </strong>
                    </div>
                  </section>
                </aside>
              </div>
            </RightSidebarContent>
          </div>
        </form>
      </div>
      {dialog ? (
        <SchemaDialog
          key={dialog.kind + String(dialog.values?.id || '')}
          dialog={dialog}
          returnFocus={dialogReturnFocus.current}
          api={initial.api_url}
          csrfToken={csrfToken}
          onClose={() => setDialog(null)}
          onSaved={refresh}
        />
      ) : null}
      {childEditor ? (
        <FormDialog
          key={childEditor.action}
          data={childEditor}
          returnFocus={dialogReturnFocus.current}
          api={initial.api_url}
          csrfToken={csrfToken}
          onClose={() => setChildEditor(null)}
          onSaved={childSaved}
        />
      ) : null}
    </div>
  );
}
