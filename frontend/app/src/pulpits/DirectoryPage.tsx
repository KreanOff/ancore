import { Dropdown } from '../shared/Dropdown';
import { DirectoryToolbar } from '../shared/DirectoryToolbar';
import { LoadMore } from '../shared/LoadMore';
import { useLoadMorePage } from '../shared/useLoadMorePage';
import { PageHeader } from '../shared/PageHeader';
import { useLayoutEffect, useRef, useState, type FormEvent } from 'react';
import { FormDialog } from '../forms/FormDialog';
import { Icon } from '../shared/Icon';
import { Emoji } from '../shared/Emoji';
import { Select } from '../shared/Select';
import { Resize, useTableWidths } from '../shared/table';
import { type PageProps, navigate } from '../shared/page';
import { usePageActions } from '../shared/usePageActions';
import type { DirectoryData } from './types';
const columns = [
  { key: 'select', label: 'Zaznaczenie', width: 40, icon: '' },
  { key: 'name', label: 'Pulpit', width: 320, icon: 'layout-dashboard' },
  { key: 'leader', label: 'Twórca', width: 220, icon: 'user-round' },
  { key: 'visibility', label: 'Widoczność', width: 190, icon: 'lock' },
  { key: 'gadgets', label: 'Gadżety', width: 130, icon: 'layout-dashboard' },
  { key: 'description', label: 'Opis', width: 320, icon: 'align-left' },
];
export default function DirectoryPage(props: PageProps) {
  const { initial, csrfToken } = props;
  const { data, loading, error, loadMore } = useLoadMorePage<DirectoryData>(
    props,
    (current) => current.pagination.next,
  );
  const actions = usePageActions(props, data.modal);
  const [selected, setSelected] = useState<Set<number>>(new Set()),
    [visibility, setVisibility] = useState(data.visibility);
  const all = useRef<HTMLInputElement>(null);
  const sizing = useTableWidths(columns, 'pulpits-directory');
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
  const filtered = !!(data.query || data.visibility),
    page = data.pagination;
  return (
    <div
      className="tasks-page tasks-list-page work-page pulpits-directory-page"
      data-react-screen="pulpit-directory"
    >
      <section className="tasks-workspace" aria-busy={actions.busy || loading}>
        <PageHeader
          heading={
            <>
              <h1 className="tasks-topbar-title">{initial.title}</h1>
            </>
          }
          actions={
            <>
              <button
                className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
                disabled={actions.busy || !data.create_url}
                onClick={() => void actions.open(data.create_url)}
              >
                <Icon name="plus" />
                <span>Utwórz pulpit</span>
              </button>
            </>
          }
        />
        <DirectoryToolbar
          action={data.base_url}
          onSubmit={search}
          filters={
            <Dropdown
              label="Filtrowanie pulpitów"
              layer={false}
              role="dialog"
              className="tasks-project-filter-builder"
              menuClass="tasks-project-query-panel"
              triggerClassName={`tasks-filter-button tasks-project-query-trigger${data.visibility ? ' is-active' : ''}`}
              trigger={
                <>
                  <Icon name="list-filter" />
                  <span>Filtruj</span>
                  <Icon name="chevron-down" className="tasks-project-query-trigger__chevron" />
                </>
              }
            >
              {(close) => (
                <>
                  <header className="tasks-project-query-panel__header">
                    <strong>Filtry pulpitów</strong>
                  </header>
                  <div className="tasks-project-filter-detail__body">
                    <Select
                      name="visibility"
                      label="Widoczność pulpitu"
                      options={[['', 'Każda widoczność'], ...data.visibility_choices]}
                      value={visibility}
                      onChange={setVisibility}
                    />
                    <button className="tasks-filter-button" type="submit" onClick={close}>
                      <Icon name="list-filter" />
                      <span>Filtruj</span>
                    </button>
                  </div>
                </>
              )}
            </Dropdown>
          }
          search={
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
          }
        />
        {actions.error ? (
          <div className="tasks-modal__errors pulpit-page-error" role="alert">
            {actions.error}
          </div>
        ) : null}
        <div className="work-content work-content--directory">
          <div
            className="tasks-table-wrap tasks-board app-data-table tasks-directory-board tasks-directory-sheet tasks-project-sheet tasks-project-sheet--selectable tasks-directory-menu-sheet tasks-spreadsheet-sheet work-space-sheet pulpit-directory-sheet"
            style={sizing.style}
          >
            {data.results.length ? (
              <section className="tasks-directory-group" role="table" aria-label="Lista pulpitów">
                <div className="app-table-header tasks-directory-header" role="row">
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
                          aria-label="Zaznacz wszystkie pulpity w widocznej liście"
                          checked={selected.size === data.results.length}
                          onChange={(event) =>
                            setSelected(
                              event.target.checked
                                ? new Set(data.results.map((item) => item.id))
                                : new Set(),
                            )
                          }
                        />
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
                      className={`tasks-issue-row app-table-row tasks-directory-row pulpit-directory-row ${selected.has(item.id) ? 'checked' : ''}`}
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

                      <span
                        className="tasks-directory-sheet__cell tasks-directory-name"
                        data-column="name"
                        role="cell"
                      >
                        <Emoji
                          value={item.emoji}
                          art={item.emoji_art}
                          className="pulpit-directory-icon"
                        />
                        <a href={item.url} title={item.name}>
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
                  <h2>{filtered ? 'Brak pasujących pulpitów' : 'Brak pulpitów'}</h2>
                  <p>
                    {filtered
                      ? 'Zmień wyszukiwanie lub filtry.'
                      : 'Utwórz pulpit z własnymi gadżetami.'}
                  </p>
                </div>
              </div>
            )}
            <LoadMore
              loaded={data.results.length}
              total={page.count}
              hasMore={!!page.next}
              loading={loading}
              error={error}
              disabled={actions.busy}
              onLoad={loadMore}
            />
          </div>
        </div>
      </section>
      {actions.modal ? (
        <FormDialog
          data={actions.modal}
          returnFocus={actions.returnFocus}
          api={initial.api_url}
          csrfToken={csrfToken}
          onClose={actions.close}
          onSaved={navigate}
        />
      ) : null}
    </div>
  );
}
