import { type ReactNode, useEffect, useRef, useState } from 'react';
import { Icon } from './Icon';
import { Modal } from './Modal';

export interface WidgetCatalogItem {
  id: string;
  label: string;
  description: string;
  preview: ReactNode;
  added?: boolean;
  previewWidth?: number;
  previewHeight?: number;
  previewCaption?: string;
}

const normalize = (value: string) =>
  value
    .toLocaleLowerCase('pl')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/ł/g, 'l');

function WidgetPreview({ item }: { item: WidgetCatalogItem }) {
  const viewport = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0.4);
  const width = item.previewWidth ?? 560;
  const height = item.previewHeight ?? 420;
  useEffect(() => {
    const element = viewport.current;
    if (!element) return;
    // Real widget controls are decorative in the catalog, including tab stops.
    element.inert = true;
    const measure = () =>
      setScale(Math.min(element.clientWidth / width, element.clientHeight / height));
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [width, height]);
  return (
    <figure className="widget-catalog-preview">
      <div className="widget-catalog-preview-viewport" ref={viewport} aria-hidden="true">
        <div
          className="widget-catalog-preview-canvas work-summary"
          style={{ width, height, transform: `translate(-50%, -50%) scale(${scale})` }}
        >
          {item.preview}
        </div>
      </div>
      <figcaption>{item.previewCaption || 'Podgląd widżetu'}</figcaption>
    </figure>
  );
}

export default function WidgetCatalog({
  items,
  onAdd,
  onClose,
  disabled = false,
  limitMessage = '',
}: {
  items: WidgetCatalogItem[];
  onAdd: (id: string) => void;
  onClose: () => void;
  disabled?: boolean;
  limitMessage?: string;
}) {
  const [query, setQuery] = useState('');
  const [notice, setNotice] = useState('');
  const entries = items.filter((item) =>
    normalize(`${item.label} ${item.description}`).includes(normalize(query.trim())),
  );
  return (
    <Modal
      title="Dodaj gadżet"
      className="app-modal-panel--compact widget-catalog-modal"
      dialogClassName="widget-catalog-dialog"
      onClose={onClose}
    >
      <div className="tasks-modal__body widget-catalog-body">
        <label className="tasks-search-field widget-catalog-search">
          <Icon name="search" />
          <input
            type="search"
            placeholder="Szukaj gadżetu…"
            aria-label="Szukaj gadżetu"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        {limitMessage ? (
          <p className="widget-catalog-limit" role="status">
            {limitMessage}
          </p>
        ) : null}
        <ul className="widget-catalog-list" aria-label="Dostępne gadżety">
          {entries.map((item) => (
            <li className="widget-catalog-item" key={item.id}>
              <WidgetPreview item={item} />
              <div className="widget-catalog-copy">
                <h3>{item.label}</h3>
                <p>{item.description}</p>
                <button
                  type="button"
                  className="tasks-filter-button"
                  disabled={disabled || item.added || !!limitMessage}
                  aria-label={`${item.added ? 'Dodano' : 'Dodaj'}: ${item.label}`}
                  onClick={() => {
                    onAdd(item.id);
                    setNotice(`Dodano gadżet: ${item.label}.`);
                  }}
                >
                  <Icon name={item.added ? 'check' : 'plus'} />
                  {item.added ? 'Dodano' : 'Dodaj'}
                </button>
              </div>
            </li>
          ))}
        </ul>
        {!entries.length ? (
          <p className="widget-catalog-empty" role="status">
            Brak pasujących gadżetów.
          </p>
        ) : null}
        <span className="u-sr-only" role="status" aria-live="polite">
          {notice}
        </span>
      </div>
    </Modal>
  );
}
