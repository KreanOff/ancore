import { type FormEvent, useRef } from 'react';
import { FieldControl } from '../forms/FormDialog';
import { DirectoryToolbar, ToolbarFilter, ToolbarSort } from '../shared/DirectoryToolbar';
import { Icon } from '../shared/Icon';
import { navigate } from '../shared/page';
import type { SearchData } from './types';

export function SearchToolbar({ data }: { data: SearchData }) {
  const form = useRef<HTMLFormElement>(null);
  const fields = data.form.fields.filter((field) => !['q', 'sort'].includes(field.name));
  const query = data.form.fields.find((field) => field.name === 'q');
  const sort = data.form.fields.find((field) => field.name === 'sort');
  const order = (Array.isArray(sort?.value) ? sort.value[0] : sort?.value) || 'created_desc';
  const sortLabel = sort?.choices?.find((choice) => choice.value === order)?.label || 'Najnowsze';
  const active = fields.filter((field) =>
    Array.isArray(field.value) ? field.value.length : field.value,
  ).length;

  function search(event?: FormEvent<HTMLFormElement>, order?: string) {
    event?.preventDefault();
    if (!form.current) return;
    const params = new URLSearchParams(
      Array.from(new FormData(form.current), ([key, value]): [string, string] => [
        key,
        String(value),
      ]),
    );
    if (order) params.set('sort', order);
    navigate(data.search_url + '?' + params);
  }

  return (
    <DirectoryToolbar
      ref={form}
      className="task-filter-search app-toolbar--embedded"
      action={data.search_url}
      onSubmit={search}
      filters={
        <>
          <ToolbarFilter
            label="Filtrowanie zadań"
            activeCount={active}
            onOpen={() =>
              requestAnimationFrame(() => {
                if (form.current) window.AncoreCustomSelect?.refresh(form.current);
              })
            }
            className="tasks-project-filter-builder"
            menuClass="tasks-project-query-panel tasks-project-filter-panel task-filter-search-panel"
          >
            <header className="tasks-project-query-panel__header tasks-project-query-panel__header--main">
              <span className="tasks-project-query-panel__title-icon">
                <Icon name="list-filter" />
              </span>
              <strong>Filtrowanie zadań</strong>
              <a className="tasks-project-query-panel__clear" href={data.clear_url}>
                Wyczyść
              </a>
            </header>
            <div className="tasks-project-filter-detail__body task-filter-search-fields">
              {fields.map((field) => (
                <div className="task-filter-search-field" key={field.name}>
                  <label htmlFor={field.id}>{field.label}</label>
                  <FieldControl field={field} bare inline />
                </div>
              ))}
            </div>
            <footer className="task-filter-search-footer">
              <button className="tasks-filter-button" type="submit">
                <Icon name="search" />
                Szukaj
              </button>
            </footer>
          </ToolbarFilter>
          <ToolbarSort
            label={`Sortowanie: ${sortLabel}`}
            current={sortLabel}
            role="dialog"
            className="tasks-project-sort-builder"
            menuClass="tasks-project-query-panel tasks-project-sort-panel"
            searchable={false}
          >
            {(close) => (
              <>
                <header className="tasks-project-query-panel__header tasks-project-query-panel__header--main">
                  <span className="tasks-project-query-panel__title-icon">
                    <Icon name="arrow-up-down" />
                  </span>
                  <strong>Sortowanie zadań</strong>
                  <button
                    type="button"
                    className="tasks-project-query-panel__clear"
                    onClick={() => {
                      close();
                      search(undefined, 'created_desc');
                    }}
                  >
                    Domyślnie
                  </button>
                </header>
                <div
                  className="tasks-project-filter-choice-list"
                  role="radiogroup"
                  aria-label="Kolejność zadań"
                >
                  {sort?.choices?.map((choice) => (
                    <button
                      key={choice.value}
                      type="button"
                      role="radio"
                      aria-checked={order === choice.value}
                      className={`tasks-project-filter-choice${order === choice.value ? ' is-active' : ''}`}
                      onClick={() => {
                        close();
                        search(undefined, choice.value);
                      }}
                    >
                      <span>{choice.label}</span>
                      <Icon name="check" />
                    </button>
                  ))}
                </div>
              </>
            )}
          </ToolbarSort>
          <span role="status" className="work-caption app-toolbar__summary">
            Zadania: {data.pagination.count}
            {data.saved_filter ? ` · ${data.saved_filter.visibility_label}` : ''}
          </span>
        </>
      }
      search={
        query ? (
          <label className="tasks-search-field tasks-project-search" htmlFor={query.id}>
            <Icon name="search" />
            <div className="app-toolbar__search-control">
              <FieldControl field={query} bare />
            </div>
          </label>
        ) : null
      }
    >
      <input type="hidden" name="mode" value="basic" />
      <input type="hidden" name="basic" value="1" />
      <input type="hidden" name="sort" value={order} />
    </DirectoryToolbar>
  );
}
