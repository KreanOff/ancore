import { type ReactNode, useState } from 'react';
import { ViewToolbar } from './ViewToolbar';
import { Dropdown } from '../shared/Dropdown';
import { Icon } from '../shared/Icon';
import { navigate } from '../shared/page';
import type { DetailData } from './types';

const FILTERS = [
  { key: 'work_type', label: 'Typ zgłoszenia', icon: 'shapes' },
  { key: 'assignee', label: 'Wykonawca', icon: 'user-round' },
  { key: 'status', label: 'Status', icon: 'list' },
  { key: 'priority', label: 'Priorytet', icon: 'flag' },
  { key: 'team', label: 'Zespół', icon: 'users' },
  { key: 'blocked', label: 'Blokada', icon: 'circle-alert' },
];
const matches = (text: string, query: string) =>
  text.toLocaleLowerCase('pl').includes(query.trim().toLocaleLowerCase('pl'));

function changeQuery(url: string, values: Record<string, string>) {
  const next = new URL(url, location.origin);
  next.searchParams.delete('page');
  next.searchParams.delete('timeline_limit');
  [...next.searchParams.keys()]
    .filter((key) => key.startsWith('list_limit_') || key.startsWith('backlog_limit_'))
    .forEach((key) => next.searchParams.delete(key));
  Object.entries(values).forEach(([key, value]) =>
    value ? next.searchParams.set(key, value) : next.searchParams.delete(key),
  );
  navigate(next.pathname + next.search);
}

export function ItemToolbar({
  data,
  url,
  children,
  actions,
}: {
  data: DetailData;
  url: string;
  children?: ReactNode;
  actions?: ReactNode;
}) {
  const [sortQuery, setSortQuery] = useState('');
  const sortFields = data.sort.fields.filter(({ label }) => matches(label, sortQuery));

  const change = (values: Record<string, string>) => changeQuery(url, values);

  return (
    <ViewToolbar className="work-item-toolbar" actions={actions}>
      <Dropdown
        label={`Sortowanie: ${data.sort.label}, ${data.sort.direction === 'asc' ? 'rosnąco' : 'malejąco'}`}
        role="dialog"
        className="tasks-project-sort-builder"
        menuClass="tasks-project-query-panel tasks-project-sort-panel"
        triggerClassName="tasks-filter-button tasks-project-query-trigger"
        onOpen={() => setSortQuery('')}
        trigger={
          <>
            <Icon
              name={
                data.sort.direction === 'desc' ? 'arrow-down-wide-narrow' : 'arrow-up-narrow-wide'
              }
            />
            <span>Sortowanie</span>
            <Icon name="chevron-down" className="tasks-project-query-trigger__chevron" />
          </>
        }
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
                  change({ sort: '' });
                }}
              >
                Domyślnie
              </button>
            </header>
            <div
              className="tasks-project-sort-directions"
              role="radiogroup"
              aria-label="Kierunek sortowania"
            >
              {['asc', 'desc'].map((direction) => (
                <button
                  key={direction}
                  type="button"
                  role="radio"
                  aria-checked={data.sort.direction === direction}
                  className={data.sort.direction === direction ? 'is-active' : ''}
                  onClick={() => {
                    close();
                    change({ sort: `${data.sort.field}_${direction}` });
                  }}
                >
                  <Icon
                    name={direction === 'asc' ? 'arrow-up-narrow-wide' : 'arrow-down-wide-narrow'}
                  />
                  {direction === 'asc' ? 'Rosnąco' : 'Malejąco'}
                </button>
              ))}
            </div>
            <label className="tasks-project-query-search">
              <Icon name="search" />
              <input
                type="search"
                placeholder="Szukaj pola sortowania"
                aria-label="Szukaj pola sortowania"
                value={sortQuery}
                onChange={(event) => setSortQuery(event.target.value)}
              />
            </label>
            <div
              className="tasks-project-sort-field-list"
              role="radiogroup"
              aria-label="Pole sortowania"
            >
              {sortFields.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  role="radio"
                  aria-checked={data.sort.field === option.value}
                  className={data.sort.field === option.value ? 'is-active' : ''}
                  onClick={() => {
                    close();
                    change({ sort: `${option.value}_${data.sort.direction}` });
                  }}
                >
                  <span className="tasks-project-query-field-icon">
                    <Icon name={option.icon} />
                  </span>
                  <span>{option.label}</span>
                  <Icon name="check" />
                </button>
              ))}
              {!sortFields.length ? (
                <p className="tasks-project-filter-menu-empty" role="status">
                  Brak pasujących pól
                </p>
              ) : null}
            </div>
          </>
        )}
      </Dropdown>
      <ItemFiltering data={data} url={url} />
      {children}
    </ViewToolbar>
  );
}

