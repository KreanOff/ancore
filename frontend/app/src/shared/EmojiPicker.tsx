import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { Dropdown } from './Dropdown';
import { Emoji, type EmojiValue } from './Emoji';
import { Icon } from './Icon';

interface Item {
  value: string;
  label: string;
  search: string;
  category: string;
  sheet: number;
  x: number;
  y: number;
}
interface Catalog {
  version: string;
  categories: { id: string; label: string; icon: string }[];
  items: Item[];
}
export interface EmojiPickerConfig {
  selected: EmojiValue;
  default?: EmojiValue;
  catalog_url: string;
  asset_url: string;
}
const catalogs = new Map<string, Promise<Catalog>>();
function loadCatalog(url: string) {
  let promise = catalogs.get(url);
  if (!promise) {
    promise = fetch(url)
      .then(async (response) => {
        if (!response.ok) throw new Error('catalog');
        const data = (await response.json()) as Catalog;
        if (!Array.isArray(data.items) || !Array.isArray(data.categories))
          throw new Error('catalog');
        return data;
      })
      .catch((error) => {
        catalogs.delete(url);
        throw error;
      });
    catalogs.set(url, promise);
  }
  return promise;
}
const normalize = (value: string) =>
  value
    .toLocaleLowerCase('pl')
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .replace(/ł/g, 'l')
    .trim();

