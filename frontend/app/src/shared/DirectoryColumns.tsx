import { type CSSProperties, useState } from 'react';
import { Dropdown } from './Dropdown';
import { Icon } from './Icon';

export interface DirectoryColumn {
  key: string;
  label: string;
  icon: string;
  width: number;
}
export interface Layout {
  order: string[];
  hidden: string[];
}
type Widths = Record<string, number>;
function read(key: string): unknown {
  try {
    return JSON.parse(localStorage.getItem(key) || 'null');
  } catch {
    return null;
  }
}
function store(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* Storage can be disabled. */
  }
}
function validLayout(
  value: unknown,
  columns: readonly DirectoryColumn[],
  defaultHidden: readonly string[],
): Layout {
  const item = value as Partial<Layout> | null;
  const keys = new Set<string>(columns.map((column) => column.key));
  const order = Array.isArray(item?.order)
    ? [...new Set(item.order.filter((key) => keys.has(key)))]
    : [];
  return {
    order: [
      'select',
      ...order.filter((key) => key !== 'select' && key !== 'spacer'),
      ...columns
        .map((column) => column.key)
        .filter((key) => !order.includes(key) && key !== 'select' && key !== 'spacer'),
      ...columns.filter((column) => column.key === 'spacer').map((column) => column.key),
    ],
    hidden: Array.isArray(item?.hidden)
      ? item.hidden.filter((key) => keys.has(key) && key !== 'select' && key !== 'spacer')
      : [...defaultHidden],
  };
}

export function useDirectoryColumns<C extends DirectoryColumn>(
  columns: readonly C[],
  segment: string,
  defaultHidden: readonly string[] = [],
) {
  const schema = columns.map((column) => column.key).join('-');
  const layoutKey = `${segment}:directoryColumnLayout:v2:${schema}`;
  const widthsKey = `${segment}:directoryColumnWidths:v4:${schema}`;
  const [layout, setLayout] = useState<Layout>(() =>
    validLayout(read(layoutKey), columns, defaultHidden),
  );
  const [widths, setWidths] = useState<Widths>(() => {
    const value = read(widthsKey);
    return value && typeof value === 'object' && !Array.isArray(value)
      ? Object.fromEntries(
          Object.entries(value).filter(
            ([, width]) =>
              typeof width === 'number' && Number.isFinite(width) && width >= 50 && width <= 1200,
          ),
        )
      : {};
  });
  const visible = layout.order
    .filter((key) => !layout.hidden.includes(key))
    .map((key) => columns.find((column) => column.key === key)!);
  const saveLayout = (value: Layout) => {
    const normalized = validLayout(value, columns, defaultHidden);
    setLayout(normalized);
    store(layoutKey, normalized);
  };
  const resize = (key: string, width: number) =>
    setWidths((current) => {
      const value = { ...current, [key]: Math.max(50, Math.min(1200, Math.round(width))) };
      store(widthsKey, value);
      return value;
    });
  const style = {
    '--tasks-directory-grid': visible
      .map((column) => `${widths[column.key] || column.width}px`)
      .join(' '),
  } as CSSProperties;
  return {
    layout,
    saveLayout,
    visible,
    resize,
    widths,
    style,
    reset: () => {
      saveLayout({ order: columns.map((column) => column.key), hidden: [...defaultHidden] });
      setWidths({});
      store(widthsKey, {});
    },
  };
}

