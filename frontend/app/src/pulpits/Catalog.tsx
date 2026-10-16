import { useEffect, useRef, useState } from 'react';
import { Icon } from '../shared/Icon';
import type { DetailData } from './types';
export interface CatalogState {
  open: boolean;
  category: string;
  query: string;
}
export function readCatalog(key: string): CatalogState {
  try {
    const value = JSON.parse(sessionStorage.getItem(key) || 'null');
    return {
      open: value?.open === true,
      category: value?.category === 'charts' ? 'charts' : 'all',
      query: typeof value?.query === 'string' ? value.query.slice(0, 200) : '',
    };
  } catch {
    return { open: false, category: 'all', query: '' };
  }
}
export function CatalogPreview({ icon }: { icon: string }) {
  return (
    <span className="pulpit-catalog-preview" aria-hidden="true">
      <Icon name={icon} />
      <span className="pulpit-catalog-preview-lines">
        <span />
        <span />
        <span />
      </span>
    </span>
  );
}
const normalize = (value: string) =>
  value
    .toLocaleLowerCase('pl')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/ł/g, 'l');
export default function Catalog({
  data,
  state,
  change,
  busy,
  count,
  add,
  close,
  error,
}: {
  data: DetailData;
  state: CatalogState;
  change: (state: CatalogState) => void;
  busy: boolean;
  count: number;
  add: (kind: string) => void;
  close: () => void;
  error: string;
}) {
  const search = useRef<HTMLInputElement>(null),
    opened = useRef(state.open);
  useEffect(() => {
    if (state.open && !opened.current) search.current?.focus({ preventScroll: true });
    opened.current = state.open;
  }, [state.open]);
  const [adding, setAdding] = useState('');
  useEffect(() => {
    if (!busy) setAdding('');
  }, [busy]);
  const limit = count >= data.max_gadgets;
  const entries = data.gadget_catalog.filter(
    (entry) =>
      (state.category === 'all' || state.category === entry.category) &&
      normalize(`${entry.name} Ancore ${entry.description} ${entry.category_label}`).includes(
        normalize(state.query.trim()),
      ),
  );
  return (
    <aside
      id="pulpit-catalog"
      className="pulpit-catalog"
      aria-labelledby="pulpit-catalog-title"
      hidden={!state.open}
      onKeyDown={(event) => {
        if (event.key === 'Escape') {
          event.preventDefault();
          event.stopPropagation();
          close();
        }
      }}
    >
      <header className="pulpit-catalog-header">
        <h2 id="pulpit-catalog-title">Dodawanie gadżetu</h2>
        <button
          type="button"
          className="tasks-icon-button"
          aria-label="Zamknij katalog gadżetów"
          onClick={close}
        >
          <Icon name="x" />
        </button>
      </header>
      <div className="pulpit-catalog-controls">
        <label className="tasks-search-field">
          <Icon name="search" />
          <input
            ref={search}
            type="search"
            placeholder="Szukaj gadżetów"
            aria-label="Szukaj gadżetów"
            value={state.query}
            onChange={(event) => change({ ...state, query: event.target.value })}
          />
        </label>
        <div className="pulpit-catalog-categories" role="group" aria-label="Kategorie gadżetów">
          {[
            ['all', 'Wszystkie'],
            ['charts', 'Statystyki'],
          ].map(([key, label]) => (
            <button
              key={key}
              type="button"
              className="tasks-filter-button"
              aria-pressed={state.category === key}
              onClick={() => change({ ...state, category: key })}
            >
              {label} <span>{data.gadget_catalog.length}</span>
            </button>
          ))}
        </div>
        <p className="pulpit-catalog-hint">
          Dodaj gadżet, a potem dopasuj jego filtry w menu „Konfiguruj”.
        </p>
        {error ? (
          <div className="tasks-modal__errors" role="alert">
            {error}
          </div>
        ) : null}
        {limit ? (
          <p className="pulpit-catalog-limit">
            Osiągnięto limit {data.max_gadgets} gadżetów. Usuń jeden, aby dodać kolejny.
          </p>
        ) : null}
        <span className="u-sr-only" role="status" aria-live="polite">
          {adding && busy ? 'Dodawanie gadżetu…' : `Pasujące gadżety: ${entries.length}.`}
        </span>
      </div>
      <div className="pulpit-catalog-list">
        {entries.map((entry) => (
          <article className="pulpit-catalog-item" key={entry.kind}>
            <div className="pulpit-catalog-item-art">
              <CatalogPreview icon={entry.icon} />
              <button
                type="button"
                className="btn btn-primary btn-sm"
                aria-label={`Dodaj: ${entry.name}`}
                disabled={busy || limit}
                onClick={() => {
                  setAdding(entry.kind);
                  add(entry.kind);
                }}
              >
                {adding === entry.kind && busy ? 'Dodawanie…' : 'Dodaj'}
              </button>
            </div>
            <div className="pulpit-catalog-item-copy">
              <h3>{entry.name}</h3>
              <span className="pulpit-catalog-author">Ancore</span>
              <p>{entry.description}</p>
              <span className="pulpit-catalog-tag">{entry.category_label}</span>
            </div>
          </article>
        ))}
        {!entries.length ? (
          <div className="pulpit-catalog-empty">
            <Icon name="search" />
            <p>Brak pasujących gadżetów.</p>
            <button
              type="button"
              className="tasks-filter-button"
              onClick={() => {
                change({ ...state, query: '', category: 'all' });
                search.current?.focus();
              }}
            >
              Wyczyść wyszukiwanie i filtry
            </button>
          </div>
        ) : null}
      </div>
    </aside>
  );
}
