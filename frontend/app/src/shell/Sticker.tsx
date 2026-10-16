import { type PointerEvent, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Icon } from '../shared/Icon';
interface Note {
  open: boolean;
  text: string;
  left: number;
  top: number;
  width: number;
  height: number;
}
const clamp = (n: number, min: number, max: number) =>
  Math.min(Math.max(n, min), Math.max(min, max));
function geometry(note: Partial<Note>): Note {
  const left =
    note.left ??
    Math.min(
      innerWidth - 288,
      (parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--sidebar-width')) ||
        56) + 24,
    );
  const top = note.top ?? 92;
  const width = clamp(note.width ?? Math.min(280, innerWidth - 16), 180, innerWidth - left - 8);
  const height = clamp(note.height ?? Math.min(220, innerHeight - 16), 140, innerHeight - top - 8);
  return {
    text: note.text || '',
    open: !!note.open,
    width,
    height,
    left: clamp(left, 8, innerWidth - width - 8),
    top: clamp(top, 8, innerHeight - height - 8),
  };
}
function read(key: string) {
  try {
    const data = JSON.parse(localStorage.getItem(key) || '{}'),
      valid: Partial<Note> = {};
    if (typeof data?.open === 'boolean') valid.open = data.open;
    if (typeof data?.text === 'string') valid.text = data.text;
    for (const field of ['left', 'top', 'width', 'height'] as const)
      if (Number.isFinite(data?.[field])) valid[field] = data[field];
    return geometry(valid);
  } catch {
    return geometry({});
  }
}
export default function Sticker({ user }: { user: string }) {
  const key = 'ancore:sticky-note:v2:user:' + user;
  const [note, setNote] = useState(() => read(key));
  const latest = useRef(note);
  latest.current = note;
  const text = useRef<HTMLTextAreaElement>(null),
    button = useRef<HTMLButtonElement>(null);
  const gesture = useRef<{ id: number; x: number; y: number; note: Note; resize: boolean }>();
  function update(next: Note, save = true) {
    latest.current = next;
    setNote(next);
    if (save) {
      try {
        localStorage.setItem(key, JSON.stringify(next));
      } catch {
        /* Keep the note usable without storage. */
      }
    }
  }
  useEffect(() => {
    if (note.open) text.current?.focus({ preventScroll: true });
  }, [note.open]);
  useEffect(() => {
    const resize = () => {
      if (latest.current.open) update(geometry(latest.current));
    };
    window.addEventListener('resize', resize);
    return () => {
      window.removeEventListener('resize', resize);
      document.body.classList.remove('app-sticky-note-dragging', 'app-sticky-note-resizing');
    };
  }, [key]);
  function start(event: PointerEvent<HTMLElement>, resize: boolean) {
    if (event.button !== 0 && event.pointerType !== 'touch') return;
    if (!resize && (event.target as HTMLElement).closest('button')) return;
    event.preventDefault();
    event.stopPropagation();
    gesture.current = {
      id: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      note: latest.current,
      resize,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
    document.body.classList.add(resize ? 'app-sticky-note-resizing' : 'app-sticky-note-dragging');
  }
  function move(event: PointerEvent<HTMLElement>) {
    const active = gesture.current;
    if (!active || active.id !== event.pointerId) return;
    const dx = event.clientX - active.x,
      dy = event.clientY - active.y;
    update(
      geometry({
        ...active.note,
        ...(active.resize
          ? { width: active.note.width + dx, height: active.note.height + dy }
          : {
              left: clamp(active.note.left + dx, 8, innerWidth - active.note.width - 8),
              top: clamp(active.note.top + dy, 8, innerHeight - active.note.height - 8),
            }),
      }),
      false,
    );
  }
  function finish(event: PointerEvent<HTMLElement>) {
    if (gesture.current?.id !== event.pointerId) return;
    gesture.current = undefined;
    if (event.currentTarget.hasPointerCapture(event.pointerId))
      event.currentTarget.releasePointerCapture(event.pointerId);
    document.body.classList.remove('app-sticky-note-dragging', 'app-sticky-note-resizing');
    update(geometry(latest.current));
  }
  const gestureProps = {
    onPointerMove: move,
    onPointerUp: finish,
    onPointerCancel: finish,
    onLostPointerCapture: finish,
  };
  return (
    <>
      {createPortal(
        <button
          ref={button}
          type="button"
          className={'tasks-icon-button app-topbar__action' + (note.open ? ' is-open' : '')}
          aria-label="Sticker"
          title="Sticker"
          aria-controls="app-sticky-note"
          aria-expanded={note.open}
          onClick={() => update(geometry({ ...note, open: !note.open }))}
        >
          <Icon name="sticky-note" />
        </button>,
        document.getElementById('app-global-actions-host')!,
      )}
      {createPortal(
        <section
          className="app-sticky-note"
          id="app-sticky-note"
          aria-label="Sticker"
          data-react-screen="sticker"
          hidden={!note.open}
          style={{ left: note.left, top: note.top, width: note.width, height: note.height }}
        >
          <header
            className="app-sticky-note__bar"
            onPointerDown={(event) => start(event, false)}
            {...gestureProps}
          >
            <span className="app-sticky-note__title">
              <Icon name="sticky-note" />
              Sticker
            </span>
            <button
              type="button"
              className="app-sticky-note__close"
              aria-label="Zamknij sticker"
              title="Zamknij sticker"
              onClick={() => {
                update({ ...note, open: false });
                button.current?.focus();
              }}
            >
              <Icon name="x" />
            </button>
          </header>
          <label className="u-sr-only" htmlFor="app-sticky-note-text">
            Treść stickera
          </label>
          <textarea
            ref={text}
            className="app-sticky-note__text"
            id="app-sticky-note-text"
            placeholder="Napisz notatkę..."
            value={note.text}
            onChange={(event) => update({ ...note, text: event.target.value })}
          />
          <button
            type="button"
            className="app-sticky-note__resize"
            aria-label="Zmień rozmiar stickera"
            title="Zmień rozmiar stickera"
            onPointerDown={(event) => start(event, true)}
            {...gestureProps}
            onKeyDown={(event) => {
              if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
              event.preventDefault();
              const step = event.shiftKey ? 40 : 12;
              update(
                geometry({
                  ...note,
                  width:
                    note.width +
                    (event.key === 'ArrowRight' ? step : event.key === 'ArrowLeft' ? -step : 0),
                  height:
                    note.height +
                    (event.key === 'ArrowDown' ? step : event.key === 'ArrowUp' ? -step : 0),
                }),
              );
            }}
          />
        </section>,
        document.getElementById('app-sticker-host')!,
      )}
    </>
  );
}
