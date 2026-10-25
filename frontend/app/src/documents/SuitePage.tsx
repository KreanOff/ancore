import { useEffect, useRef, useState } from 'react';
import type { PageProps } from '../shared/page';
import { Icon } from '../shared/Icon';
import { useDirtyGuard } from '../shared/useDirtyGuard';
import { FileIcon } from './Icons';
import { documentRequest } from './requests';
import { useOffice } from './useOffice';
import type { SuiteData } from './types';
export default function SuitePage({ initial, csrfToken }: PageProps) {
  const data = initial.data as SuiteData,
    item = data.document,
    canRename = !initial.read_only && !!data.rename_url,
    office = useOffice(data, csrfToken);
  const [saved, setSaved] = useState(item.name),
    [title, setTitle] = useState(item.name),
    [editing, setEditing] = useState(false),
    [pending, setPending] = useState(false),
    [error, setError] = useState('');
  const input = useRef<HTMLInputElement>(null),
    button = useRef<HTMLButtonElement>(null),
    life = useRef(new AbortController()),
    active = useRef(false),
    sending = useRef(false);
  useDirtyGuard(office.dirty || (canRename && editing && title.trim() !== saved), pending);
  useEffect(() => () => life.current.abort(), []);
  useEffect(() => {
    document.title = `${saved} | ${data.drive ? 'Dysk' : 'Dokumenty'} | ancore`;
  }, [saved, data.drive]);
  function finish(focus: boolean) {
    active.current = false;
    setEditing(false);
    setTitle(saved);
    setError('');
    if (focus) requestAnimationFrame(() => button.current?.focus());
  }
  function begin() {
    if (!canRename || sending.current) return;
    active.current = true;
    setEditing(true);
    requestAnimationFrame(() => {
      input.current?.focus();
      input.current?.select();
    });
  }
  async function persist(focus = false) {
    if (!canRename || !active.current || sending.current) return;
    const value = title.trim();
    if (value === saved) {
      finish(focus);
      return;
    }
    setError('');
    if (!value) {
      setError('Podaj nazwę pliku.');
      if (focus) input.current?.focus();
      return;
    }
    sending.current = true;
    setPending(true);
    const body = new FormData();
    body.set('title', value);
    try {
      const result = await documentRequest<{ title: string }>(
        data.rename_url,
        csrfToken,
        life.current.signal,
        body,
      );
      if (life.current.signal.aborted) return;
      setSaved(result.title);
      setTitle(result.title);
      active.current = false;
      setEditing(false);
      if (focus && document.activeElement === input.current)
        requestAnimationFrame(() => button.current?.focus());
    } catch (e) {
      if (!life.current.signal.aborted)
        setError(
          e instanceof Error
            ? e.message
            : 'Nie udało się zapisać nazwy. Sprawdź połączenie i spróbuj ponownie.',
        );
    } finally {
      sending.current = false;
      setPending(false);
    }
  }
  return (
    <div
      className="documents-page office-suite"
      data-react-screen="office-suite"
      data-app-full-navigation
    >
      <header
        className="tasks-topbar tasks-topbar--directory documents-topbar office-suite-topbar"
        aria-label="Pasek dokumentu"
      >
        <div className="tasks-titlebar-left tasks-project-breadcrumb">
          <a
            className="tasks-issue-close"
            href={data.back_url}
            aria-label={data.drive ? 'Wróć do dysku' : 'Wróć do dokumentów'}
            title={data.drive ? 'Wróć do dysku' : 'Wróć do dokumentów'}
          >
            <Icon name="arrow-left" />
          </a>
          <span className="office-suite-file-icon" aria-hidden="true">
            <FileIcon variant={item.variant} />
          </span>
          <h1 className="tasks-topbar-title office-suite-title" aria-busy={pending}>
            {canRename ? (
              <>
                <button
                  ref={button}
                  type="button"
                  className="office-suite-title-button"
                  hidden={editing}
                  aria-label={`Zmień nazwę: ${saved}`}
                  title={`Zmień nazwę: ${saved}`}
                  onClick={begin}
                >
                  {saved}
                </button>
                <input
                  ref={input}
                  className="form-input office-suite-title-input"
                  type="text"
                  hidden={!editing}
                  value={title}
                  maxLength={255}
                  size={Math.max(12, Math.min(60, Array.from(title).length + 1))}
                  aria-label="Nazwa pliku"
                  aria-describedby="suite-title-hint suite-title-error"
                  aria-invalid={!!error}
                  autoComplete="off"
                  readOnly={pending}
                  onChange={(e) => {
                    setTitle(e.target.value);
                    setError('');
                  }}
                  onBlur={() => void persist()}
                  onKeyDown={(e) => {
                    if (e.nativeEvent.isComposing || !['Enter', 'Escape'].includes(e.key)) return;
                    e.preventDefault();
                    if (pending) return;
                    if (e.key === 'Escape') finish(true);
                    else void persist(true);
                  }}
                />
              </>
            ) : (
              <span className="office-suite-title-text" title={saved}>
                {saved}
              </span>
            )}
          </h1>
        </div>
      </header>
      {canRename ? (
        <>
          <span id="suite-title-hint" className="u-sr-only">
            Enter zapisuje nazwę, Escape anuluje. Kliknięcie poza polem także zapisuje zmianę.
          </span>
          <span className="u-sr-only" role="status" aria-live="polite" aria-atomic="true">
            {pending
              ? 'Zapisywanie nazwy…'
              : error
                ? 'Błąd zapisu nazwy'
                : editing && title.trim() !== saved
                  ? 'Nazwa do zapisania'
                  : 'Nazwa zapisana'}
          </span>
        </>
      ) : null}
      <span className="u-sr-only" role="status" aria-live="polite">
        {office.status}
      </span>
      {canRename ? (
        <div
          id="suite-title-error"
          className="office-suite-error tasks-modal__errors"
          role="alert"
          hidden={!error}
        >
          {error}
        </div>
      ) : null}
      <div className="office-suite-error tasks-modal__errors" role="alert" hidden={!office.error}>
        <span>{office.error}</span>
        {office.retry ? (
          <button type="button" className="btn btn-secondary btn-sm" onClick={office.save}>
            Ponów zapis
          </button>
        ) : null}
      </div>
      {data.board_url ? (
        <iframe
          ref={office.frame}
          className="office-suite-frame"
          src={data.board_url}
          title="Edytor tablicy"
          allow="clipboard-read; clipboard-write"
        />
      ) : data.editor_config ? (
        <div className="office-suite-frame">
          <div ref={office.holder} id="office-doc-editor" />
        </div>
      ) : (
        <div className="documents-empty office-suite-unavailable">
          <div>
            <Icon name="file-text" />
            <h3>Edytor biurowy jest niedostępny</h3>
            <p>Połączenie z serwerem edycji wymaga konfiguracji przez administratora Ancore.</p>
            <p>Dokument jest zapisany. Możesz go pobrać lub wrócić do katalogu.</p>
            <a className="btn btn-secondary" href={item.download_url} download>
              Pobierz
            </a>
            <a className="btn btn-secondary" href={data.back_url}>
              {data.drive ? 'Wróć do dysku' : 'Wróć do dokumentów'}
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
