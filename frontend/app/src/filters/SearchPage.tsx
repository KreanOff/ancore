import type { FormEvent } from 'react';
import { FieldControl, FormDialog } from '../forms/FormDialog';
import { ForYouTaskRow } from '../dashboard/ForYouPage';
import { Icon } from '../shared/Icon';
import { EmptyState } from '../shared/EmptyState';
import { Pagination } from '../shared/Pagination';
import { type PageProps, navigate } from '../shared/page';
import { StatusGroup } from '../shared/StatusGroup';
import { usePageActions } from '../shared/usePageActions';
import type { SearchData } from './types';
import type { Item } from '../spaces/types';

export default function SearchPage(props: PageProps) {
  const { initial, csrfToken } = props,
    data = initial.data as SearchData;
  const actions = usePageActions(props, data.modal),
    saved = data.saved_filter;
  const groups = new Map<string, Item[]>();
  for (const item of data.items) {
    const key = `${item.category}:${item.status_label}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(item);
  }
  const ordered = [...groups.entries()].sort((a, b) => a[1][0].status_order - b[1][0].status_order);
  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    navigate(
      data.search_url +
        '?' +
        new URLSearchParams(
          Array.from(new FormData(event.currentTarget), ([key, value]): [string, string] => [
            key,
            String(value),
          ]),
        ),
    );
  }
  const field = (name: string) => {
    const schema = data.form.fields.find((item) => item.name === name);
    return schema ? <FieldControl field={schema} bare inline /> : null;
  };
  return (
    <div
      className="tasks-page tasks-list-page work-page task-filters-page"
      data-react-screen="filter-search"
    >
      <section className="tasks-workspace" aria-busy={actions.busy}>
        <header className="tasks-topbar tasks-topbar--directory tasks-topbar--project-directory">
          <div className="tasks-titlebar-left">
            {saved ? (
              <button
                type="button"
                className={`tasks-icon-button ${saved.favorite ? 'is-active' : ''}`}
                aria-label={`${saved.favorite ? 'Usuń z' : 'Dodaj do'} ulubionych: ${saved.name}`}
                aria-pressed={saved.favorite}
                disabled={actions.busy}
                onClick={() => void actions.act(saved.favorite_url, { return_to: data.list_url })}
              >
                <Icon name="star" />
              </button>
            ) : null}
            <h1 className="tasks-topbar-title">{initial.title}</h1>
            {data.changed ? <span className="work-caption">Zmienione warunki</span> : null}
          </div>
          <div className="tasks-titlebar-actions">
            {data.changed && saved?.editable && data.can_save ? (
              <button
                className="tasks-filter-button"
                disabled={actions.busy}
                onClick={() =>
                  void actions.act(saved.url + 'save/', {
                    jql: data.jql,
                    revision: String(saved.revision),
                  })
                }
              >
                Zapisz
              </button>
            ) : null}
            {data.can_save ? (
              <button
                className="tasks-filter-button"
                disabled={actions.busy}
                onClick={() => void actions.open(data.save_as_url)}
              >
                <Icon name="filter" />
                {saved ? 'Zapisz jako' : 'Zapisz filtr'}
              </button>
            ) : null}
            {saved?.editable ? (
              <button
                className="tasks-filter-button"
                disabled={actions.busy}
                onClick={() => void actions.open(saved.edit_url)}
              >
                <Icon name="settings" />
                Edytuj filtr
              </button>
            ) : null}
          </div>
        </header>
        <nav className="notifications-tabs work-tabs" aria-label="Tryb wyszukiwania">
          {data.basic_available ? (
            <a
              href={data.basic_url}
              className={data.mode === 'basic' ? 'is-active' : ''}
              aria-current={data.mode === 'basic' ? 'page' : undefined}
            >
              Podstawowy
            </a>
          ) : (
            <span
              className="task-filter-disabled"
              title="Tych warunków nie można przedstawić w trybie podstawowym."
            >
              Podstawowy
            </span>
          )}
          <a
            href={data.advanced_url}
            className={data.mode === 'advanced' ? 'is-active' : ''}
            aria-current={data.mode === 'advanced' ? 'page' : undefined}
          >
            Zaawansowany
          </a>
        </nav>
        <form className="task-filter-search" action={data.search_url} onSubmit={search}>
          <input type="hidden" name="mode" value={data.mode} />
          {data.mode === 'basic' ? (
            <>
              <input type="hidden" name="basic" value="1" />
              <div className="tasks-filterbar tasks-filterbar--directory task-filter-controls">
                <div className="tasks-filterbar-left">
                  {['space', 'type', 'status', 'priority', 'assignee'].map((name) => (
                    <div className="task-filter-control" key={name}>
                      {field(name)}
                    </div>
                  ))}
                  <button className="tasks-filter-button" type="submit">
                    <Icon name="search" />
                    Szukaj
                  </button>
                </div>
              </div>
              <div className="tasks-filterbar tasks-filterbar--directory task-filter-controls">
                <div className="tasks-filterbar-left">
                  <label className="tasks-search-field tasks-project-search">
                    <Icon name="search" />
                    {field('q')}
                  </label>
                  <div className="task-filter-control">{field('tag')}</div>
                  <div className="task-filter-control">{field('team')}</div>
                </div>
                <div className="tasks-filterbar-right">
                  <div className="task-filter-control">{field('sort')}</div>
                  <a className="tasks-filter-button" href={data.clear_url}>
                    Wyczyść
                  </a>
                </div>
              </div>
            </>
          ) : (
            <>
              <div className="task-filter-advanced">
                <label htmlFor="filter-jql" className="u-sr-only">
                  Zapytanie zaawansowane
                </label>
                <textarea
                  id="filter-jql"
                  name="jql"
                  className="form-input"
                  rows={2}
                  maxLength={4000}
                  defaultValue={data.jql}
                  placeholder="assignee = currentUser() AND category != closed ORDER BY created DESC"
                  aria-invalid={!!data.search_error}
                  aria-describedby={data.search_error ? 'filter-query-error' : undefined}
                />
                <button className="tasks-filter-button" type="submit">
                  <Icon name="search" />
                  Szukaj
                </button>
                <a className="tasks-filter-button" href={data.clear_url}>
                  Wyczyść
                </a>
              </div>
              <QueryHelp />
            </>
          )}
        </form>
        {data.search_error ? (
          <div
            className="task-filter-query-error tasks-modal__errors"
            id="filter-query-error"
            role="alert"
          >
            {data.search_error}
          </div>
        ) : null}
        {actions.error ? (
          <div className="task-filter-query-error tasks-modal__errors" role="alert">
            {actions.error}
          </div>
        ) : null}
        <div className="tasks-filterbar tasks-filterbar--directory">
          <div className="tasks-filterbar-left">
            <span role="status">
              Zadania: {data.pagination.count}
              {saved ? ` · ${saved.visibility_label}` : ''}
            </span>
          </div>
        </div>
        <div className="work-content work-content--tasks">
          <div
            className={`tasks-table-wrap tasks-board work-item-list ${data.items.length ? '' : 'tasks-board--empty'}`}
          >
            {ordered.length ? (
              ordered.map(([key, items]) => (
                <StatusGroup
                  key={key}
                  category={items[0].category}
                  label={items[0].status_label}
                  count={items.length}
                >
                  <div className="tasks-issue-list">
                    {items.map((item) => (
                      <ForYouTaskRow
                        key={item.id}
                        selectable
                        row={{
                          title: item.title,
                          key: item.key,
                          url: item.url,
                          location: item.type_label,
                          icon: item.type_icon,
                          is_task: true,
                          status_label: item.status_label,
                          overdue: item.due_urgency === 'overdue',
                          due_at: item.due_at || undefined,
                          task: {
                            status: item.category,
                            priority: item.priority,
                            priority_label: item.priority_label,
                            type_label: item.type_label,
                            type_icon: item.type_icon,
                            tags_count: item.tags_count,
                            attachments_count: item.attachments_count,
                            due_urgency: item.due_urgency,
                          },
                        }}
                      />
                    ))}
                  </div>
                </StatusGroup>
              ))
            ) : (
              <EmptyState
                illustration="tasks"
                title={data.search_error ? 'Popraw warunki wyszukiwania' : 'Nie znaleziono zadań'}
                description={
                  data.search_error
                    ? 'Po poprawieniu zapytania wybierz „Szukaj”.'
                    : 'Zmień warunki lub wyczyść filtry, aby zobaczyć inne wyniki.'
                }
              />
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
          onSaved={navigate}
        />
      ) : null}
    </div>
  );
}
function QueryHelp() {
  return (
    <details className="task-filter-help">
      <summary>Pomoc składni wyszukiwania</summary>
      <p>
        Pola: <code>space</code> (alias <code>project</code>), <code>status</code>,{' '}
        <code>type</code>, <code>priority</code>, <code>assignee</code>, <code>reporter</code>,{' '}
        <code>tag</code>, <code>team</code>, <code>sprint</code>, <code>key</code>,{' '}
        <code>text</code>, <code>created</code>, <code>due</code>, <code>category</code>.
      </p>
      <p>
        Łącz warunki przez <code>AND</code>, <code>OR</code>, <code>NOT</code> i nawiasy. Użyj{' '}
        <code>=</code>, <code>!=</code>, <code>IN</code>, <code>NOT IN</code>, <code>IS EMPTY</code>
        , <code>IS NOT EMPTY</code>. Tekst wyszukasz przez <code>~</code>; daty porównasz przez{' '}
        <code>&gt;</code>, <code>&gt;=</code>, <code>&lt;</code>, <code>&lt;=</code>. Wartości ze
        spacjami otocz cudzysłowem.
      </p>
      <p>
        Przykład:{' '}
        <code>
          assignee = currentUser() AND due &lt; startOfDay() AND category != closed ORDER BY
          priority DESC, due ASC
        </code>
        . Daty: <code>2026-10-10</code> lub <code>-7d</code>. <code>currentUser()</code> zawsze
        oznacza osobę oglądającą filtr.
      </p>
      <p>
        Obsługiwana jest powyższa składnia inspirowana JQL. Pozostałe pola i funkcje Jira nie są
        dostępne.
      </p>
    </details>
  );
}
