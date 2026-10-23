import { setPageLocation } from '../shared/page';
import { useLayoutEffect, useRef, useState } from 'react';
import { Avatar, type AvatarData } from '../shared/Avatar';
import { Dropdown } from '../shared/Dropdown';
import { Icon } from '../shared/Icon';
import { Pagination, type PaginationData } from '../shared/Pagination';
import { Resize, useTableWidths } from '../shared/table';
import { Select } from '../shared/Select';
import { type Page, type PageProps, navigate, pageRequest } from '../shared/page';
import { errorMessage } from '../shared/api';
import { FormDialog, type FormDialogData } from '../forms/FormDialog';
export interface Space {
  id: number;
  name: string;
  key: string;
  slug: string;
  description: string;
  kind: string;
  kind_label: string;
  template: string;
  template_label: string;
  management: string;
  management_label: string;
  visibility: string;
  avatar: AvatarData;
  url: string;
  settings_url: string;
  edit_url: string;
  favorite_url: string;
  configuration_url: string;
  favorite: boolean;
  can_manage: boolean;
  item_count: number;
}
interface Data {
  results: Space[];
  base_url: string;
  spaces_url: string;
  create_url: string;
  query: string;
  tab: string;
  kind: string;
  pagination: PaginationData;
  illustration: string;
  modal: FormDialogData | null;
}
export default function DirectoryPage({ initial, csrfToken }: PageProps) {
  const data = initial.data as Data;
  const [kind, setKind] = useState(data.kind),
    [selected, setSelected] = useState<Set<number>>(new Set()),
    [modal, setModal] = useState<FormDialogData | null>(data.modal),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('');
  const all = useRef<HTMLInputElement>(null),
    life = useRef(new AbortController()),
    pending = useRef(false);
  useLayoutEffect(() => {
    if (all.current)
      all.current.indeterminate = selected.size > 0 && selected.size < data.results.length;
  }, [selected, data.results.length]);
  useLayoutEffect(() => () => life.current.abort(), []);
  async function openForm(url: string) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError('');
    try {
      const result = await pageRequest<Page>(initial.api_url, url, csrfToken, life.current.signal);
      if (result.type !== 'form') throw new Error('Nie udało się otworzyć formularza.');
      if (!life.current.signal.aborted) setModal(result.data as FormDialogData);
    } catch (exception) {
      if (!life.current.signal.aborted) setError(errorMessage(exception));
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  async function favorite(space: Space) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError('');
    const values = new FormData();
    values.set('next', initial.url);
    try {
      await pageRequest(
        initial.api_url,
        space.favorite_url,
        csrfToken,
        life.current.signal,
        values,
      );
      if (!life.current.signal.aborted) navigate(initial.url);
    } catch (exception) {
      if (!life.current.signal.aborted) setError(errorMessage(exception));
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  function close() {
    setModal(null);
    if (data.modal) setPageLocation(data.modal.return_url);
  }
  const filtered = !!(data.query || data.kind);
  const headings = [
    ['select', 'Zaznaczenie', ''],
    ['menu', 'Działania', ''],
    ['key', 'KLUCZ', 'hash'],
    ['name', 'PRZESTRZEŃ', 'layers'],
    ['kind', 'RODZAJ', 'shapes'],
    ['template', 'SZABLON', 'layout-dashboard'],
    ['description', 'OPIS', 'align-left'],
    ['tasks_count', 'ZADANIA', 'list-checks'],
  ];
  const widths = [40, 40, 150, 320, 190, 220, 320, 130];
  const columns = headings.map(([key, label], index) => ({ key, label, width: widths[index] }));
  const sizing = useTableWidths(
    columns,
    location.pathname.split('/').filter(Boolean)[0] || 'spaces',
  );
  return (
    <div className="tasks-page tasks-list-page work-page" data-react-screen="space-directory">
      <section className="tasks-workspace" aria-busy={busy}>
        <header className="tasks-topbar tasks-topbar--directory tasks-topbar--project-directory">
          <div className="tasks-titlebar-left">
            <h1 className="tasks-topbar-title">{initial.title}</h1>
          </div>
          <div className="tasks-titlebar-actions">
            <button
              type="button"
              className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
              disabled={busy}
              aria-haspopup="dialog"
              onClick={() => void openForm(data.create_url)}
            >
              <Icon name="plus" />
              Utwórz przestrzeń
            </button>
          </div>
        </header>
        <nav className="notifications-tabs work-tabs" aria-label="Katalog przestrzeni">
          {[
            ['all', 'Wszystkie', 'layers'],
            ['favorites', 'Ulubione', 'star'],
            ['private', 'Prywatne', 'lock'],
          ].map(([key, label, icon]) => (
            <a
              key={key}
              href={data.spaces_url + (key === 'all' ? '' : `?tab=${key}`)}
              aria-current={data.tab === key ? 'page' : undefined}
            >
              <Icon name={icon} />
              {label}
            </a>
          ))}
        </nav>
        <form
          className="tasks-filterbar tasks-filterbar--directory work-item-toolbar"
          method="get"
          action={data.base_url}
        >
          <input type="hidden" name="tab" value={data.tab} />
          <input type="hidden" name="kind" value={kind} />
          <div className="tasks-filterbar-left">
            <Select
              label="Rodzaj przestrzeni"
              hideLabel
              value={kind}
              options={KINDS}
              onChange={setKind}
            />
            <button type="submit" className="tasks-filter-button">
              <Icon name="filter" />
              <span>Filtruj</span>
            </button>
          </div>
          <div className="tasks-filterbar-right">
            <label className="tasks-search-field tasks-project-search">
              <Icon name="search" />
              <input
                type="search"
                name="q"
                defaultValue={data.query}
                placeholder="Szukaj przestrzeni"
                aria-label="Szukaj przestrzeni"
                maxLength={120}
              />
            </label>
          </div>
        </form>
        {error ? (
          <p className="tasks-modal__errors" role="alert">
            {error}
          </p>
        ) : null}
        <div className="work-content work-content--directory">
          <div
            className="tasks-table-wrap tasks-board tasks-directory-board tasks-directory-sheet tasks-project-sheet tasks-project-sheet--selectable tasks-directory-menu-sheet tasks-spreadsheet-sheet work-space-sheet"
            data-directory-resize="false"
            style={sizing.style}
          >
            {data.results.length ? (
              <section
                className="tasks-directory-group"
                role="table"
                aria-label="Lista przestrzeni"
              >
                <div className="tasks-directory-header" role="row">
                  {headings.map(([key, label, icon], index) => (
                    <span
                      key={key}
                      className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                      data-column={key}
                      role="columnheader"
                    >
                      {key === 'select' ? (
                        <input
                          ref={all}
                          type="checkbox"
                          className="tasks-row-checkbox"
                          aria-label="Zaznacz wszystkie przestrzenie na tej stronie"
                          checked={selected.size === data.results.length}
                          onChange={(event) =>
                            setSelected(
                              event.target.checked
                                ? new Set(data.results.map((space) => space.id))
                                : new Set(),
                            )
                          }
                        />
                      ) : key === 'menu' ? (
                        <span className="u-sr-only">Działania</span>
                      ) : (
                        <>
                          {label}
                          <Icon name={icon} />
                          <Resize
                            column={columns[index]}
                            width={sizing.widths[key] || widths[index]}
                            resize={sizing.resize}
                          />
                        </>
                      )}
                    </span>
                  ))}
                </div>
                <div className="tasks-issue-list tasks-directory-list" role="rowgroup">
                  {data.results.map((space) => (
                    <article
                      key={space.id}
                      role="row"
                      className={`tasks-issue-row tasks-directory-row work-space-row ${selected.has(space.id) ? 'checked' : ''}`}
                    >
                      <span
                        className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                        data-column="select"
                        role="cell"
                      >
                        <input
                          type="checkbox"
                          className="tasks-row-checkbox"
                          aria-label={`Zaznacz przestrzeń ${space.name}`}
                          checked={selected.has(space.id)}
                          onChange={(event) =>
                            setSelected((current) => {
                              const next = new Set(current);
                              if (event.target.checked) next.add(space.id);
                              else next.delete(space.id);
                              return next;
                            })
                          }
                        />
                      </span>
                      <div
                        className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                        data-column="menu"
                        role="cell"
                      >
                        <Dropdown
                          label={`Działania: ${space.name}`}
                          className="resources-react-row-actions"
                          menuClass="documents-item-menu"
                          role="group"
                          trigger={<Icon name="menu" />}
                        >
                          {(closeMenu) => (
                            <div className="documents-menu-actions">
                              <a href={space.url} className="tasks-project-menu-button">
                                <Icon name="layers" />
                                <span>Otwórz przestrzeń</span>
                              </a>
                              <button
                                type="button"
                                className="tasks-project-menu-button tasks-favorite-toggle"
                                aria-pressed={space.favorite}
                                disabled={busy}
                                onClick={() => {
                                  closeMenu();
                                  void favorite(space);
                                }}
                              >
                                <Icon name={space.favorite ? 'star-filled' : 'star'} />
                                <span>
                                  {space.favorite ? 'Usuń z ulubionych' : 'Dodaj do ulubionych'}
                                </span>
                              </button>
                              {space.can_manage ? (
                                <button
                                  type="button"
                                  className="tasks-project-menu-button"
                                  disabled={busy}
                                  onClick={() => {
                                    closeMenu();
                                    void openForm(space.edit_url);
                                  }}
                                >
                                  <Icon name="pencil" />
                                  <span>Edytuj przestrzeń</span>
                                </button>
                              ) : null}
                              <a
                                href={space.settings_url}
                                className="tasks-project-menu-button"
                                onClick={
                                  space.can_manage
                                    ? (event) => {
                                        if (
                                          event.button ||
                                          event.metaKey ||
                                          event.ctrlKey ||
                                          event.shiftKey ||
                                          event.altKey
                                        )
                                          return;
                                        event.preventDefault();
                                        closeMenu();
                                        void openForm(space.edit_url);
                                      }
                                    : undefined
                                }
                              >
                                <Icon name="settings" />
                                <span>Ustawienia przestrzeni</span>
                              </a>
                            </div>
                          )}
                        </Dropdown>
                      </div>
                      <span
                        className="tasks-directory-sheet__cell"
                        data-column="key"
                        role="cell"
                        title={space.key}
                      >
                        {space.key}
                      </span>
                      <span
                        className="tasks-directory-sheet__cell tasks-directory-name"
                        data-column="name"
                        role="cell"
                      >
                        <Avatar space data={space.avatar} />
                        <a href={space.url} title={space.name}>
                          {space.name}
                        </a>
                      </span>
                      <span className="tasks-directory-sheet__cell" data-column="kind" role="cell">
                        {space.kind_label}
                      </span>
                      <span
                        className="tasks-directory-sheet__cell"
                        data-column="template"
                        role="cell"
                      >
                        {space.template_label}
                      </span>
                      <span
                        className="tasks-directory-sheet__cell tasks-project-sheet__description"
                        data-column="description"
                        role="cell"
                        title={space.description}
                      >
                        {space.description || 'Brak opisu'}
                      </span>
                      <span
                        className="tasks-directory-sheet__cell tasks-project-sheet__count"
                        data-column="tasks_count"
                        role="cell"
                      >
                        {space.item_count}
                      </span>
                    </article>
                  ))}
                </div>
              </section>
            ) : (
              <div
                className="tasks-empty-state tasks-empty-state--illustrated work-space-empty-state"
                role="status"
              >
                <img
                  className="tasks-empty-state__illustration work-space-empty-state__illustration"
                  src={data.illustration}
                  alt=""
                  width={720}
                  height={540}
                  draggable={false}
                />
                <div className="tasks-empty-state__copy">
                  <h2>
                    {filtered
                      ? 'Brak pasujących przestrzeni'
                      : data.tab === 'favorites'
                        ? 'Brak ulubionych przestrzeni'
                        : data.tab === 'private'
                          ? 'Brak prywatnych przestrzeni'
                          : 'Brak przestrzeni'}
                  </h2>
                  <p>
                    {filtered
                      ? 'Zmień wyszukiwanie lub filtry.'
                      : data.tab === 'favorites'
                        ? 'Oznacz przestrzeń gwiazdką, aby pojawiła się na tej liście.'
                        : 'Utwórz przestrzeń i wybierz sposób pracy swojego zespołu.'}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
        <Pagination data={data.pagination} />
      </section>
      {modal ? (
        <FormDialog
          data={modal}
          api={initial.api_url}
          csrfToken={csrfToken}
          onClose={close}
          onSaved={(url) => {
            setModal(null);
            navigate(url);
          }}
        />
      ) : null}
    </div>
  );
}
const KINDS: [string, string][] = [
  ['', 'Wszystkie rodzaje'],
  ['software', 'Programistyczne'],
  ['business', 'Biznesowe'],
  ['service', 'Obsługowe'],
];
