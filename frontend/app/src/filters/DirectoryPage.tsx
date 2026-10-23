import type { FormEvent } from 'react';
import { FormDialog } from '../forms/FormDialog';
import { Dropdown } from '../shared/Dropdown';
import { Icon } from '../shared/Icon';
import { Pagination } from '../shared/Pagination';
import { type PageProps, navigate } from '../shared/page';
import { Resize, useTableWidths } from '../shared/table';
import { usePageActions } from '../shared/usePageActions';
import type { DirectoryData, SavedFilter } from './types';

const columns = [
  { key: 'select', label: 'Ulubione', width: 40 },
  { key: 'menu', label: 'Działania', width: 40 },
  { key: 'name', label: 'Filtr', width: 320 },
  { key: 'leader', label: 'Twórca', width: 220 },
  { key: 'visibility', label: 'Widoczność', width: 190 },
  { key: 'description', label: 'Opis', width: 320 },
];
const icons = ['', '', 'filter', 'user-round', 'lock', 'align-left'];
export default function DirectoryPage(props: PageProps) {
  const { initial, csrfToken } = props,
    data = initial.data as DirectoryData;
  const actions = usePageActions(props, data.modal);
  const sizing = useTableWidths(columns, 'task-filters-directory');
  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    navigate(
      event.currentTarget.action +
        '?' +
        new URLSearchParams(
          Array.from(new FormData(event.currentTarget), ([key, value]): [string, string] => [
            key,
            String(value),
          ]),
        ),
    );
  }
  function star(item: SavedFilter) {
    void actions.act(item.favorite_url, { return_to: data.list_url });
  }
  function remove(item: SavedFilter) {
    window.showConfirmModal({
      title: 'Usuń filtr',
      message: window.escapeHtmlForModal(`Usunąć „${item.name}”?`),
      confirmText: 'Usuń',
      cancelText: 'Anuluj',
      confirmClass: 'btn-danger',
      onConfirm: () => void actions.act(item.delete_url, { return_to: data.list_url }),
    });
  }
  const filtered = !!data.query;
  return (
    <div
      className="tasks-page tasks-list-page work-page task-filters-page"
      data-react-screen="filter-directory"
    >
      <section className="tasks-workspace" aria-busy={actions.busy}>
        <header className="tasks-topbar tasks-topbar--directory tasks-topbar--project-directory">
          <div className="tasks-titlebar-left">
            <h1 className="tasks-topbar-title">{initial.title}</h1>
          </div>
          <div className="tasks-titlebar-actions">
            <a className="tasks-filter-button" href={data.search_url}>
              <Icon name="plus" />
              Nowe wyszukiwanie
            </a>
          </div>
        </header>
        <nav className="notifications-tabs work-tabs" aria-label="Katalog filtrów">
          {[
            ['favorites', 'Ulubione'],
            ['mine', 'Moje filtry'],
            ['shared', 'Udostępnione mi'],
            ['all', 'Wszystkie filtry'],
          ].map(([key, label]) => (
            <a
              key={key}
              href={`${data.filters_url}?tab=${key}`}
              className={data.tab === key ? 'is-active' : ''}
              aria-current={data.tab === key ? 'page' : undefined}
            >
              {key === 'favorites' ? <Icon name="star" /> : null}
              {label}
            </a>
          ))}
        </nav>
        <form
          className="tasks-filterbar tasks-filterbar--directory work-item-toolbar"
          action={data.filters_url}
          onSubmit={search}
        >
          <div className="tasks-filterbar-left">
            <input type="hidden" name="tab" value={data.tab} />
            <span>Wyszukaj zapisany filtr</span>
          </div>
          <div className="tasks-filterbar-right">
            <label className="tasks-search-field tasks-project-search">
              <Icon name="search" />
              <input
                type="search"
                name="q"
                defaultValue={data.query}
                placeholder="Szukaj filtrów"
                aria-label="Szukaj filtrów"
              />
            </label>
            <button className="tasks-filter-button" type="submit">
              Szukaj
            </button>
          </div>
        </form>
        {actions.error ? (
          <div className="tasks-modal__errors task-filter-query-error" role="alert">
            {actions.error}
          </div>
        ) : null}
        <div className="work-content work-content--directory">
          <div
            className="tasks-table-wrap tasks-board tasks-directory-board tasks-directory-sheet tasks-project-sheet tasks-directory-menu-sheet tasks-spreadsheet-sheet work-space-sheet task-filter-directory"
            style={sizing.style}
          >
            {data.results.length ? (
              <section className="tasks-directory-group" role="table" aria-label="Lista filtrów">
                <div className="tasks-directory-header" role="row">
                  {columns.map((column, index) => (
                    <span
                      key={column.key}
                      className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                      role="columnheader"
                      data-column={column.key}
                    >
                      {index === 0 ? (
                        <>
                          <Icon name="star" />
                          <span className="u-sr-only">Ulubione</span>
                        </>
                      ) : index === 1 ? (
                        <span className="u-sr-only">Działania</span>
                      ) : (
                        <>
                          {column.label.toLocaleUpperCase('pl')}
                          <Icon name={icons[index]} />
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
                      key={item.id}
                      className="tasks-issue-row tasks-directory-row"
                      role="row"
                    >
                      <span
                        className="tasks-directory-sheet__cell"
                        role="cell"
                        data-column="select"
                      >
                        <button
                          className={`tasks-icon-button tasks-favorite-toggle ${item.favorite ? 'is-active' : ''}`}
                          aria-label={`${item.favorite ? 'Usuń z' : 'Dodaj do'} ulubionych: ${item.name}`}
                          aria-pressed={item.favorite}
                          disabled={actions.busy}
                          onClick={() => star(item)}
                        >
                          <Icon name={item.favorite ? 'star-filled' : 'star'} />
                        </button>
                      </span>
                      <div className="tasks-directory-sheet__cell" role="cell" data-column="menu">
                        <Dropdown
                          label={`Działania filtra ${item.name}`}
                          className="tasks-row-actions"
                          triggerClassName="tasks-project-sheet__edit-button"
                          menuClass="tasks-project-menu"
                          trigger={<Icon name="menu" />}
                        >
                          {(close) => (
                            <div>
                              <a className="tasks-project-menu-button" href={item.url}>
                                <Icon name="search" />
                                Otwórz filtr
                              </a>

                              {item.editable ? (
                                <button
                                  className="tasks-project-menu-button"
                                  disabled={actions.busy}
                                  onClick={() => {
                                    close();
                                    void actions.open(item.edit_url);
                                  }}
                                >
                                  <Icon name="pencil" />
                                  Edytuj filtr i dostępy
                                </button>
                              ) : null}
                              <a
                                className="tasks-project-menu-button"
                                href={`${data.search_url}?jql=${encodeURIComponent(item.query)}&mode=advanced`}
                              >
                                <Icon name="copy" />
                                Użyj w nowym wyszukiwaniu
                              </a>
                              {item.editable ? (
                                <button
                                  className="tasks-project-menu-button tasks-project-menu-button--danger"
                                  disabled={actions.busy}
                                  onClick={() => {
                                    close();
                                    remove(item);
                                  }}
                                >
                                  <Icon name="trash-2" />
                                  Usuń filtr
                                </button>
                              ) : null}
                            </div>
                          )}
                        </Dropdown>
                      </div>
                      <span
                        className="tasks-directory-sheet__cell tasks-directory-name"
                        role="cell"
                        data-column="name"
                      >
                        <a href={item.url} title={item.name}>
                          {item.name}
                        </a>
                      </span>
                      <span
                        className="tasks-directory-sheet__cell"
                        role="cell"
                        data-column="leader"
                      >
                        {item.author}
                      </span>
                      <span
                        className="tasks-directory-sheet__cell"
                        role="cell"
                        data-column="visibility"
                      >
                        {item.visibility_label}
                      </span>
                      <span
                        className="tasks-directory-sheet__cell tasks-project-sheet__description"
                        role="cell"
                        data-column="description"
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
                className="tasks-empty-state tasks-empty-state--centered tasks-empty-state--illustrated"
                role="status"
              >
                <img
                  className="tasks-empty-state__illustration"
                  src={data.illustration}
                  alt=""
                  width={720}
                  height={540}
                  draggable={false}
                />
                <div className="tasks-empty-state__copy">
                  <h2>{filtered ? 'Brak pasujących filtrów' : 'Brak filtrów'}</h2>
                  <p>
                    {filtered
                      ? 'Zmień wyszukiwanie lub wyczyść jego warunki.'
                      : data.tab === 'favorites'
                        ? 'Oznacz filtr gwiazdką, aby mieć go pod ręką.'
                        : data.tab === 'shared'
                          ? 'Filtry udostępnione przez inne osoby pojawią się tutaj.'
                          : 'Zapisz wyszukiwanie, aby wracać do aktualnych wyników.'}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
        <Pagination data={data.pagination} />
      </section>
      {actions.modal ? (
        <FormDialog
          data={actions.modal}
          api={initial.api_url}
          csrfToken={csrfToken}
          onClose={actions.close}
          onSaved={(url) =>
            navigate(actions.modal?.filter_settings === 'edit' && !data.modal ? initial.url : url)
          }
        />
      ) : null}
    </div>
  );
}
