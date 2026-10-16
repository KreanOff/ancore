import { useState } from 'react';
import { Dropdown } from '../shared/Dropdown';
import { Icon } from '../shared/Icon';
import type { DirectoryData, Filter } from './types';
export default function Filters({
  data,
  change,
}: {
  data: DirectoryData;
  change: (values: Record<string, string>) => void;
}) {
  const [field, setField] = useState<Filter | null>(null),
    [query, setQuery] = useState(''),
    [value, setValue] = useState(''),
    [operator, setOperator] = useState('contains'),
    [sortQuery, setSortQuery] = useState('');
  const active = data.filters.filter((field) => field.active);
  function show(next: Filter) {
    setField(next);
    setQuery('');
    setValue(next.value);
    setOperator(next.operator || 'contains');
  }
  return (
    <>
      <Dropdown
        label={
          data.office
            ? 'Filtrowanie dokumentów'
            : data.libraries
              ? 'Filtrowanie dysków'
              : 'Filtrowanie plików'
        }
        role="dialog"
        className="tasks-project-filter-builder"
        menuClass="tasks-project-query-panel tasks-project-filter-panel"
        triggerClassName={
          'tasks-filter-button tasks-project-query-trigger' + (active.length ? ' is-active' : '')
        }
        onOpen={() => {
          setField(null);
          setQuery('');
        }}
        trigger={
          <>
            <Icon name="list-filter" />
            <span>Filtruj</span>
            {active.length ? (
              <span
                className="tasks-project-query-count"
                aria-label={`Aktywne filtry: ${active.length}`}
              >
                {active.length}
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
                    setQuery('');
                  }}
                >
                  <Icon name="arrow-left" />
                </button>
              ) : (
                <span className="tasks-project-query-panel__title-icon">
                  <Icon name="list-filter" />
                </span>
              )}
              <strong>
                {field?.label ||
                  (data.office
                    ? 'Filtry dokumentów'
                    : data.libraries
                      ? 'Filtry dysków'
                      : 'Filtry plików')}
              </strong>
              {active.length && !field ? (
                <button
                  type="button"
                  className="tasks-project-query-panel__clear"
                  onClick={() => {
                    close();
                    change(
                      Object.fromEntries(Object.keys(data.filter_params).map((key) => [key, ''])),
                    );
                  }}
                >
                  Wyczyść
                </button>
              ) : null}
            </header>
            {!field || field.searchable ? (
              <label className="tasks-project-query-search">
                <Icon name="search" />
                <input
                  type="search"
                  placeholder={field ? 'Szukaj opcji' : 'Szukaj pola'}
                  aria-label={field ? 'Szukaj opcji' : 'Szukaj pola'}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </label>
            ) : null}
            {!field ? (
              <div className="tasks-project-filter-field-list">
                {data.filters
                  .filter((item) =>
                    item.label.toLocaleLowerCase('pl').includes(query.toLocaleLowerCase('pl')),
                  )
                  .map((item) => (
                    <button
                      key={item.param}
                      type="button"
                      aria-label={`Filtr: ${item.label}`}
                      onClick={() => show(item)}
                    >
                      <span className="tasks-project-query-field-icon">
                        <Icon name={item.icon} />
                      </span>
                      <span>
                        <strong>{item.label}</strong>
                        {item.active ? <small>{item.value_label}</small> : null}
                      </span>
                      <Icon name="chevron-right" />
                    </button>
                  ))}
              </div>
            ) : field.kind === 'text' ? (
              <form
                className="tasks-project-filter-detail__body"
                onSubmit={(e) => {
                  e.preventDefault();
                  close();
                  change({ [field.param]: value, [field.operator_param]: operator });
                }}
              >
                <div className="tasks-project-filter-control">
                  <span>Warunek</span>
                  <Dropdown
                    label="Warunek"
                    className="tasks-project-text-operator"
                    layer={false}
                    role="group"
                    triggerClassName="tasks-project-text-operator__toggle"
                    menuClass="tasks-project-text-operator__menu"
                    trigger={
                      <>
                        <span>{data.operators.find((item) => item.value === operator)?.label}</span>
                        <Icon name="chevron-down" />
                      </>
                    }
                  >
                    {(close) => (
                      <>
                        {data.operators.map((item) => (
                          <button
                            type="button"
                            key={item.value}
                            role="option"
                            aria-selected={operator === item.value}
                            className={
                              'tasks-project-text-operator__option' +
                              (operator === item.value ? ' is-active' : '')
                            }
                            onClick={() => {
                              setOperator(item.value);
                              close();
                            }}
                          >
                            <span>{item.label}</span>
                            <Icon name="check" />
                          </button>
                        ))}
                      </>
                    )}
                  </Dropdown>
                </div>
                <label
                  className="tasks-project-filter-control"
                  hidden={operator === 'is_empty' || operator === 'is_not_empty'}
                >
                  <span>Wartość</span>
                  <input
                    className="form-input"
                    aria-label={`Wartość: ${field.label}`}
                    value={value}
                    maxLength={255}
                    onChange={(e) => setValue(e.target.value)}
                  />
                </label>
                <div className="tasks-project-filter-detail__actions">
                  <button
                    type="button"
                    className="tasks-project-filter-detail__clear"
                    onClick={() => {
                      close();
                      change({ [field.param]: '', [field.operator_param]: '' });
                    }}
                  >
                    Wyczyść
                  </button>
                  <button type="submit" className="btn-primary tasks-project-filter-detail__apply">
                    Zastosuj
                  </button>
                </div>
              </form>
            ) : (
              <div className="tasks-project-filter-choice-list">
                {[{ value: '', label: 'Dowolna wartość' }, ...(field.options || [])]
                  .filter((item) =>
                    item.label.toLocaleLowerCase('pl').includes(query.toLocaleLowerCase('pl')),
                  )
                  .map((item) => (
                    <button
                      key={item.value}
                      type="button"
                      className={
                        'tasks-project-filter-choice' +
                        (item.value === field.value ? ' is-active' : '')
                      }
                      role="radio"
                      aria-checked={item.value === field.value}
                      onClick={() => {
                        close();
                        change({ [field.param]: item.value });
                      }}
                    >
                      <span>{item.label}</span>
                      <Icon name="check" />
                    </button>
                  ))}
              </div>
            )}
          </>
        )}
      </Dropdown>
      <Dropdown
        label={`Sortowanie: ${data.sort_label}`}
        className="tasks-project-sort-builder"
        menuClass="tasks-project-query-panel tasks-project-sort-panel"
        role="dialog"
        triggerClassName="tasks-filter-button tasks-project-query-trigger"
        trigger={
          <>
            <Icon
              name={
                data.sort_direction === 'desc' ? 'arrow-down-wide-narrow' : 'arrow-up-narrow-wide'
              }
            />
            <span>Sortuj</span>
            <span className="tasks-project-sort-current">{data.sort_label}</span>
            <Icon name="chevron-down" />
          </>
        }
      >
        {(close) => (
          <>
            <header className="tasks-project-query-panel__header tasks-project-query-panel__header--main">
              <span className="tasks-project-query-panel__title-icon">
                <Icon name="arrow-up-down" />
              </span>
              <span>
                <strong>
                  {data.office
                    ? 'Sortowanie dokumentów'
                    : data.libraries
                      ? 'Sortowanie dysków'
                      : 'Sortowanie plików'}
                </strong>
              </span>
            </header>
            <div
              className="tasks-project-sort-directions"
              role="radiogroup"
              aria-label="Kierunek sortowania"
            >
              {[
                ['asc', 'Rosnąco'],
                ['desc', 'Malejąco'],
              ].map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  role="radio"
                  aria-checked={data.sort_direction === value}
                  className={data.sort_direction === value ? 'is-active' : ''}
                  onClick={() => {
                    close();
                    change({ sort: `${data.sort_field}_${value}` });
                  }}
                >
                  <Icon
                    name={value === 'asc' ? 'arrow-up-narrow-wide' : 'arrow-down-wide-narrow'}
                  />
                  {label}
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
              {data.sort_fields
                .filter((field) =>
                  field.label.toLocaleLowerCase('pl').includes(sortQuery.toLocaleLowerCase('pl')),
                )
                .map((field) => (
                  <button
                    key={field.value}
                    type="button"
                    role="radio"
                    aria-checked={data.sort_field === field.value}
                    className={data.sort_field === field.value ? 'is-active' : ''}
                    onClick={() => {
                      close();
                      change({ sort: `${field.value}_${data.sort_direction}` });
                    }}
                  >
                    <span className="tasks-project-query-field-icon">
                      <Icon name={field.icon} />
                    </span>
                    <span>{field.label}</span>
                    <Icon name="check" />
                  </button>
                ))}
            </div>
          </>
        )}
      </Dropdown>
      {active.map((field) => (
        <button
          key={field.param}
          type="button"
          className="tasks-project-active-filter"
          title={`Usuń filtr ${field.label}`}
          aria-label={`Usuń filtr ${field.label}`}
          onClick={() =>
            change({
              [field.param]: '',
              ...(field.operator_param ? { [field.operator_param]: '' } : {}),
            })
          }
        >
          <Icon name={field.icon} />
          <span>
            <strong>{field.label}:</strong> {field.value_label}
          </span>
          <Icon name="x" />
        </button>
      ))}
    </>
  );
}
