import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { flushSync } from 'react-dom';
import { Icon } from '../shared/Icon';
import { Avatar } from '../shared/Avatar';
import { pageRequest } from '../shared/page';
import type { PanelsConfig, SearchPayload } from './types';
import { LoadingRows, PanelState } from './States';

const searchFilters = [
  { key: 'all', label: 'Wszystko' },
  { key: 'space_tasks', label: 'Zadania' },
  { key: 'spaces', label: 'Przestrzenie' },
  { key: 'office-documents', label: 'Dokumenty' },
  { key: 'documents', label: 'Pliki' },
  { key: 'tags', label: 'Tagi' },
  { key: 'calendar', label: 'Kalendarz' },
  { key: 'resources', label: 'Zasoby' },
  { key: 'document-libraries', label: 'Dyski' },
  { key: 'document-folders', label: 'Foldery' },
  { key: 'workplaces', label: 'Workspace' },
  { key: 'navigation', label: 'Nawigacja' },
];

function MatchedText({ text, query }: { text: string; query: string }) {
  const term = query.trim().toLocaleLowerCase('pl');
  if (term.length < 2) return <>{text}</>;
  const lower = text.toLocaleLowerCase('pl');
  const parts = [];
  let start = 0;
  let match = lower.indexOf(term);
  while (match !== -1) {
    parts.push(text.slice(start, match));
    parts.push(<mark key={match}>{text.slice(match, match + term.length)}</mark>);
    start = match + term.length;
    match = lower.indexOf(term, start);
  }
  parts.push(text.slice(start));
  return <>{parts}</>;
}