export function DirectoryColumnManager({
  columns,
  layout,
  save,
  reset,
}: {
  columns: readonly DirectoryColumn[];
  layout: Layout;
  save: (value: Layout) => void;
  reset: () => void;
}) {
  const [draft, setDraft] = useState(layout);
  const [query, setQuery] = useState('');
  const [dragged, setDragged] = useState('');
  function move(key: string, target: string, after = false) {
    if (
      !key ||
      key === target ||
      ['select', 'spacer'].includes(key) ||
      ['select', 'spacer'].includes(target)
    )
      return;
    setDraft((current) => {
      const order = current.order.filter((item) => item !== key);
      const index = order.indexOf(target);
      if (index < 0) return current;
      order.splice(index + (after ? 1 : 0), 0, key);
      return { ...current, order };
    });
  }
  return (
    <Dropdown
      label="Zarządzaj tabelą"
      role="dialog"
      className="tasks-directory-column-manager"
      menuClass="tasks-directory-column-menu tasks-project-query-panel"
      onOpen={() => {
        setDraft(layout);
        setQuery('');
      }}
      trigger={<Icon name="columns-3" />}
    >
      {(close) => (
        <>
          <header className="tasks-project-query-panel__header tasks-project-query-panel__header--main">
            <Icon name="columns-3" />
            <strong>Kolumny tabeli</strong>
          </header>
          <label className="tasks-directory-column-search tasks-project-query-search">
            <Icon name="search" />
            <input
              type="search"
              placeholder="Szukaj kolumny"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <div className="tasks-directory-column-list">
            {draft.order
              .filter((key) => key !== 'select' && key !== 'spacer')
              .map((key) => {
                const column = columns.find((item) => item.key === key)!;
                return (
                  <label
                    key={key}
                    className="tasks-directory-column-item"
                    hidden={
                      !column.label.toLocaleLowerCase('pl').includes(query.toLocaleLowerCase('pl'))
                    }
                    draggable
                    onDragStart={(event) => {
                      setDragged(key);
                      event.dataTransfer.setData('text/plain', key);
                    }}
                    onDragOver={(event) => event.preventDefault()}
                    onDrop={(event) => {
                      event.preventDefault();
                      const bounds = event.currentTarget.getBoundingClientRect();
                      move(dragged, key, event.clientY > bounds.top + bounds.height / 2);
                      setDragged('');
                    }}
                    onDragEnd={() => setDragged('')}
                  >
                    <input
                      type="checkbox"
                      aria-label={column.label}
                      checked={!draft.hidden.includes(key)}
                      onChange={(event) =>
                        setDraft((current) => ({
                          ...current,
                          hidden: event.target.checked
                            ? current.hidden.filter((item) => item !== key)
                            : [...current.hidden, key],
                        }))
                      }
                    />
                    <span>{column.label}</span>
                    <button
                      type="button"
                      className="tasks-directory-column-drag"
                      aria-label={`Przenieś kolumnę ${column.label}. Użyj strzałek w górę lub w dół.`}
                      onKeyDown={(event) => {
                        if (!['ArrowUp', 'ArrowDown'].includes(event.key)) return;
                        event.preventDefault();
                        event.stopPropagation();
                        const index = draft.order.indexOf(key);
                        move(
                          key,
                          draft.order[index + (event.key === 'ArrowUp' ? -1 : 1)] || 'select',
                          event.key === 'ArrowDown',
                        );
                      }}
                    >
                      <Icon name="grip-vertical" />
                    </button>
                  </label>
                );
              })}
            {!columns.some(
              (column) =>
                column.key !== 'select' &&
                column.key !== 'spacer' &&
                column.label.toLocaleLowerCase('pl').includes(query.toLocaleLowerCase('pl')),
            ) ? (
              <span className="tasks-directory-column-empty" role="status">
                Brak kolumn
              </span>
            ) : null}
          </div>
          <div className="tasks-directory-column-actions">
            <button
              type="button"
              className="tasks-directory-column-reset"
              onClick={() => {
                reset();
                close();
              }}
            >
              <Icon name="rotate-ccw" />
              <span>Resetuj</span>
            </button>
            <span className="tasks-directory-column-action-group">
              <button type="button" className="tasks-directory-column-cancel" onClick={close}>
                Anuluj
              </button>
              <button
                type="button"
                className="tasks-directory-column-save"
                onClick={() => {
                  save(draft);
                  close();
                }}
              >
                Zapisz
              </button>
            </span>
          </div>
        </>
      )}
    </Dropdown>
  );
}
