import { type DragEvent, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { RowIcon } from './Rows';
import type { DirectoryData, Row } from './types';
const mime = 'application/x-ancore-document';
export function useDrag(
  data: DirectoryData,
  busy: boolean,
  move: (url: string, target: string, settle: () => Promise<void>) => Promise<boolean | undefined>,
  upload: (url: string, files: File[]) => void,
) {
  const [source, setSource] = useState<Row | null>(null),
    [target, setTarget] = useState<{ value: string; label: string } | null>(null),
    [message, setMessage] = useState(''),
    [moving, setMoving] = useState(false);
  const drag = useRef<Row | null>(null),
    preview = useRef<HTMLDivElement>(null),
    canvas = useRef<HTMLCanvasElement | null>(null),
    until = useRef(0),
    movingRef = useRef(false),
    point = useRef({ x: 0, y: 0 });
  function finish() {
    drag.current = null;
    setSource(null);
    setTarget(null);
    setMessage('');
    canvas.current?.remove();
    canvas.current = null;
    setMoving(false);
  }
  useLayoutEffect(() => {
    if (source && preview.current)
      preview.current.style.transform = `translate3d(${point.current.x + 18}px,${point.current.y + 18}px,0)`;
  }, [source]);
  useEffect(() => {
    const preventFileNavigation = (event: globalThis.DragEvent) => {
      if ([...(event.dataTransfer?.types || [])].some((type) => type === 'Files' || type === mime))
        event.preventDefault();
    };
    const key = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !movingRef.current) finish();
    };
    const blur = () => {
      if (!movingRef.current) finish();
    };
    window.addEventListener('blur', blur);
    document.addEventListener('keydown', key);
    document.addEventListener('dragover', preventFileNavigation);
    document.addEventListener('drop', preventFileNavigation);
    return () => {
      window.removeEventListener('blur', blur);
      document.removeEventListener('keydown', key);
      document.removeEventListener('dragover', preventFileNavigation);
      document.removeEventListener('drop', preventFileNavigation);
      canvas.current?.remove();
      preview.current?.getAnimations().forEach((animation) => animation.cancel());
    };
  }, []);
  const external = (event: DragEvent) => [...event.dataTransfer.types].includes('Files');
  const relevant = (event: DragEvent) =>
    external(event) || [...event.dataTransfer.types].includes(mime);
  function destination(event: DragEvent) {
    if (busy || data.view === 'trash') return null;
    const element = (event.target as Element).closest<HTMLElement>('[data-doc-target]');
    if (!element || element.closest('[inert]')) return null;
    const value = element.dataset.docTarget!;
    if (!external(event) && (value === drag.current?.target || value === drag.current?.location))
      return null;
    return { value, label: element.dataset.docLabel || 'Dokumenty' };
  }
  return {
    dragged: source?.id || null,
    drop: target?.value || null,
    handlers: {
      onDragStart(event: DragEvent) {
        const element = (event.target as Element).closest<HTMLElement>('[data-doc-row]');
        const row = data.rows.find((item) => item.id === element?.dataset.docRow);
        if (
          !row?.move_url ||
          busy ||
          data.office ||
          data.view === 'trash' ||
          (event.target as Element).closest('button,input,select,textarea,.documents-item-actions')
        ) {
          event.preventDefault();
          return;
        }
        drag.current = row;
        point.current = { x: event.clientX, y: event.clientY };
        setSource(row);
        event.dataTransfer.clearData();
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData(
          mime,
          JSON.stringify({
            scope: data.base_url,
            url: row.move_url,
            location: row.location,
            folder: row.target || '',
          }),
        );
        const node = document.createElement('canvas');
        node.width = node.height = 1;
        node.className = 'documents-drag-native-image';
        document.body.append(node);
        canvas.current = node;
        event.dataTransfer.setDragImage(node, 0, 0);
      },
      onDragOver(event: DragEvent) {
        if (!relevant(event)) return;
        event.preventDefault();
        const next = destination(event);
        setTarget((current) => (current?.value === next?.value ? current : next));
        event.dataTransfer.dropEffect = next ? (external(event) ? 'copy' : 'move') : 'none';
        if (preview.current) {
          const rect = preview.current.getBoundingClientRect();
          preview.current.style.transform = `translate3d(${Math.max(8, event.clientX + rect.width + 24 < innerWidth ? event.clientX + 18 : event.clientX - rect.width - 18)}px,${Math.max(8, event.clientY + rect.height + 24 < innerHeight ? event.clientY + 18 : event.clientY - rect.height - 18)}px,0)`;
        }
        if (!source)
          setMessage(
            next
              ? `Upuść, aby przesłać pliki do: ${next.label}`
              : 'Upuść na folder lub wybrany dysk.',
          );
      },
      onDragLeave(event: DragEvent) {
        if (!event.relatedTarget) {
          setTarget(null);
          setMessage('');
        }
      },
      onDragEnd() {
        until.current = Date.now() + 250;
        if (!movingRef.current) finish();
      },
      onClickCapture(event: React.MouseEvent) {
        if (Date.now() < until.current) {
          event.preventDefault();
          event.stopPropagation();
        }
      },
      async onDrop(event: DragEvent) {
        if (!relevant(event)) return;
        event.preventDefault();
        event.stopPropagation();
        const next = destination(event),
          files = Array.from(event.dataTransfer.files),
          payload = event.dataTransfer.getData(mime);
        const directories = Array.from(event.dataTransfer.items).some(
          (item) =>
            (
              item as DataTransferItem & {
                webkitGetAsEntry?: () => { isDirectory: boolean } | null;
              }
            ).webkitGetAsEntry?.()?.isDirectory,
        );
        if (!next) {
          finish();
          return;
        }
        if (external(event)) {
          finish();
          if (directories || !files.length) {
            window.showNotification?.(
              'Przeciągnij pojedyncze pliki. Przesyłanie folderów z komputera nie jest obsługiwane.',
              'error',
            );
            return;
          }
          const url = new URL(data.base_url + 'upload/', location.origin);
          const [kind, id] = next.value.split(':');
          if (kind === 'folder' || kind === 'library') url.searchParams.set(kind, id);
          upload(url.pathname + url.search, files);
          return;
        }
        let value;
        try {
          value = JSON.parse(payload);
        } catch {
          finish();
          return;
        }
        if (
          !value ||
          value.scope !== data.base_url ||
          typeof value.url !== 'string' ||
          !value.url.startsWith(data.base_url) ||
          !/^(?:folders\/\d+|[0-9a-f-]{36})\/move\/$/.test(value.url.slice(data.base_url.length))
        ) {
          window.showNotification?.(
            'Przenoś elementy w obrębie tego samego modułu i Workspace.',
            'error',
          );
          finish();
          return;
        }
        if (value.folder === next.value || value.location === next.value) {
          finish();
          return;
        }
        const element = (event.target as Element).closest<HTMLElement>('[data-doc-target]');
        movingRef.current = true;
        setMoving(true);
        try {
          await move(value.url, next.value, async () => {
            const node = preview.current;
            if (
              !node ||
              !element?.isConnected ||
              matchMedia('(prefers-reduced-motion: reduce)').matches
            )
              return;
            const destination = element.getBoundingClientRect(),
              bounds = node.getBoundingClientRect();
            const animation = node.animate(
              [
                { transform: node.style.transform, opacity: 1 },
                {
                  transform: `translate3d(${destination.left + destination.width / 2 - bounds.width * 0.1}px,${destination.top + destination.height / 2 - bounds.height * 0.1}px,0) scale(.2)`,
                  opacity: 0,
                },
              ],
              { duration: 180, easing: 'cubic-bezier(.2,.7,.2,1)', fill: 'forwards' },
            );
            try {
              await animation.finished;
            } catch {}
          });
        } finally {
          movingRef.current = false;
          finish();
        }
      },
    },
    overlay: (
      <>
        {source
          ? createPortal(
              <div
                ref={preview}
                className={`documents-drag-preview ${target ? 'has-drop-target' : ''}`}
                style={{
                  zoom: 1 / (parseFloat(getComputedStyle(document.documentElement).zoom) || 1),
                }}
                aria-hidden="true"
              >
                <div className="documents-drag-preview__card">
                  <span className="documents-drag-preview__icon">
                    <RowIcon row={source} />
                  </span>
                  <div className="documents-drag-preview__copy">
                    <span className="documents-drag-preview__name">{source.name}</span>
                    <span className="documents-drag-preview__meta">
                      {source.row_kind === 'folder'
                        ? 'Folder'
                        : `${source.extension} · ${source.size}`}
                    </span>
                  </div>
                  <span className="documents-drag-preview__hint">
                    {moving
                      ? 'Przenoszenie…'
                      : target
                        ? `Przenieś do: ${target.label}`
                        : 'Wybierz folder docelowy'}
                  </span>
                </div>
              </div>,
              document.body,
            )
          : null}
        {message ? (
          <p className="documents-drag-status" role="status">
            {message}
          </p>
        ) : null}
      </>
    ),
  };
}
