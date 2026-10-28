import { type CSSProperties, type ReactNode, useState } from 'react';
import { Avatar } from '../shared/Avatar';
import { Dropdown } from '../shared/Dropdown';
import { Icon } from '../shared/Icon';
import type { Summary } from './types';

export function SummaryDistribution({
  rows,
  total,
  people = false,
  title,
  description,
  className = '',
}: {
  rows: Summary['types'];
  total: number;
  people?: boolean;
  title: string;
  description: ReactNode;
  className?: string;
}) {
  const [mode, setMode] = useState<'percent' | 'count'>('percent');
  const [sort, setSort] = useState<'default' | 'count'>('default');
  const visibleRows = sort === 'count' ? [...rows].sort((a, b) => b.count - a.count) : rows;

  return (
    <section
      className={`work-panel work-summary-panel work-summary-panel--distribution ${className}`}
      aria-label={title}
      data-summary-reveal
    >
      <header className="work-panel-heading">
        <h2>{title}</h2>
        {rows.length ? (
          <div className="work-summary-controls">
            <div
              className="work-summary-display-mode"
              role="group"
              aria-label={`Sposób prezentacji: ${title}`}
            >
              <button
                type="button"
                className={mode === 'percent' ? 'is-active' : ''}
                aria-pressed={mode === 'percent'}
                aria-label="Pokaż procenty"
                onClick={() => setMode('percent')}
              >
                %
              </button>
              <button
                type="button"
                className={mode === 'count' ? 'is-active' : ''}
                aria-pressed={mode === 'count'}
                aria-label="Pokaż liczbę zadań"
                onClick={() => setMode('count')}
              >
                Liczba
              </button>
            </div>
            <Dropdown
              label={`Sortowanie: ${title}`}
              className="work-summary-sort"
              triggerClassName={`tasks-filter-button work-summary-sort-trigger ${sort === 'count' ? 'is-active' : ''}`}
              searchable={false}
              trigger={
                <>
                  <Icon name="arrow-down-wide-narrow" />
                  <span>Sortowanie</span>
                  <Icon name="chevron-down" />
                </>
              }
            >
              {(close) => (
                <>
                  {[
                    { value: 'default', label: 'Kolejność domyślna' },
                    { value: 'count', label: 'Najwięcej zadań' },
                  ].map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      role="menuitemradio"
                      aria-checked={sort === option.value}
                      className={`tasks-row-action ${sort === option.value ? 'is-active' : ''}`}
                      onClick={() => {
                        setSort(option.value as 'default' | 'count');
                        close();
                      }}
                    >
                      <Icon name={sort === option.value ? 'check' : 'minus'} />
                      {option.label}
                    </button>
                  ))}
                </>
              )}
            </Dropdown>
          </div>
        ) : null}
      </header>
      <p className="work-caption">{description}</p>
      {people && !rows.length ? (
        <div className="work-summary-empty">
          <Icon name="users" />
          <p>Brak otwartych zadań</p>
          <span className="work-caption">Przypisane zadania pokażą obciążenie zespołu.</span>
        </div>
      ) : (
        <>
          <div className="work-summary-distribution-heading" aria-hidden="true">
            <span>{people ? 'Osoba przypisana' : 'Typ'}</span>
            <span>{people ? 'Rozkład prac' : 'Rozkład'}</span>
          </div>
          <ul
            className={`work-summary-bars work-summary-bars--distribution work-summary-bars--${people ? 'people' : 'types'}`}
          >
            {visibleRows.map((row) => {
              const share = total ? Math.min(100, Math.max(0, (row.count * 100) / total)) : 0;
              const percent = row.count && total ? `${row.percent || '<1'}%` : '0%';
              const details = `${row.label}: ${row.count} z ${total} ${people ? 'otwartych ' : ''}zadań · ${percent}`;
              return (
                <li key={row.url}>
                  <a href={row.url} title={details} aria-label={`${details}. Wyświetl zadania.`}>
                    <span className="work-summary-label" title={row.label}>
                      {row.avatar ? (
                        <Avatar data={row.avatar} className="tasks-issue-mini-avatar" />
                      ) : people ? (
                        <span className="work-summary-unassigned">
                          <Icon name="user" />
                        </span>
                      ) : (
                        <Icon name={row.icon || 'circle'} />
                      )}
                      <span className="work-summary-row-label">{row.label}</span>
                      <span className="work-summary-row-count" aria-hidden="true">
                        {row.count}
                      </span>
                    </span>
                    <span
                      className={`work-summary-distribution work-summary-distribution--${mode}`}
                    >
                      <progress
                        className="work-summary-progress-accessible"
                        value={row.count}
                        max={total || 1}
                        aria-label={details}
                      >
                        {percent}
                      </progress>
                      <span
                        className="work-summary-distribution-fill"
                        style={{ '--summary-fill-width': `${share}%` } as CSSProperties}
                        aria-hidden="true"
                      />
                      <span
                        className={`work-summary-distribution-percent ${share < 20 ? 'work-summary-distribution-percent--small' : ''}`}
                        aria-hidden="true"
                      >
                        {mode === 'count' ? row.count : percent}
                      </span>
                    </span>
                  </a>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </section>
  );
}
