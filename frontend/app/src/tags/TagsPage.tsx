import {
  type CSSProperties,
  type ReactNode,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from 'react';
import { Avatar } from '../shared/Avatar';
import { Dropdown } from '../shared/Dropdown';
import { DirectoryColumnManager, useDirectoryColumns } from '../shared/DirectoryColumns';
import { Icon } from '../shared/Icon';
import { EmptyState } from '../shared/EmptyState';
import { Modal } from '../shared/Modal';
import { type PageProps, navigate } from '../shared/page';
import { Resize } from '../shared/table';
import { usePageActions } from '../shared/usePageActions';
import { FormDialog, type FormDialogData } from '../forms/FormDialog';
import { dateLabel } from '../spaces/types';
import NotesDialog from './NotesDialog';
import type { Tag, TagsData } from './types';

const columns = [
  { key: 'select', label: 'Zaznaczenie', icon: '', width: 40 },
  { key: 'menu', label: 'Działania', icon: '', width: 40 },
  { key: 'action', label: 'Edytuj', icon: '', width: 40 },
  { key: 'info', label: 'Informacje', icon: '', width: 40 },
  { key: 'notes', label: 'Notatki', icon: '', width: 40 },
  { key: 'tag_name', label: 'Nazwa tagu', icon: 'tag', width: 250 },
  { key: 'tag_code', label: 'Kod tagu', icon: 'hash', width: 250 },
  { key: 'tag_type', label: 'Typ', icon: 'shapes', width: 140 },
  { key: 'tag_visual', label: 'Kolor / ikona', icon: 'palette', width: 160 },
  { key: 'priority', label: 'Priorytet', icon: 'flag', width: 140 },
  { key: 'scope', label: 'Zakres', icon: 'target', width: 140 },
  { key: 'owner', label: 'Właściciel', icon: 'user-round', width: 190 },
  { key: 'status', label: 'Status', icon: 'circle-dot', width: 140 },
  { key: 'description', label: 'Opis', icon: 'align-left', width: 320 },
  { key: 'usage_notes', label: 'Użycie', icon: 'notebook-pen', width: 260 },
  { key: 'automation', label: 'Automatyka', icon: 'workflow', width: 260 },
  { key: 'related_tags', label: 'Powiązane', icon: 'tags', width: 220 },
  { key: 'task_count', label: 'Zadania', icon: 'list-checks', width: 250 },
  { key: 'created_at', label: 'Data utworzenia', icon: 'calendar-days', width: 130 },
  { key: 'spacer', label: '', icon: '', width: 0 },
];
const hidden = ['action', 'info', 'notes'];
const filters = [
  ['status', 'statuses', 'Status', 'circle-dot'],
  ['category', 'categories', 'Typ', 'layers-3'],
  ['scope', 'scopes', 'Zakres', 'target'],
  ['owner', 'owners', 'Właściciel', 'circle-user-round'],
  ['priority', 'priorities', 'Priorytet', 'chart-no-axes-column-increasing'],
];
export default function TagsPage(props: PageProps) {
  const { initial, csrfToken } = props;
  const [data, setData] = useState(initial.data as TagsData),
    [selected, setSelected] = useState<Set<number>>(new Set()),
    [modal, setModal] = useState<FormDialogData | null>((initial.data as TagsData).modal),
    [info, setInfo] = useState<Tag | null>(null),
    [notes, setNotes] = useState<number | null>(null),
    [query, setQuery] = useState(data.query);
  const actions = usePageActions(props),
    all = useRef<HTMLInputElement>(null),
    aggregate = useRef<HTMLDetailsElement>(null),
    timer = useRef<ReturnType<typeof setTimeout>>();
  const sizing = useDirectoryColumns(
    columns,
    location.pathname.startsWith('/workplaces/') ? 'workplaces' : 'tasks',
    hidden,
  );
  useLayoutEffect(() => {
    if (all.current)
      all.current.indeterminate = selected.size > 0 && selected.size < data.tags.length;
  }, [selected, data.tags.length]);
  useEffect(() => () => clearTimeout(timer.current), []);
  useEffect(() => {
    const close = (event: Event) => {
      if (!aggregate.current?.contains(event.target as Node))
        aggregate.current?.removeAttribute('open');
    };
    const escape = (event: KeyboardEvent) => {
      if (
        event.key === 'Escape' &&
        aggregate.current?.open &&
        !aggregate.current.querySelector('.tasks-filter-dropdown.is-open')
      ) {
        aggregate.current.removeAttribute('open');
        aggregate.current.querySelector('summary')?.focus();
      }
    };
    document.addEventListener('click', close);
    document.addEventListener('keydown', escape);
    return () => {
      document.removeEventListener('click', close);
      document.removeEventListener('keydown', escape);
    };
  }, []);
  function change(values: Record<string, string>) {
    clearTimeout(timer.current);
    const url = new URL(initial.url, location.origin);
    url.searchParams.set('q', query);
    url.searchParams.delete('page');
    Object.entries(values).forEach(([key, value]) =>
      value ? url.searchParams.set(key, value) : url.searchParams.delete(key),
    );
    navigate(url.pathname + url.search);
  }
  function edit(tag?: Tag) {
    if (!data.form || actions.busy) return;
    const form = {
      ...data.form,
      submit_label: tag ? 'Zapisz zmiany' : 'Utwórz tag',
      fields: data.form.fields.map((field) => ({
        ...field,
        errors: [],
        value: tag
          ? ((tag[field.name as keyof Tag] as string | string[] | null) ?? field.value)
          : field.value,
        choices:
          field.name === 'related_tags' && tag
            ? field.choices?.filter((choice) => choice.value !== String(tag.id))
            : field.choices,
      })),
    };
    setModal({
      title: tag ? 'Edytuj tag' : 'Nowy tag',
      action: initial.url,
      return_url: initial.url,
      values: { action: tag ? 'edit_tag' : 'create_tag', tag_id: tag ? String(tag.id) : '' },
      form,
    });
  }
  function remove(tags: Tag[]) {
    window.showConfirmModal({
      title: tags.length === 1 ? 'Usuń tag' : 'Usuń tagi',
      message: window.escapeHtmlForModal(
        tags.length === 1
          ? `Usunąć tag „${tags[0].name}”?`
          : `Usunąć zaznaczone tagi (${tags.length})?`,
      ),
      confirmText: 'Usuń',
      cancelText: 'Anuluj',
      confirmClass: 'btn-danger',
      onConfirm: () =>
        void actions.act(initial.url, {
          action: 'delete_tag',
          tag_ids: tags.map((tag) => String(tag.id)),
        }),
    });
  }
  // Repeated form values are sent by the same domain endpoint, also for bulk delete.
  const selectedTags = data.tags.filter((tag) => selected.has(tag.id));
  function cell(tag: Tag, key: string): ReactNode {
    if (key === 'select')
      return (
        <input
          key="select"
          type="checkbox"
          className="tasks-row-checkbox tasks-directory-sheet__cell tasks-tag-sheet__cell"
          data-column="select"
          aria-label={`Zaznacz tag ${tag.name}`}
          checked={selected.has(tag.id)}
          onChange={(event) =>
            setSelected((current) => {
              const next = new Set(current);
              if (event.target.checked) next.add(tag.id);
              else next.delete(tag.id);
              return next;
            })
          }
        />
      );
    if (key === 'menu')
      return (
        <Dropdown
          label={`Działania tagu ${tag.name}`}
          className="tasks-row-actions"
          triggerClassName="tasks-project-sheet__edit-button"
          menuClass="tasks-project-menu"
          trigger={<Icon name="menu" />}
        >
          {(close) => (
            <div>
              {data.can_edit ? (
                <button
                  className="tasks-project-menu-button"
                  disabled={actions.busy}
                  onClick={() => {
                    close();
                    edit(tag);
                  }}
                >
                  <Icon name="pencil" />
                  Edytuj tag
                </button>
              ) : null}
              <button
                className="tasks-project-menu-button"
                onClick={() => {
                  close();
                  setInfo(tag);
                }}
              >
                <Icon name="info" />
                Informacje o tagu
              </button>
              <button
                className="tasks-project-menu-button"
                onClick={() => {
                  close();
                  setNotes(tag.id);
                }}
              >
                <Icon name="file-text" />
                Notatki tagu
              </button>
              {data.can_edit ? (
                <button
                  className="tasks-project-menu-button tasks-project-menu-button--danger"
                  disabled={actions.busy}
                  onClick={() => {
                    close();
                    remove([tag]);
                  }}
                >
                  <Icon name="trash-2" />
                  Usuń tag
                </button>
              ) : null}
            </div>
          )}
        </Dropdown>
      );
    if (['action', 'info', 'notes'].includes(key))
      return key === 'action' && !data.can_edit ? null : (
        <button
          className="tasks-project-sheet__edit-button"
          aria-label={`${key === 'action' ? 'Edytuj tag' : key === 'info' ? 'Informacje o tagu' : 'Notatki tagu'} ${tag.name}`}
          onClick={() =>
            key === 'action' ? edit(tag) : key === 'info' ? setInfo(tag) : setNotes(tag.id)
          }
        >
          <Icon name={key === 'action' ? 'pencil' : key === 'info' ? 'info' : 'file-text'} />
        </button>
      );
    if (key === 'tag_name') return tag.name;
    if (key === 'tag_code') return tag.code;
    if (key === 'tag_visual')
      return (
        <span
          className="tasks-project-value-badge tasks-project-value-badge--with-icon tasks-project-value-badge--tag-visual"
          style={{ '--tag-color': tag.color } as CSSProperties}
        >
          <Icon name={tag.icon} />
          <span>{tag.labels.icon}</span>
        </span>
      );
    if (key === 'priority')
      return (
        <span
          className={`tasks-project-value-badge tasks-project-value-badge--with-icon tasks-project-value-badge--priority-${tag.priority}`}
        >
          <span className={`tasks-row-priority priority-${tag.priority}`} aria-hidden="true">
            <Icon
              name={
                (
                  {
                    urgent: 'circle-alert',
                    high: 'arrow-up',
                    medium: 'equal',
                    low: 'arrow-down',
                  } as Record<string, string>
                )[tag.priority] || 'circle'
              }
            />
          </span>
          <span>{tag.labels.priority}</span>
        </span>
      );
    const field = key === 'tag_type' ? 'category' : key;
    if (['category', 'status', 'scope'].includes(field))
      return (
        <span
          className={`tasks-project-value-badge tasks-project-value-badge--tag-${field}-${tag[field as keyof Tag]}`}
        >
          {tag.labels[field]}
        </span>
      );
    if (key === 'owner')
      return (
        tag.owner_label || <span className="tasks-project-sheet__muted">Brak właściciela</span>
      );
    if (key === 'description') return tag.description || 'Brak opisu';
    if (key === 'usage_notes') return tag.usage_notes || 'Brak opisu użycia';
    if (key === 'automation') return tag.automation_rules || 'Brak reguł';
    if (key === 'related_tags') return tag.related_label;
    if (key === 'task_count') return `${tag.task_count} zadań`;
    if (key === 'created_at') return dateLabel(tag.created_at, true);
    return null;
  }
  const activeFilters = Object.values(data.filters).some(Boolean),
    sort = data.sort_options.find((option) => option.value === data.sort)!;
  const noteTag = data.tags.find((tag) => tag.id === notes);
  return (
    <div className="tasks-page tasks-list-page work-page" data-react-screen="space-tags">
      <section className="tasks-workspace" aria-busy={actions.busy}>
        <header className="tasks-topbar tasks-topbar--directory tasks-topbar--project-directory">
          <div className="tasks-titlebar-left">
            <Avatar space data={data.space.avatar} className="space-avatar--heading" />
            <h1 className="tasks-topbar-title work-space-title">{data.space.name}</h1>
          </div>
          <div className="tasks-titlebar-actions">
            {data.can_edit ? (
              <>
                <button
                  className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
                  disabled={actions.busy}
                  onClick={() => edit()}
                >
                  <Icon name="plus" />
                  Dodaj tag
                </button>
                <Dropdown
                  label="Więcej opcji"
                  className="tasks-section-actions"
                  triggerClassName="tasks-icon-button"
                  menuClass="tasks-section-menu"
                  trigger={<Icon name="ellipsis" />}
                >
                  {(close) => (
                    <>
                      <button
                        className="tasks-project-menu-button"
                        disabled={selected.size !== 1 || actions.busy}
                        onClick={() => {
                          close();
                          edit(selectedTags[0]);
                        }}
                      >
                        <Icon name="pencil" />
                        Edytuj tag
                      </button>
                      <button
                        className="tasks-project-menu-button tasks-project-menu-button--danger"
                        disabled={!selected.size || actions.busy}
                        onClick={() => {
                          close();
                          remove(selectedTags);
                        }}
                      >
                        <Icon name="trash-2" />
                        Usuń tag
                      </button>
                    </>
                  )}
                </Dropdown>
              </>
            ) : null}
          </div>
        </header>
        <nav
          className="notifications-tabs work-tabs work-tabs--views"
          aria-label="Widoki przestrzeni"
        >
          {data.navigation.map((nav) => (
            <a key={nav.key} href={nav.url} aria-current={nav.key === 'tags' ? 'page' : undefined}>
              <Icon name={nav.icon} />
              {nav.label}
            </a>
          ))}
        </nav>
        <div className="tasks-filterbar tasks-filterbar--directory">
          <div className="tasks-filterbar-left">
            <DirectoryColumnManager
              columns={columns}
              layout={sizing.layout}
              save={sizing.saveLayout}
              reset={sizing.reset}
            />
            <Dropdown
              label={`Sortowanie: ${sort.label}`}
              className="tasks-sort-dropdown"
              menuClass="tasks-sort-menu"
              trigger={
                <>
                  <Icon
                    name={
                      sort.direction === 'desc' ? 'arrow-down-wide-narrow' : 'arrow-up-wide-narrow'
                    }
                  />
                  <span>Sortuj</span>
                  <span className="tasks-project-sort-current">{sort.label}</span>
                  <Icon name="chevron-down" />
                </>
              }
            >
              {(close) =>
                data.sort_options.map((option) => (
                  <button
                    type="button"
                    role="menuitemradio"
                    key={option.value}
                    aria-checked={data.sort === option.value}
                    className={data.sort === option.value ? 'is-active' : ''}
                    onClick={() => {
                      close();
                      change({ sort: option.value });
                    }}
                  >
                    <Icon name={option.icon} />
                    <span>{option.label}</span>
                  </button>
                ))
              }
            </Dropdown>
            <details
              ref={aggregate}
              className={`tasks-project-filter-builder tasks-directory-filter-aggregate ${activeFilters ? 'is-active' : ''}`}
            >
              <summary
                className="tasks-filter-button tasks-project-query-trigger"
                aria-label="Filtruj listę"
              >
                <Icon name="list-filter" />
                <span>Filtruj</span>
                <Icon name="chevron-down" />
              </summary>
              <div
                className="tasks-project-query-panel tasks-directory-filter-aggregate__panel"
                aria-label="Filtry listy"
              >
                <header className="tasks-project-query-panel__header tasks-project-query-panel__header--main">
                  <Icon name="list-filter" />
                  <strong>Filtry</strong>
                </header>
                <div className="tasks-directory-filter-aggregate__controls">
                  {filters.map(([key, optionKey, label, icon]) => (
                    <TagFilter
                      key={key}
                      label={label}
                      icon={icon}
                      value={data.filters[key]}
                      options={data.filter_options[optionKey]}
                      change={(value) => change({ [key]: value })}
                    />
                  ))}
                  {activeFilters ? (
                    <button
                      className="tasks-filter-button"
                      onClick={() => change(Object.fromEntries(filters.map(([key]) => [key, ''])))}
                    >
                      Wyczyść filtry
                    </button>
                  ) : null}
                </div>
              </div>
            </details>
          </div>
          <div className="tasks-filterbar-center" />
          <div className="tasks-filterbar-right">
            <form
              className="react-field-slot"
              onSubmit={(event) => {
                event.preventDefault();
                change({});
              }}
            >
              <label className="tasks-search-field tasks-project-search">
                <Icon name="search" />
                <input
                  type="search"
                  value={query}
                  placeholder="Szukaj tagów"
                  aria-label="Szukaj tagów"
                  autoComplete="off"
                  onChange={(event) => {
                    const value = event.target.value;
                    setQuery(value);
                    clearTimeout(timer.current);
                    timer.current = setTimeout(() => change({ q: value }), 350);
                  }}
                />
              </label>
            </form>
            <div className="tasks-project-pagination tasks-project-pagination--toolbar">
              <nav
                className="tasks-project-pagination__pages tasks-project-pagination__pages--toolbar"
                aria-label="Strony tagów"
              >
                <button
                  className="tasks-project-pagination__button"
                  aria-label="Poprzednia strona"
                  disabled={!data.window.previous_url}
                  onClick={() => navigate(data.window.previous_url)}
                >
                  <Icon name="chevron-left" />
                </button>
                <span
                  className="tasks-project-pagination__summary tasks-project-pagination__summary--compact"
                  aria-label={data.window.summary}
                  aria-live="polite"
                >
                  {data.window.compact_summary}
                </span>
                <button
                  className="tasks-project-pagination__button"
                  aria-label="Następna strona"
                  disabled={!data.window.next_url}
                  onClick={() => navigate(data.window.next_url)}
                >
                  <Icon name="chevron-right" />
                </button>
              </nav>
              <Dropdown
                label="Liczba pozycji na stronie"
                className="tasks-project-pagination__size-control"
                menuClass="tasks-project-pagination__size-menu"
                trigger={
                  <>
                    <Icon name="rows-3" />
                    <span>{data.window.page_size} / stronę</span>
                    <Icon name="chevron-down" />
                  </>
                }
              >
                {(close) =>
                  data.window.page_size_options.map((size) => (
                    <button
                      role="menuitemradio"
                      key={size}
                      aria-checked={size === data.window.page_size}
                      className={size === data.window.page_size ? 'is-active' : ''}
                      onClick={() => {
                        close();
                        change({ page_size: String(size) });
                      }}
                    >
                      {size}
                    </button>
                  ))
                }
              </Dropdown>
            </div>
          </div>
        </div>
        {actions.error ? (
          <div className="tasks-modal__errors task-filter-query-error" role="alert">
            {actions.error}
          </div>
        ) : null}
        <div className="work-content work-content--tasks">
          <div
            className={`tasks-table-wrap tasks-board tasks-directory-board tasks-directory-sheet tasks-tag-sheet tasks-spreadsheet-sheet tasks-directory-menu-sheet ${data.tags.length ? '' : 'tasks-tag-board--empty'}`}
            style={sizing.style}
          >
            <section
              className="tasks-issue-group tasks-directory-group"
              role="table"
              aria-label="Lista tagów"
            >
              {data.tags.length ? (
                <div
                  className="tasks-directory-header tasks-directory-sheet__header tasks-tag-sheet__header"
                  role="row"
                >
                  {sizing.visible.map((column) => (
                    <span
                      key={column.key}
                      className={`tasks-directory-sheet__cell tasks-tag-sheet__cell ${column.key === 'select' ? 'tasks-directory-header-select' : ''}`}
                      data-column={column.key}
                      role="columnheader"
                    >
                      {column.key === 'select' ? (
                        <input
                          ref={all}
                          type="checkbox"
                          className="tasks-row-checkbox"
                          aria-label="Zaznacz wszystkie tagi"
                          checked={selected.size === data.tags.length}
                          onChange={(event) =>
                            setSelected(
                              event.target.checked
                                ? new Set(data.tags.map((tag) => tag.id))
                                : new Set(),
                            )
                          }
                        />
                      ) : column.icon ? (
                        <>
                          {column.label.toLocaleUpperCase('pl')}
                          <Icon name={column.icon} />
                          <Resize
                            column={column}
                            width={sizing.widths[column.key] || column.width}
                            resize={sizing.resize}
                          />
                        </>
                      ) : (
                        <span className="u-sr-only">{column.label}</span>
                      )}
                    </span>
                  ))}
                </div>
              ) : null}
              <div
                className="tasks-issue-list tasks-section-list tasks-directory-list tasks-tag-list"
                role="rowgroup"
              >
                {data.tags.map((tag) => (
                  <article
                    key={tag.id}
                    className={`tasks-issue-row tasks-section-row tasks-all-groups-row tasks-directory-row tasks-directory-sheet__row tasks-tag-sheet__row ${selected.has(tag.id) ? 'checked' : ''}`}
                    role="row"
                  >
                    {sizing.visible.map((column) =>
                      column.key === 'select' ? (
                        cell(tag, column.key)
                      ) : (
                        <span
                          key={column.key}
                          className={`tasks-directory-sheet__cell tasks-tag-sheet__cell ${column.key === 'tag_name' ? 'tasks-directory-name tasks-row-title' : column.key === 'tag_visual' ? 'tasks-tag-sheet__visual' : ['description', 'usage_notes', 'automation', 'related_tags'].includes(column.key) ? 'tasks-tag-sheet__description' : ''}`}
                          data-column={column.key}
                          role="cell"
                        >
                          {cell(tag, column.key)}
                        </span>
                      ),
                    )}
                  </article>
                ))}
                {!data.tags.length ? (
                  <EmptyState
                    className="tasks-tag-empty-state"
                    illustration="tasks"
                    title={
                      data.query || activeFilters
                        ? 'Nie znaleziono tagów.'
                        : 'Nie ma jeszcze tagów.'
                    }
                    description={
                      data.query || activeFilters
                        ? 'Zmień lub wyczyść filtry, aby zobaczyć inne wyniki.'
                        : 'Utwórz pierwszy tag, aby łatwiej porządkować zadania.'
                    }
                  />
                ) : null}
              </div>
            </section>
          </div>
        </div>
      </section>
      {modal ? (
        <FormDialog
          data={modal}
          api={initial.api_url}
          csrfToken={csrfToken}
          onClose={() => setModal(null)}
          onSaved={navigate}
        />
      ) : null}
      {info ? <InfoDialog tag={info} close={() => setInfo(null)} /> : null}
      {noteTag ? (
        <NotesDialog
          {...props}
          tag={noteTag}
          canEdit={data.can_edit}
          close={() => setNotes(null)}
          updated={setData}
        />
      ) : null}
    </div>
  );
}
function TagFilter({
  label,
  icon,
  value,
  options,
  change,
}: {
  label: string;
  icon: string;
  value: string;
  options: { value: string; label: string }[];
  change: (value: string) => void;
}) {
  const [query, setQuery] = useState('');
  return (
    <Dropdown
      label={`Filtr: ${label}`}
      menuClass="tasks-filter-menu--wide"
      onOpen={() => setQuery('')}
      trigger={
        <>
          <Icon name={icon} />
          <span>
            {label}
            {value ? `: ${options.find((option) => option.value === value)?.label || value}` : ''}
          </span>
        </>
      }
    >
      {(close) => (
        <>
          {label === 'Właściciel' ? (
            <label className="tasks-filter-menu-search">
              <Icon name="search" />
              <input
                type="search"
                placeholder="Szukaj właściciela"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
            </label>
          ) : null}
          {[{ value: '', label: 'Wszystko' }, ...options]
            .filter((option) =>
              option.label.toLocaleLowerCase('pl').includes(query.toLocaleLowerCase('pl')),
            )
            .map((option) => (
              <button
                role="menuitemradio"
                key={option.value}
                aria-checked={option.value === value}
                className={option.value === value ? 'is-active' : ''}
                onClick={() => {
                  close();
                  change(option.value);
                }}
              >
                <span>{option.label}</span>
              </button>
            ))}
        </>
      )}
    </Dropdown>
  );
}
function InfoDialog({ tag, close }: { tag: Tag; close: () => void }) {
  return (
    <Modal
      title="Informacje o tagu"
      className="tasks-project-modal tasks-project-info-modal"
      onClose={close}
    >
      <div className="tasks-modal__body tasks-project-info-modal__body tasks-issue-modal__body">
        <section className="tasks-project-info-summary">
          <h3>{tag.name}</h3>
          <p>{tag.description || 'Brak opisu'}</p>
        </section>
        <dl className="tasks-project-info-list">
          {[
            ['Kod', tag.code],
            ['Zadania', `${tag.task_count} zadań`],
            ['Typ tagu', tag.labels.category],
            ['Kolor / ikona', `${tag.color} / ${tag.labels.icon}`],
            ['Zakres', tag.labels.scope],
            ['Właściciel / dział', tag.owner_label || 'Brak właściciela'],
            ['Opis użycia', tag.usage_notes || 'Brak opisu użycia'],
            ['Reguły automatyczne', tag.automation_rules || 'Brak reguł'],
            ['Powiązane tagi', tag.related_label],
            ['Status', tag.labels.status],
            ['Priorytet', tag.labels.priority],
            ['Utworzono', dateLabel(tag.created_at)],
          ].map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      </div>
      <footer className="tasks-modal__footer">
        <button className="btn btn-secondary" onClick={close}>
          Zamknij
        </button>
      </footer>
    </Modal>
  );
}
