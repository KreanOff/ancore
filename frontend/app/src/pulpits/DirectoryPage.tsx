import { useLayoutEffect, useRef, useState, type FormEvent } from 'react';
import { FormDialog } from '../forms/FormDialog';
import { Icon } from '../shared/Icon';
import { Select } from '../shared/Select';
import { Resize, useTableWidths } from '../shared/table';
import { type PageProps, navigate } from '../shared/page';
import { usePageActions } from '../shared/usePageActions';
import { DashboardActions, confirmDelete } from './Actions';
import type { DirectoryData } from './types';
const columns = [
  { key: 'select', label: 'Zaznaczenie', width: 40, icon: '' },
  { key: 'menu', label: 'Działania', width: 40, icon: '' },
  { key: 'name', label: 'Pulpit', width: 320, icon: 'layout-dashboard' },
  { key: 'leader', label: 'Twórca', width: 220, icon: 'user-round' },
  { key: 'visibility', label: 'Widoczność', width: 190, icon: 'lock' },
  { key: 'gadgets', label: 'Gadżety', width: 130, icon: 'layout-dashboard' },
  { key: 'description', label: 'Opis', width: 320, icon: 'align-left' },
];
export default function DirectoryPage(props: PageProps) {
  const { initial, csrfToken } = props,
    data = initial.data as DirectoryData;
  const actions = usePageActions(props, data.modal);
  const [selected, setSelected] = useState<Set<number>>(new Set()),
    [visibility, setVisibility] = useState(data.visibility),
    [favorite, setFavorite] = useState(data.favorite);
  const all = useRef<HTMLInputElement>(null),
    form = useRef<HTMLFormElement>(null);
  const sizing = useTableWidths(
    columns,
    data.management ? 'pulpits-management' : 'pulpits-directory',
  );
  useLayoutEffect(() => {
    if (all.current)
      all.current.indeterminate = selected.size > 0 && selected.size < data.results.length;
  }, [selected, data.results.length]);
  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void navigate(
      data.base_url +
        '?' +
        new URLSearchParams(
          Array.from(new FormData(event.currentTarget), ([key, value]): [string, string] => [
            key,
            String(value),
          ]),
        ),
    );
  }
  function filter(key: string, value: string) {
    if (key === 'visibility') setVisibility(value);
    else setFavorite(value);
    if (data.management) {
      const params = new URLSearchParams();
      params.set('q', (form.current?.elements.namedItem('q') as HTMLInputElement)?.value || '');
      params.set('visibility', key === 'visibility' ? value : visibility);
      params.set('favorite', key === 'favorite' ? value : favorite);
      void navigate(data.base_url + '?' + params);
    }
  }
  const filtered = !!(data.query || data.visibility || data.favorite),
    page = data.pagination;
  return (
    <div
      className={`tasks-page tasks-list-page work-page ${data.management ? 'work-page--management' : 'pulpits-directory-page'}`}
      data-react-screen="pulpit-directory"
    >
      <section className="tasks-workspace" aria-busy={actions.busy}>
        <header className="tasks-topbar tasks-topbar--directory tasks-topbar--project-directory">
          <div className="tasks-titlebar-left">
            <h1 className="tasks-topbar-title">{initial.title}</h1>
          </div>
          <div className="tasks-titlebar-actions">
            <button
              className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
              disabled={actions.busy}
              onClick={() => void actions.open(data.create_url)}
            >
              <Icon name="plus" />
              <span>Utwórz pulpit</span>
            </button>
          </div>
        </header>
        <form
          ref={form}
          className="tasks-filterbar tasks-filterbar--directory work-item-toolbar"
          action={data.base_url}
          onSubmit={search}
        >
          <div className="tasks-filterbar-left">
            <Select
              name="visibility"
              hideLabel
              label="Widoczność pulpitu"
              options={[['', 'Każda widoczność'], ...data.visibility_choices]}
              value={visibility}
              onChange={(value) => filter('visibility', value)}
            />
            {data.management ? (
              <Select
                name="favorite"
                hideLabel
                label="Oznaczenie gwiazdką"
                value={favorite}
                options={[
                  ['', 'Wszystkie pulpity'],
                  ['starred', 'Oznaczone gwiazdką'],
                  ['unstarred', 'Bez gwiazdki'],
                ]}
                onChange={(value) => filter('favorite', value)}
              />
            ) : null}
            <button className="tasks-filter-button" type="submit">
              <Icon name="filter" />
              <span>Filtruj</span>
            </button>
          </div>
          <div className="tasks-filterbar-right">
            <label className="tasks-search-field tasks-project-search">
              <Icon name="search" />
              <input
                name="q"
                type="search"
                defaultValue={data.query}
                placeholder="Szukaj pulpitu"
                aria-label="Szukaj pulpitu"
              />
            </label>
            <nav
              className="tasks-project-pagination__pages tasks-project-pagination__pages--toolbar"
              aria-label={data.management ? 'Strony zarządzania pulpitami' : 'Strony pulpitów'}
            >
              {page.previous ? (
                <a
                  className="tasks-project-pagination__button"
                  href={page.previous}
                  aria-label="Poprzednia strona"
                >
                  <Icon name="chevron-left" />
                </a>
              ) : (
                <button
                  className="tasks-project-pagination__button"
                  type="button"
                  disabled
                  aria-label="Poprzednia strona"
                >
                  <Icon name="chevron-left" />
                </button>
              )}
              <span
                className="tasks-project-pagination__summary tasks-project-pagination__summary--compact"
                aria-live="polite"
              >
                {page.start}–{page.end} z {page.count}
              </span>
              {page.next ? (
                <a
                  className="tasks-project-pagination__button"
                  href={page.next}
                  aria-label="Następna strona"
                >
                  <Icon name="chevron-right" />
                </a>
              ) : (
                <button
                  className="tasks-project-pagination__button"
                  type="button"
                  disabled
                  aria-label="Następna strona"
                >
                  <Icon name="chevron-right" />
                </button>
              )}
            </nav>
          </div>
        </form>
        {actions.error ? (
          <div className="tasks-modal__errors pulpit-page-error" role="alert">
            {actions.error}
          </div>
        ) : null}
        <div className="work-content work-content--directory">
          <div
            className={`tasks-table-wrap tasks-board tasks-directory-board tasks-directory-sheet tasks-project-sheet tasks-project-sheet--selectable tasks-directory-menu-sheet tasks-spreadsheet-sheet work-space-sheet pulpit-directory-sheet ${data.management ? 'pulpit-management-sheet' : ''}`}
            style={sizing.style}
          >
            {data.results.length ? (
              <section
                className="tasks-directory-group"
                role="table"
                aria-label={data.management ? 'Zarządzanie pulpitami' : 'Lista pulpitów'}
              >
                <div className="tasks-directory-header" role="row">
                  {columns.map((column, index) => (
                    <span
                      key={column.key}
                      className={`tasks-directory-sheet__cell tasks-project-sheet__cell ${index === 0 ? 'tasks-directory-header-select' : ''}`}
                      data-column={column.key}
                      role="columnheader"
                    >
                      {index === 0 ? (
                        <input
                          ref={all}
                          className="tasks-row-checkbox"
                          type="checkbox"
                          aria-label="Zaznacz wszystkie pulpity na tej stronie"
                          checked={selected.size === data.results.length}
                          onChange={(event) =>
                            setSelected(
                              event.target.checked
                                ? new Set(data.results.map((item) => item.id))
                                : new Set(),
                            )
                          }
                        />
                      ) : index === 1 ? (
                        <span className="u-sr-only">Działania</span>
                      ) : (
                        <>
                          {column.label.toLocaleUpperCase('pl')}
                          <Icon name={column.icon} />
                          <Resize
                            column={column}
                            width={sizing.widths[column.key] || column.width}
                            resize={sizing.resize}
                          />
                        </>
                      )}
                    </span>
                  ))}
                </div>
                <div className="tasks-issue-list tasks-directory-list" role="rowgroup">
                  {data.results.map((item) => (
                    <article
                      className={`tasks-issue-row tasks-directory-row pulpit-directory-row ${selected.has(item.id) ? 'checked' : ''}`}
                      role="row"
                      key={item.id}
                    >
                      <span
                        className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                        data-column="select"
                        role="cell"
                      >
                        <input
                          className="tasks-row-checkbox"
                          type="checkbox"
                          aria-label={`Zaznacz pulpit ${item.name}`}
                          checked={selected.has(item.id)}
                          onChange={(event) =>
                            setSelected((current) => {
                              const next = new Set(current);
                              if (event.target.checked) next.add(item.id);
                              else next.delete(item.id);
                              return next;
                            })
                          }
                        />
                      </span>
                      <span className="tasks-directory-sheet__cell" data-column="menu" role="cell">
                        <DashboardActions
                          item={item}
                          directory
                          busy={actions.busy}
                          favorite={() =>
                            void actions.act(item.favorite_url, { next: data.list_url })
                          }
                          remove={() =>
                            confirmDelete(
                              'Usuń pulpit',
                              item.name,
                              () => void actions.act(item.delete_url, {}),
                            )
                          }
                        />
                      </span>
                      <span
                        className="tasks-directory-sheet__cell tasks-directory-name"
                        data-column="name"
                        role="cell"
                      >
                        <Icon name="layout-dashboard" className="pulpit-directory-icon" />
                        <a href={data.management ? item.gadgets_url : item.url} title={item.name}>
                          {item.name}
                        </a>
                      </span>
                      <span
                        className="tasks-directory-sheet__cell"
                        data-column="leader"
                        role="cell"
                        title={item.author}
                      >
                        {item.author}
                      </span>
                      <span
                        className="tasks-directory-sheet__cell"
                        data-column="visibility"
                        role="cell"
                        title={item.visibility_label}
                      >
                        {item.visibility_label}
                      </span>
                      <span
                        className="tasks-directory-sheet__cell tasks-project-sheet__count"
                        data-column="gadgets"
                        role="cell"
                      >
                        {item.gadget_count}
                      </span>
                      <span
                        className="tasks-directory-sheet__cell tasks-project-sheet__description"
                        data-column="description"
                        role="cell"
                        title={item.description}
                      >
                        {item.description || 'Brak opisu'}
                      </span>
                    </article>
                  ))}
                </div>
              </section>
            ) : (
              <div
                className="tasks-empty-state tasks-empty-state--illustrated pulpit-directory-empty-state"
                role="status"
              >
                <img
                  className="tasks-empty-state__illustration pulpit-directory-empty-state__illustration"
                  src={data.illustration}
                  alt=""
                  width={1448}
                  height={1086}
                  draggable={false}
                />
                <div className="tasks-empty-state__copy">
                  <h2>
                    {filtered
                      ? 'Brak pasujących pulpitów'
                      : data.management
                        ? 'Brak pulpitów do zarządzania'
                        : 'Brak pulpitów'}
                  </h2>
                  <p>
                    {filtered
                      ? 'Zmień wyszukiwanie lub filtry.'
                      : 'Utwórz pulpit z własnymi gadżetami.'}
                  </p>
                  {filtered ? (
                    <a className="tasks-filter-button" href={data.base_url}>
                      Wyczyść filtry
                    </a>
                  ) : (
                    <button
                      className="tasks-filter-button"
                      disabled={actions.busy}
                      onClick={() => void actions.open(data.create_url)}
                    >
                      Utwórz pulpit
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </section>
      {actions.modal ? (
        <FormDialog
          data={actions.modal}
          api={initial.api_url}
          csrfToken={csrfToken}
          onClose={actions.close}
          onSaved={navigate}
        />
      ) : null}
    </div>
  );
}