export default function EmojiPicker({
  id,
  name,
  label,
  value,
  config,
  disabled,
  invalid,
  describedBy,
  variant = 'field',
}: {
  id: string;
  name: string;
  label: string;
  value: string;
  config: EmojiPickerConfig;
  disabled: boolean;
  invalid: boolean;
  describedBy: string;
  variant?: 'field' | 'avatar';
}) {
  const [selected, setSelected] = useState(config.selected),
    [current, setCurrent] = useState(value);
  const [catalog, setCatalog] = useState<Catalog>(),
    [error, setError] = useState(false);
  const [query, setQuery] = useState(''),
    [category, setCategory] = useState('all'),
    [limit, setLimit] = useState(120);
  const search = useRef<HTMLInputElement>(null),
    input = useRef<HTMLInputElement>(null),
    list = useRef<HTMLDivElement>(null);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  const storageKey = `ancore:emoji-recent:${document.body.dataset.accountId}:${document.body.dataset.workplaceId}`;
  const [recent, setRecent] = useState<string[]>(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey) || '[]');
      return Array.isArray(saved)
        ? saved.filter((value): value is string => typeof value === 'string').slice(0, 32)
        : [];
    } catch {
      return [];
    }
  });
  async function load() {
    setError(false);
    try {
      const data = await loadCatalog(config.catalog_url);
      if (alive.current) setCatalog(data);
    } catch {
      if (alive.current) setError(true);
    }
  }
  function filter(nextQuery: string, nextCategory = category) {
    setQuery(nextQuery);
    setCategory(nextCategory);
    setLimit(120);
    list.current?.scrollTo(0, 0);
  }
  const normalizedQuery = normalize(query);
  const terms = normalizedQuery.split(/\s+/).filter(Boolean);
  const results = (catalog?.items || []).filter(
    (item) =>
      (terms.length ||
        category === 'all' ||
        (category === 'recent' ? recent.includes(item.value) : item.category === category)) &&
      terms.every((term) => item.search.includes(term) || item.value.includes(term)),
  );
  if (!terms.length && category === 'recent')
    results.sort((a, b) => recent.indexOf(a.value) - recent.indexOf(b.value));
  if (terms.length) {
    const rank = (item: Item) =>
      item.value.replace(/\ufe0f/g, '') === query.replace(/\ufe0f/g, '')
        ? 0
        : normalize(item.label) === normalizedQuery
          ? 1
          : normalize(item.label).startsWith(normalizedQuery)
            ? 2
            : 3;
    results.sort((a, b) => rank(a) - rank(b));
  }
  function choose(item: Item, close: () => void) {
    const chosen: EmojiValue = {
      value: item.value,
      label: item.label,
      art: {
        url: `${config.asset_url}sheet-${String(item.sheet).padStart(2, '0')}.webp?v=${catalog!.version}`,
        position: `${(item.x * 100) / 15}% ${(item.y * 100) / 15}%`,
      },
    };
    commit(chosen, close);
  }
  function commit(chosen: EmojiValue, close: () => void, remember = true) {
    setSelected(chosen);
    setCurrent(chosen.value);
    input.current!.value = chosen.value;
    input.current!.dispatchEvent(new Event('input', { bubbles: true }));
    input.current!.dispatchEvent(new Event('change', { bubbles: true }));
    if (remember) {
      const next = [chosen.value, ...recent.filter((value) => value !== chosen.value)].slice(0, 32);
      setRecent(next);
      try {
        localStorage.setItem(storageKey, JSON.stringify(next));
      } catch {
        /* Storage is optional. */
      }
    }
    close();
  }
  function gridKeys(event: KeyboardEvent<HTMLDivElement>) {
    const buttons = [
      ...event.currentTarget.querySelectorAll<HTMLButtonElement>('[data-emoji-value]'),
    ];
    const index = buttons.indexOf(event.target as HTMLButtonElement);
    if (
      index < 0 ||
      !['ArrowRight', 'ArrowLeft', 'ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)
    )
      return;
    event.preventDefault();
    event.stopPropagation();
    const next =
      event.key === 'Home'
        ? 0
        : event.key === 'End'
          ? buttons.length - 1
          : Math.max(
              0,
              Math.min(
                buttons.length - 1,
                index +
                  ({ ArrowRight: 1, ArrowLeft: -1, ArrowDown: 8, ArrowUp: -8 }[event.key] || 0),
              ),
            );
    buttons[next]?.focus();
    buttons[next]?.scrollIntoView({ block: 'nearest' });
  }
  function categoryKeys(event: KeyboardEvent<HTMLButtonElement>) {
    if (!['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    event.stopPropagation();
    const buttons = [
      ...event.currentTarget.parentElement!.querySelectorAll<HTMLButtonElement>('button'),
    ];
    const index = buttons.indexOf(event.currentTarget);
    const next =
      event.key === 'Home'
        ? 0
        : event.key === 'End'
          ? buttons.length - 1
          : (index + (event.key === 'ArrowRight' ? 1 : -1) + buttons.length) % buttons.length;
    buttons[next]?.click();
    buttons[next]?.focus();
  }
  return (
    <div
      className={`emoji-picker-control${variant === 'avatar' ? ' emoji-picker-control--avatar' : ''}`}
    >
      <input
        ref={input}
        type="hidden"
        id={`${id}_value`}
        name={name}
        value={current}
        disabled={disabled}
        readOnly
      />
      <Dropdown
        label={`Wybierz emoji: ${label}`}
        role="dialog"
        searchable={false}
        className="emoji-picker"
        menuClass="emoji-picker-menu"
        triggerClassName={
          variant === 'avatar' ? 'emoji-picker-avatar-trigger' : 'form-input emoji-picker-trigger'
        }
        triggerProps={{ id, 'aria-describedby': describedBy, 'aria-invalid': invalid }}
        disabled={disabled}
        onOpen={() => {
          void load();
          requestAnimationFrame(() => search.current?.focus());
        }}
        trigger={
          variant === 'avatar' ? (
            <>
              <Emoji
                value={selected.value}
                art={selected.art}
                className="profile-page-avatar emoji-picker-avatar-preview"
              />
              <span className="profile-photo-button">Zmień</span>
            </>
          ) : (
            <>
              <Emoji value={selected.value} art={selected.art} />
              <span>{selected.label}</span>
              <Icon name="chevron-down" />
            </>
          )
        }
      >
        {(close) => (
          <>
            <div className="ancore-custom-select__search">
              <Icon name="search" />
              <input
                ref={search}
                type="search"
                className="ancore-custom-select__search-input"
                aria-label="Szukaj emoji"
                placeholder="Szukaj emoji…"
                value={query}
                onChange={() => {}}
                onInputCapture={(event) => {
                  // Searching is local UI state, outside the surrounding form's dirty tracking.
                  event.stopPropagation();
                  filter(event.currentTarget.value);
                }}
                onKeyDown={(event) => {
                  if (event.key === 'ArrowDown') {
                    event.preventDefault();
                    event.stopPropagation();
                    list.current?.querySelector<HTMLButtonElement>('[data-emoji-value]')?.focus();
                  } else if (event.key === 'Enter') {
                    event.preventDefault();
                    event.stopPropagation();
                    list.current?.querySelector<HTMLButtonElement>('[data-emoji-value]')?.click();
                  }
                }}
              />
            </div>
            {config.default ? (
              <button
                type="button"
                className="tasks-project-menu-button emoji-picker-default"
                aria-pressed={selected.value === config.default.value}
                onClick={() => commit(config.default!, close, false)}
              >
                <Emoji value={config.default.value} art={config.default.art} />
                <span>Domyślna ikona pulpitu</span>
                {selected.value === config.default.value ? <Icon name="check" /> : null}
              </button>
            ) : null}
            <div className="emoji-picker-categories" role="tablist" aria-label="Kategorie emoji">
              {[
                { id: 'all', label: 'Wszystkie', icon: 'layout-grid' },
                { id: 'recent', label: 'Ostatnio używane', icon: 'clock' },
                ...(catalog?.categories || []),
              ].map((item) => (
                <button
                  type="button"
                  role="tab"
                  tabIndex={category === item.id ? 0 : -1}
                  aria-selected={!terms.length && category === item.id}
                  aria-label={item.label}
                  title={item.label}
                  key={item.id}
                  onClick={() => filter('', item.id)}
                  onKeyDown={categoryKeys}
                >
                  <Icon name={item.icon} />
                </button>
              ))}
            </div>
            <div className="emoji-picker-caption" role="status">
              {catalog
                ? `${terms.length ? 'Wyniki wyszukiwania' : category === 'all' ? 'Wszystkie emoji' : category === 'recent' ? 'Ostatnio używane' : catalog.categories.find((item) => item.id === category)?.label} · ${results.length}`
                : error
                  ? 'Biblioteka emoji'
                  : 'Ładowanie emoji…'}
            </div>
            <div ref={list} className="emoji-picker-results" onKeyDown={gridKeys}>
              {error ? (
                <div className="emoji-picker-empty" role="alert">
                  Nie udało się wczytać emoji.
                  <button type="button" className="btn btn-secondary" onClick={() => void load()}>
                    Spróbuj ponownie
                  </button>
                </div>
              ) : catalog && !results.length ? (
                <p className="emoji-picker-empty">
                  {category === 'recent' && !terms.length
                    ? 'Wybrane emoji pojawią się tutaj.'
                    : 'Brak pasujących emoji.'}
                </p>
              ) : (
                <div className="emoji-picker-grid">
                  {results.slice(0, limit).map((item, index) => (
                    <button
                      type="button"
                      tabIndex={index === 0 ? 0 : -1}
                      key={item.value}
                      data-emoji-value={item.value}
                      aria-label={item.label}
                      title={item.label}
                      aria-pressed={selected.value === item.value}
                      onClick={() => choose(item, close)}
                    >
                      <Emoji
                        value={item.value}
                        art={{
                          url: `${config.asset_url}sheet-${String(item.sheet).padStart(2, '0')}.webp?v=${catalog!.version}`,
                          position: `${(item.x * 100) / 15}% ${(item.y * 100) / 15}%`,
                        }}
                      />
                    </button>
                  ))}
                </div>
              )}
              {results.length > limit ? (
                <button
                  type="button"
                  className="emoji-picker-more btn btn-secondary"
                  onClick={() => setLimit(limit + 120)}
                >
                  Pokaż więcej ({results.length - limit})
                </button>
              ) : null}
            </div>
            <div className="emoji-picker-footer">
              <Emoji value={selected.value} art={selected.art} />
              <span>{selected.label}</span>
              <small>Fluent Emoji 3D</small>
            </div>
          </>
        )}
      </Dropdown>
    </div>
  );
}