export default function Search({ config, token }: { config: PanelsConfig; token: string }) {
  const [open, setOpen] = useState(false),
    [query, setQuery] = useState('');
  const [payload, setPayload] = useState<SearchPayload | null>(null),
    [group, setGroup] = useState('all');
  const [loading, setLoading] = useState(false),
    [failed, setFailed] = useState(false),
    [retry, setRetry] = useState(0);
  const [active, setActive] = useState(-1),
    input = useRef<HTMLInputElement>(null),
    form = useRef<HTMLFormElement>(null);
  const results = useRef<HTMLDivElement>(null),
    suppressFocus = useRef(false);
  const state = useRef({ open });
  state.current = { open };
  const focus = (select = false) => {
    setActive(-1);
    suppressFocus.current = true;
    input.current?.focus({ preventScroll: true });
    if (select) input.current?.select();
    suppressFocus.current = false;
  };
  const close = (restore = false) => {
    setOpen(false);
    setActive(-1);
    if (restore) focus();
  };
  useEffect(() => {
    document.body.classList.toggle('global-search-open', open);
    if (open) window.dispatchEvent(new CustomEvent('ancore:global-search-open'));
    return () => document.body.classList.remove('global-search-open');
  }, [open]);
  useEffect(() => {
    if (!open) return;
    const controller = new AbortController(),
      text = query.trim();
    setPayload(null);
    setFailed(false);
    setActive(-1);
    if (text.length === 1) {
      setLoading(false);
      return;
    }
    setLoading(true);
    const timer = setTimeout(
      async () => {
        try {
          const data = await pageRequest<SearchPayload>(
            config.api_url,
            config.search_url + '?' + new URLSearchParams(text ? { q: text } : { recent: '1' }),
            token,
            controller.signal,
          );
          if (!controller.signal.aborted) {
            setPayload(data);
            setLoading(false);
          }
        } catch {
          if (!controller.signal.aborted) {
            setFailed(true);
            setLoading(false);
          }
        }
      },
      text ? 180 : 0,
    );
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [open, query, retry, config.api_url, config.search_url, token]);
  useEffect(() => {
    const dismiss = () => close();
    const reset = () => {
      close();
      setQuery('');
      setPayload(null);
      setGroup('all');
    };
    const outside = (event: Event) => {
      if (!form.current?.contains(event.target as Node)) close();
    };
    const keyboard = (event: globalThis.KeyboardEvent) => {
      if (
        event.defaultPrevented ||
        event.isComposing ||
        document.querySelector('.confirm-modal-overlay')
      )
        return;
      const target = event.target as HTMLElement;
      const typing = target.matches('input, textarea, select') || target.isContentEditable;
      if (
        ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') ||
        (!typing && event.key === '/' && !state.current.open)
      ) {
        // The inbox can hand focus back to search. Other editors keep their own
        // modal workflow and cannot be bypassed by a global shortcut.
        if (form.current?.closest('[inert]')) {
          const inbox = document.getElementById('notifications-panel');
          if (!inbox || inbox.getAttribute('aria-busy') === 'true') return;
        }
        event.preventDefault();
        flushSync(() => {
          window.dispatchEvent(new CustomEvent('ancore:global-search-open'));
          setOpen(true);
        });
        focus(true);
      } else if (event.key === 'Escape' && state.current.open) {
        event.preventDefault();
        event.stopPropagation();
        close(true);
      }
    };
    for (const name of [
      'ancore:notifications-open',
      'ancore:workspace-menu-open',
      'ancore:sidebar-toggle',
    ])
      window.addEventListener(name, dismiss);
    document.addEventListener('ancore:content-unloading', reset);
    document.addEventListener('keydown', keyboard);
    document.addEventListener('pointerdown', outside);
    document.addEventListener('focusin', outside);
    return () => {
      for (const name of [
        'ancore:notifications-open',
        'ancore:workspace-menu-open',
        'ancore:sidebar-toggle',
      ])
        window.removeEventListener(name, dismiss);
      document.removeEventListener('ancore:content-unloading', reset);
      document.removeEventListener('keydown', keyboard);
      document.removeEventListener('pointerdown', outside);
      document.removeEventListener('focusin', outside);
    };
  }, []);
  const currentPayload = payload?.query === query.trim() ? payload : null;
  const groups = (currentPayload?.groups || []).filter(
    (item) => currentPayload?.recent || group === 'all' || group === item.key,
  );
  const filters = searchFilters.filter(
    (item, index) =>
      index < 5 ||
      item.key === group ||
      currentPayload?.groups.some((result) => result.key === item.key),
  );
  const count = groups.reduce((sum, item) => sum + item.results.length, 0),
    truncated = groups.some((item) => item.has_more);
  const summary = loading
    ? 'Wyszukiwanie…'
    : failed
      ? 'Spróbuj ponownie'
      : query.trim().length === 1
        ? 'Wpisz co najmniej 2 znaki.'
        : currentPayload?.recent
          ? 'Ostatnio oglądane w tym Workspace'
          : currentPayload
            ? `Wyniki: ${count}${truncated ? '+' : ''}`
            : 'Wyszukaj w bieżącym Workspace';
  function select(index: number) {
    const links = results.current?.querySelectorAll<HTMLAnchorElement>('.global-search-result');
    if (!links?.length) return;
    const next = (index + links.length) % links.length;
    setActive(next);
    links[next].focus({ preventScroll: true });
    links[next].scrollIntoView({ block: 'nearest' });
  }
  function keyboard(event: KeyboardEvent) {
    if (event.nativeEvent.isComposing) return;
    if (
      event.target !== input.current &&
      !(event.target as HTMLElement).closest('.global-search-result')
    )
      return;
    if (!open && ['ArrowDown', 'ArrowUp', 'Enter'].includes(event.key)) {
      event.preventDefault();
      setOpen(true);
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      select(event.target === input.current ? 0 : active + 1);
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      if (active === 0 && event.target !== input.current) focus();
      else select(event.target === input.current ? -1 : active - 1);
    }
    if (event.target !== input.current && ['Home', 'End'].includes(event.key)) {
      event.preventDefault();
      select(event.key === 'Home' ? 0 : -1);
    }
  }
  let index = 0;
  return (
    <form
      ref={form}
      className="global-search-form app-topbar__search"
      role="search"
      data-react-screen="global-search"
      onKeyDown={keyboard}
      onSubmit={(event) => {
        event.preventDefault();
        if (!open) {
          setOpen(true);
          return;
        }
        if (loading || failed || !currentPayload) return;
        results.current
          ?.querySelector<HTMLAnchorElement>(
            active < 0 ? '.global-search-result' : '.global-search-result.is-active',
          )
          ?.click();
      }}
    >
      <label htmlFor="global-search-input">
        <Icon name="search" />
        <input
          ref={input}
          id="global-search-input"
          type="search"
          role="combobox"
          aria-label="Globalne wyszukiwanie"
          aria-controls="global-search-panel"
          aria-expanded={open}
          aria-haspopup="dialog"
          aria-autocomplete="none"
          maxLength={120}
          placeholder="Szukaj zadań, przestrzeni, dokumentów…"
          autoComplete="off"
          spellCheck={false}
          value={query}
          onFocus={() => {
            setActive(-1);
            if (!suppressFocus.current) setOpen(true);
          }}
          onClick={() => setOpen(true)}
          onChange={(event) => {
            setQuery(event.target.value);
            setPayload(null);
            setActive(-1);
            setFailed(false);
            setLoading(event.target.value.trim().length !== 1);
            if (!event.target.value.trim()) setGroup('all');
            setOpen(true);
          }}
        />
        <span className="global-search-form__shortcut" aria-hidden="true">
          {typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)
            ? '⌘ K'
            : 'Ctrl K'}
        </span>
        <button
          type="button"
          className="global-search-form__clear"
          aria-label="Wyczyść wyszukiwanie"
          title="Wyczyść wyszukiwanie"
          hidden={!query}
          onClick={() => {
            setQuery('');
            setPayload(null);
            setGroup('all');
            setOpen(true);
            focus();
          }}
        >
          <Icon name="circle-x" />
        </button>
      </label>
      <aside
        id="global-search-panel"
        className="global-search-panel global-search-panel--quick"
        role="dialog"
        aria-labelledby="global-search-title"
        hidden={!open}
      >
        <h2 id="global-search-title" className="u-sr-only">
          Wyszukaj w Ancore
        </h2>
        <div className="global-search-quick-toolbar">
          {!query.trim() ? (
            <span className="global-search-quick-heading">
              <Icon name="clock" />
              Ostatnio oglądane
              {currentPayload?.recent ? (
                <span className="global-search-filter-count">{count}</span>
              ) : null}
            </span>
          ) : (
            <div className="global-search-filters" role="group" aria-label="Typ wyników">
              {filters.map((item) => {
                const resultGroup = currentPayload?.groups.find(
                  (result) => result.key === item.key,
                );
                const filterCount =
                  item.key === 'all' ? currentPayload?.total : resultGroup?.results.length || 0;
                const hasMore =
                  item.key === 'all' ? currentPayload?.truncated : resultGroup?.has_more;
                return (
                  <button
                    type="button"
                    key={item.key}
                    className="tasks-filter-button"
                    aria-pressed={group === item.key}
                    onClick={() => {
                      setGroup(item.key);
                      setActive(-1);
                      results.current?.scrollTo({ top: 0 });
                    }}
                  >
                    {item.label}
                    {currentPayload && !loading ? (
                      <span className="global-search-filter-count">
                        {filterCount}
                        {hasMore ? '+' : ''}
                      </span>
                    ) : null}
                  </button>
                );
              })}
            </div>
          )}
          <button
            type="button"
            className="tasks-icon-button global-search-close"
            aria-label="Zamknij wyszukiwanie"
            title="Zamknij wyszukiwanie (Esc)"
            onClick={() => close(true)}
          >
            <Icon name="x" />
          </button>
        </div>
        <div className="global-search-results" ref={results} tabIndex={-1} aria-busy={loading}>
          {loading ? (
            <LoadingRows />
          ) : failed ? (
            <PanelState
              icon="wifi-off"
              title="Nie udało się pobrać wyników"
              retry={() => {
                focus();
                setRetry((value) => value + 1);
              }}
            >
              Sprawdź połączenie i spróbuj ponownie za chwilę.
            </PanelState>
          ) : query.trim().length === 1 ? (
            <PanelState icon="text-cursor-input" title="Wpisz jeszcze jeden znak">
              Fraza „{query.trim()}” jest zbyt krótka, aby rozpocząć globalne wyszukiwanie.
            </PanelState>
          ) : !count ? (
            currentPayload?.recent ? (
              <PanelState icon="scan-search" title="Znajdź zadanie, przestrzeń lub dokument">
                Wpisz co najmniej 2 znaki. Ostatnio oglądane elementy pojawią się tutaj, gdy je
                otworzysz.
              </PanelState>
            ) : (
              <PanelState icon="search-x" title="Nie znaleźliśmy wyników">
                Sprawdź pisownię „{query.trim()}” albo użyj krótszej, bardziej ogólnej frazy.
                {group !== 'all' ? (
                  <button
                    type="button"
                    className="global-search-state__retry"
                    onClick={() => {
                      setGroup('all');
                      setActive(-1);
                      focus();
                    }}
                  >
                    Szukaj we wszystkich typach
                  </button>
                ) : null}
              </PanelState>
            )
          ) : (
            <>
              {groups.map((item) => (
                <section className="global-search-group" key={item.key}>
                  {!currentPayload?.recent ? (
                    <header className="global-search-group__header">
                      <h3>
                        <Icon name={item.icon} />
                        <span>{item.label}</span>
                      </h3>
                      <span className="global-search-group__count">
                        {item.results.length}
                        {item.has_more ? '+' : ''}
                      </span>
                    </header>
                  ) : null}
                  <div className="global-search-group__list">
                    {item.results.map((result, i) => {
                      const current = index++;
                      return (
                        <a
                          key={result.url + i}
                          href={result.url}
                          target={result.new_tab ? '_blank' : undefined}
                          rel={result.new_tab ? 'noopener' : undefined}
                          className={
                            'global-search-result' + (active === current ? ' is-active' : '')
                          }
                          onFocus={() => setActive(current)}
                          onClick={() => close()}
                        >
                          {result.avatar ? (
                            <Avatar
                              data={result.avatar}
                              space
                              className="global-search-result__avatar"
                            />
                          ) : (
                            <span
                              className={
                                'global-search-result__icon' +
                                (['Zadanie', 'Podzadanie'].includes(result.type)
                                  ? ' tasks-issue-type'
                                  : '')
                              }
                            >
                              <Icon name={result.icon || item.icon} />
                            </span>
                          )}
                          <span className="global-search-result__body">
                            <span className="global-search-result__title-line">
                              <strong className="global-search-result__title" title={result.title}>
                                <MatchedText text={result.title} query={query} />
                              </strong>
                              <span className="global-search-result__type">{result.type}</span>
                            </span>
                            {result.meta ? (
                              <span className="global-search-result__meta" title={result.meta}>
                                <MatchedText text={result.meta} query={query} />
                              </span>
                            ) : null}
                            {result.eyebrow ? (
                              <span className="global-search-result__eyebrow">
                                {result.eyebrow}
                              </span>
                            ) : null}
                          </span>
                          <span className="global-search-result__arrow">
                            <Icon name="arrow-up-right" />
                          </span>
                        </a>
                      );
                    })}
                  </div>
                </section>
              ))}
              {truncated ? (
                <p className="global-search-results__limit-note">
                  Pokazujemy najtrafniejsze wyniki. Doprecyzuj frazę, aby zawęzić listę.
                </p>
              ) : null}
            </>
          )}
        </div>
        <footer className="global-search-quick-footer">
          <span>{summary}</span>
          <span className="global-search-quick-keys" aria-hidden="true">
            <span>
              <kbd>↑</kbd>
              <kbd>↓</kbd> wybierz
            </span>
            <span>
              <kbd>↵</kbd> otwórz
            </span>
            <span>
              <kbd>esc</kbd> zamknij
            </span>
          </span>
        </footer>
        <span className="u-sr-only" role="status" aria-live="polite" aria-atomic="true">
          {summary}
        </span>
      </aside>
    </form>
  );
}
