import { type CSSProperties, useRef, useState } from 'react';

export interface TableColumn {
  key: string;
  label: string;
  width: number;
}

export function useTableWidths(columns: TableColumn[], segment: string) {
  const key = `${segment}:directoryColumnWidths:v4:${columns.map((column) => column.key).join('-')}`;
  const [widths, setWidths] = useState<Record<string, number>>(() => {
    try {
      const value = JSON.parse(localStorage.getItem(key) || '{}');
      if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
      return Object.fromEntries(
        Object.entries(value).filter(
          ([, width]) =>
            typeof width === 'number' && Number.isFinite(width) && width >= 50 && width <= 1200,
        ),
      ) as Record<string, number>;
    } catch {
      return {};
    }
  });
  function resize(column: string, size: number) {
    setWidths((current) => {
      const next = { ...current, [column]: Math.max(50, Math.min(1200, Math.round(size))) };
      try {
        localStorage.setItem(key, JSON.stringify(next));
      } catch {
        /* Storage may be disabled. */
      }
      return next;
    });
  }
  return {
    widths,
    resize,
    style: {
      '--tasks-directory-grid': columns
        .map((column) => `${widths[column.key] || column.width}px`)
        .join(' '),
    } as CSSProperties,
  };
}

export function Resize({
  column,
  width,
  resize,
}: {
  column: TableColumn;
  width: number;
  resize: (key: string, width: number) => void;
}) {
  const start = useRef({ x: 0, width, scale: 1 });
  const [active, setActive] = useState(false);
  return (
    <button
      type="button"
      className={`tasks-directory-column-resizer ${active ? 'is-active' : ''}`}
      aria-label={`Zmień szerokość kolumny ${column.label.toLocaleLowerCase('pl')}`}
      onPointerDown={(event) => {
        if (event.button) return;
        event.preventDefault();
        const bounds = event.currentTarget.parentElement!.getBoundingClientRect();
        start.current = {
          x: event.clientX,
          width,
          scale: bounds.width / event.currentTarget.parentElement!.offsetWidth || 1,
        };
        event.currentTarget.setPointerCapture(event.pointerId);
        setActive(true);
      }}
      onPointerMove={(event) => {
        if (active)
          resize(
            column.key,
            start.current.width + (event.clientX - start.current.x) / start.current.scale,
          );
      }}
      onPointerUp={() => setActive(false)}
      onPointerCancel={() => setActive(false)}
      onKeyDown={(event) => {
        if (['ArrowLeft', 'ArrowRight'].includes(event.key)) {
          event.preventDefault();
          resize(column.key, width + (event.key === 'ArrowRight' ? 10 : -10));
        }
      }}
      onDoubleClick={() => resize(column.key, column.width)}
    />
  );
}
