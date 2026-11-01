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
import { type Page, type PageProps, navigate, pageRequest, setPageLocation } from '../shared/page';
import { errorMessage } from '../shared/api';
import { Resize } from '../shared/table';
import { FormDialog, type FormDialogData } from '../forms/FormDialog';
import { dateLabel } from '../spaces/types';
import { SpaceHeader } from '../spaces/SpaceHeader';
import NotesDialog from './NotesDialog';
import type { Tag, TagsData } from './types';

const columns = [
  { key: 'select', label: 'Zaznaczenie', icon: '', width: 40 },
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
    [query, setQuery] = useState(data.query),
    [loading, setLoading] = useState(false),
    [listError, setListError] = useState(''),
    [notice, setNotice] = useState('');
  const currentUrl = useRef(initial.url),
    life = useRef(new AbortController()),
    pending = useRef(false),
    table = useRef<HTMLDivElement>(null),
    scroll = useRef<{ top: number; left: number } | null>(null);
  const currentProps = { ...props, initial: { ...initial, url: currentUrl.current } };
  const busy = loading,
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
  useLayoutEffect(() => {
    if (scroll.current && table.current) {
      table.current.scrollTop = scroll.current.top;
      table.current.scrollLeft = scroll.current.left;
      scroll.current = null;
    }
  }, [data]);
  useEffect(
    () => () => {
      clearTimeout(timer.current);
      life.current.abort();
    },
    [],
  );
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
    const url = new URL(currentUrl.current, location.origin);
    url.searchParams.set('q', query);
    url.searchParams.delete('page');
    url.searchParams.delete('page_size');
    url.searchParams.delete('tags_limit');
    Object.entries(values).forEach(([key, value]) =>
      value ? url.searchParams.set(key, value) : url.searchParams.delete(key),
    );
    navigate(url.pathname + url.search);
  }
  async function loadMore() {
    if (pending.current || !data.window.more_url) return;
    pending.current = true;
    setLoading(true);
    setListError('');
    try {
      const page = await pageRequest<Page>(
        initial.api_url,
        data.window.more_url,
        csrfToken,
        life.current.signal,
      );
      if (life.current.signal.aborted) return;
      const next = page.data as TagsData;
      if (page.type !== 'space-tags' || next.space.id !== data.space.id)
        throw new Error('Nie udało się wczytać tagów. Spróbuj ponownie.');
      if (table.current)
        scroll.current = { top: table.current.scrollTop, left: table.current.scrollLeft };
      currentUrl.current = data.window.more_url;
      setPageLocation(currentUrl.current);
      setData(next);
      const visible = new Set(next.tags.map((tag) => tag.id));
      setSelected((current) => new Set([...current].filter((id) => visible.has(id))));
      setNotice(`Wczytano ${next.window.loaded_count} z ${next.window.total_tags} tagów.`);
    } catch (exception) {
      if (!life.current.signal.aborted)
        setListError(
          exception instanceof Error && exception.name === 'TimeoutError'
            ? 'Serwer nie odpowiedział na czas. Spróbuj ponownie.'
            : errorMessage(exception),
        );
    } finally {
      pending.current = false;
      if (!life.current.signal.aborted) setLoading(false);
    }
  }
  function edit(tag?: Tag) {
    if (!data.form || busy || pending.current) return;
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
      action: currentUrl.current,
      return_url: currentUrl.current,
      values: { action: tag ? 'edit_tag' : 'create_tag', tag_id: tag ? String(tag.id) : '' },
      form,
    });
  }
  function openNotes(tag: Tag) {
    if (!busy && !pending.current) setNotes(tag.id);
  }
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
    if (['action', 'info', 'notes'].includes(key))
      return key === 'action' && !data.can_edit ? null : (
        <button
          className="tasks-project-sheet__edit-button"
          disabled={key !== 'info' && busy}
          aria-label={`${key === 'action' ? 'Edytuj tag' : key === 'info' ? 'Informacje o tagu' : 'Notatki tagu'} ${tag.name}`}
          onClick={() =>
            key === 'action' ? edit(tag) : key === 'info' ? setInfo(tag) : openNotes(tag)
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
      <section className="tasks-workspace" aria-busy={busy}>
        <SpaceHeader
          navigation={data.navigation}
          currentView="tags"
          heading={
            <>
              <Avatar space data={data.space.avatar} className="space-avatar--heading" />
              <h1 className="tasks-topbar-title work-space-title">{data.space.name}</h1>
            </>
          }
          actions={
            data.can_edit ? (
              <button
                className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
                disabled={busy}
                onClick={() => edit()}
              >
                <Icon name="plus" />
                Dodaj tag
              </button>
            ) : null
          }
        />
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
          </div>
        </div>
        <div className="u-sr-only" role="status" aria-live="polite">
          {notice}
        </div>
        <div className="work-content work-content--tasks">
          <div
            ref={table}
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
            {data.window.more_url || data.window.loaded_count > 20 ? (
              <button
                type="button"
                className="tasks-filter-button work-list-more"
                aria-label={`${loading ? 'Wczytywanie tagów' : data.window.more_url ? 'Pokaż więcej' : 'Wszystkie tagi'}: Tagi (${data.window.loaded_count} / ${data.window.total_tags})`}
                aria-disabled={busy || !data.window.more_url}
                aria-busy={loading}
                onClick={() => void loadMore()}
              >
                {loading
                  ? 'Wczytywanie…'
                  : data.window.more_url
                    ? 'Pokaż więcej'
                    : 'Wszystkie tagi'}
                <span className="work-list-more__count">
                  ({data.window.loaded_count} / {data.window.total_tags})
                </span>
              </button>
            ) : null}
            {listError ? (
              <div className="tasks-modal__errors work-list-more-error" role="alert">
                {listError} Kliknij „Pokaż więcej”, aby ponowić.
              </div>
            ) : null}
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
          {...currentProps}
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