export function ItemFiltering({
  data,
  url,
}: {
  data: Pick<DetailData, 'filters' | 'filter_options' | 'type_icons' | 'summary_filter_label'>;
  url: string;
}) {
  const [field, setField] = useState<(typeof FILTERS)[number] | null>(null);
  const [filterQuery, setFilterQuery] = useState('');
  const availableFilters = FILTERS.filter(
    ({ key }) => key !== 'blocked' || data.filter_options.blocked,
  );
  const active =
    availableFilters.filter(({ key }) => data.filters[key]).length + (data.filters.summary ? 1 : 0);
  const options = field
    ? data.filter_options[field.key].filter(([, label]) => matches(label, filterQuery))
    : [];
  const fields = availableFilters.filter(({ label }) => matches(label, filterQuery));
  const change = (values: Record<string, string>) => changeQuery(url, values);
  return (
    <Dropdown
      label="Filtrowanie zadań"
      role="dialog"
      className="tasks-project-filter-builder"
      menuClass="tasks-project-query-panel tasks-project-filter-panel"
      triggerClassName={`tasks-filter-button tasks-project-query-trigger${active ? ' is-active' : ''}`}
      onOpen={() => {
        setField(null);
        setFilterQuery('');
      }}
      trigger={
        <>
          <Icon name="list-filter" />
          <span>Filtrowanie</span>
          {active ? (
            <span className="tasks-project-query-count" aria-label={`Aktywne filtry: ${active}`}>
              {active}
            </span>
          ) : null}
          <Icon name="chevron-down" className="tasks-project-query-trigger__chevron" />
        </>
      }
    >
      {(close) => (
        <>
          <header className="tasks-project-query-panel__header tasks-project-query-panel__header--main">
            {field ? (
              <button
                type="button"
                className="tasks-project-query-panel__back"
                aria-label="Wróć do pól filtrów"
                onClick={() => {
                  setField(null);
                  setFilterQuery('');
                }}
              >
                <Icon name="arrow-left" />
              </button>
            ) : (
              <span className="tasks-project-query-panel__title-icon">
                <Icon name="list-filter" />
              </span>
            )}
            <strong>{field?.label || 'Filtrowanie zadań'}</strong>
            {active && !field ? (
              <button
                type="button"
                className="tasks-project-query-panel__clear"
                onClick={() => {
                  close();
                  change(
                    Object.fromEntries(
                      [...FILTERS.map(({ key }) => key), 'summary'].map((key) => [key, '']),
                    ),
                  );
                }}
              >
                Wyczyść
              </button>
            ) : null}
          </header>
          <label className="tasks-project-query-search">
            <Icon name="search" />
            <input
              type="search"
              placeholder={field ? 'Szukaj opcji' : 'Szukaj pola'}
              aria-label={field ? 'Szukaj opcji' : 'Szukaj pola'}
              value={filterQuery}
              onChange={(event) => setFilterQuery(event.target.value)}
            />
          </label>
          {field ? (
            <div
              className="tasks-project-filter-choice-list"
              role="radiogroup"
              aria-label={field.label}
            >
              {options.map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  role="radio"
                  aria-checked={(data.filters[field.key] || '') === value}
                  className={`tasks-project-filter-choice${(data.filters[field.key] || '') === value ? ' is-active' : ''}`}
                  onClick={() => {
                    close();
                    change({ [field.key]: value });
                  }}
                >
                  {field.key === 'work_type' ? (
                    <span className="tasks-issue-type">
                      <Icon name={data.type_icons?.[value] || 'shapes'} />
                      <span>{label}</span>
                    </span>
                  ) : (
                    <span>{label}</span>
                  )}
                  <Icon name="check" />
                </button>
              ))}
              {!options.length ? (
                <p className="tasks-project-filter-menu-empty" role="status">
                  Brak pasujących opcji
                </p>
              ) : null}
            </div>
          ) : (
            <div className="tasks-project-filter-field-list">
              {fields.map((option) => (
                <button
                  key={option.key}
                  type="button"
                  aria-label={`Filtr: ${option.label}`}
                  onClick={() => {
                    setField(option);
                    setFilterQuery('');
                  }}
                >
                  <span className="tasks-project-query-field-icon">
                    <Icon name={option.icon} />
                  </span>
                  <span>
                    <strong>{option.label}</strong>
                    {data.filters[option.key] ? (
                      <small>
                        {
                          data.filter_options[option.key].find(
                            ([value]) => value === data.filters[option.key],
                          )?.[1]
                        }
                      </small>
                    ) : null}
                  </span>
                  <Icon name="chevron-right" />
                </button>
              ))}
              {data.filters.summary && matches(data.summary_filter_label, filterQuery) ? (
                <button
                  type="button"
                  aria-label={`Usuń filtr: ${data.summary_filter_label}`}
                  onClick={() => {
                    close();
                    change({ summary: '' });
                  }}
                >
                  <span className="tasks-project-query-field-icon">
                    <Icon name="chart-no-axes-combined" />
                  </span>
                  <span>
                    <strong>Podsumowanie</strong>
                    <small>{data.summary_filter_label}</small>
                  </span>
                  <Icon name="x" />
                </button>
              ) : null}
              {!fields.length &&
              !(data.filters.summary && matches(data.summary_filter_label, filterQuery)) ? (
                <p className="tasks-project-filter-menu-empty" role="status">
                  Brak pasujących pól
                </p>
              ) : null}
            </div>
          )}
        </>
      )}
    </Dropdown>
  );
}
