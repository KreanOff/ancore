import { setPageLocation } from '../shared/page';
import { type FormEvent, useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { FormSchema } from '../forms/FormDialog';
import { Icon } from '../shared/Icon';
import { Select } from '../shared/Select';
import { errorMessage } from '../shared/api';
import { type PageProps, PageError, pageRequest } from '../shared/page';
import { useDirtyGuard } from '../shared/useDirtyGuard';
import { safeFragment } from './richText';
import type { Row } from './types';
interface TextData {
  form: FormSchema;
  is_new: boolean;
  back_url: string;
  action: string;
  document: Row | null;
  upgrade_url: string;
}
const commands = [
  ['bold', 'Pogrubienie', 'B'],
  ['italic', 'Kursywa', 'I'],
  ['underline', 'Podkreślenie', 'U'],
  ['insertUnorderedList', 'Lista punktowana', 'list'],
  ['insertOrderedList', 'Lista numerowana', '1.'],
  ['removeFormat', 'Usuń formatowanie', 'T×'],
  ['undo', 'Cofnij', 'rotate-ccw'],
  ['redo', 'Ponów', 'rotate-ccw'],
];
export default function TextPage({ initial, csrfToken }: PageProps) {
  const data = initial.data as TextData,
    field = (name: string) => data.form.fields.find((field) => field.name === name);
  const [title, setTitle] = useState(String(field('title')?.value || '')),
    [revision, setRevision] = useState(String(field('revision')?.value || 1)),
    [action, setAction] = useState(data.action),
    [isNew, setNew] = useState(data.is_new),
    [dirty, setDirty] = useState(data.form.bound),
    [pending, setPending] = useState(false),
    [error, setError] = useState(
      [...data.form.errors, ...data.form.fields.flatMap((field) => field.errors)].join(' '),
    ),
    [status, setStatus] = useState(
      data.is_new ? 'Niezapisany dokument' : `Zapisano ${data.document?.datetime}`,
    ),
    [words, setWords] = useState(0),
    [block, setBlock] = useState('p'),
    [pressed, setPressed] = useState<Record<string, boolean>>({});
  const editor = useRef<HTMLDivElement>(null),
    form = useRef<HTMLFormElement>(null),
    life = useRef(new AbortController()),
    saved = useRef(''),
    range = useRef<Range>(),
    sending = useRef(false),
    saveRef = useRef<() => void>(() => {}),
    titleValue = useRef(title);
  useDirtyGuard(dirty, pending);
  function signature() {
    return JSON.stringify([titleValue.current, editor.current?.innerHTML || '']);
  }
  function update() {
    const changed = signature() !== saved.current;
    setDirty(changed);
    const text = editor.current?.innerText.trim() || '';
    setWords(text ? text.split(/\s+/u).length : 0);
    if (changed && !sending.current) setStatus('Niezapisane zmiany');
  }
  useLayoutEffect(() => {
    editor.current!.replaceChildren(safeFragment(String(field('content')?.value || '')));
    saved.current = data.form.bound ? '' : signature();
    update();
  }, []);
  useEffect(() => {
    const selection = () => {
      const value = getSelection(),
        host = editor.current;
      if (
        !value?.rangeCount ||
        !host?.contains(value.anchorNode) ||
        !host.contains(value.focusNode)
      )
        return;
      range.current = value.getRangeAt(0).cloneRange();
      setPressed(
        Object.fromEntries(
          commands.slice(0, 5).map(([key]) => [key, document.queryCommandState(key)]),
        ),
      );
      const next = document.queryCommandValue('formatBlock').toLowerCase().replace(/[<>]/g, '');
      setBlock(['p', 'h1', 'h2', 'h3', 'blockquote'].includes(next) ? next : 'p');
    };
    const key = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        event.preventDefault();
        saveRef.current();
      }
    };
    document.addEventListener('selectionchange', selection);
    document.addEventListener('keydown', key);
    return () => {
      life.current.abort();
      document.removeEventListener('selectionchange', selection);
      document.removeEventListener('keydown', key);
    };
  }, []);
  function command(name: string, value?: string) {
    editor.current?.focus();
    if (range.current && editor.current?.contains(range.current.commonAncestorContainer)) {
      const selection = getSelection();
      selection?.removeAllRanges();
      selection?.addRange(range.current);
    }
    document.execCommand(name, false, value);
    update();
  }
  async function save(event?: FormEvent) {
    event?.preventDefault();
    if (sending.current || !form.current?.reportValidity()) return;
    update();
    const sent = signature(),
      body = new FormData();
    body.set('title', titleValue.current);
    body.set('content', editor.current!.innerHTML);
    body.set('revision', revision);
    sending.current = true;
    setPending(true);
    setError('');
    setStatus('Zapisywanie…');
    try {
      const result = await pageRequest<{
        url: string;
        revision: number;
        saved_at: string;
        title: string;
      }>(initial.api_url, action, csrfToken, life.current.signal, body);
      if (life.current.signal.aborted) return;
      setAction(result.url);
      setRevision(String(result.revision));
      setNew(false);
      saved.current = sent;
      setPageLocation(result.url);
      document.title = `${result.title} | Dokumenty | ancore`;
      setStatus(`Zapisano o ${result.saved_at}`);
    } catch (e) {
      if (life.current.signal.aborted) return;
      let message = errorMessage(e);
      if (e instanceof PageError && e.data.errors) {
        const fields = e.data.errors as Record<string, { message: string }[]>;
        message =
          Object.values(fields)
            .flat()
            .map((error) => error.message)
            .join(' ') || message;
      }
      setError(message);
      setStatus('Nie zapisano zmian');
    } finally {
      sending.current = false;
      setPending(false);
      if (!life.current.signal.aborted) update();
    }
  }
  saveRef.current = () => void save();
  const download = isNew ? '' : new URL('download/', new URL(action, location.origin)).pathname;
  const upgrade = isNew
    ? ''
    : data.upgrade_url || new URL('upgrade/', new URL(action, location.origin)).pathname;
  return (
    <form
      ref={form}
      className="documents-page office-editor"
      data-react-screen="office-text"
      data-app-full-navigation
      onSubmit={save}
      aria-busy={pending}
    >
      <header className="tasks-topbar tasks-topbar--directory documents-topbar">
        <div className="tasks-titlebar-left">
          <a className="tasks-icon-button" href={data.back_url} aria-label="Wróć do dokumentów">
            <Icon name="arrow-left" />
          </a>
          <h1 className="tasks-topbar-title">{isNew ? 'Nowy dokument' : 'Edytuj dokument'}</h1>
        </div>
        <div className="tasks-titlebar-actions">
          <span className="documents-muted office-save-status" role="status">
            {status}
          </span>
          {!isNew ? (
            <a
              className="btn btn-secondary"
              href={download}
              download
              aria-disabled={dirty || pending}
              onClick={(event) => {
                if (dirty || pending) {
                  event.preventDefault();
                  setError('Zapisz zmiany przed pobraniem dokumentu.');
                }
              }}
            >
              Pobierz DOCX
            </a>
          ) : null}
          <button type="submit" className="btn btn-primary" disabled={pending}>
            Zapisz
          </button>
        </div>
      </header>
      {!isNew ? (
        <div className="documents-results-hint">
          Ten dokument korzysta z edytora tekstu Ancore.{' '}
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={pending}
            onClick={() => {
              if (dirty) {
                setError('Zapisz zmiany przed utworzeniem kopii dokumentu.');
                return;
              }
              const copy = document.createElement('form');
              copy.method = 'post';
              copy.action = upgrade;
              copy.target = '_blank';
              copy.rel = 'noopener';
              const token = document.createElement('input');
              token.type = 'hidden';
              token.name = 'csrfmiddlewaretoken';
              token.value = csrfToken;
              copy.append(token);
              document.body.append(copy);
              copy.submit();
              copy.remove();
            }}
          >
            Utwórz kopię w pełnym edytorze DOCX
          </button>
        </div>
      ) : null}
      <div className="office-editor-scroll">
        <div className="office-editor-metadata">
          <div className="documents-field">
            <label htmlFor="office-text-title">Nazwa dokumentu</label>
            <input
              id="office-text-title"
              name="title"
              className="form-input tasks-inline-input"
              maxLength={255}
              required
              value={title}
              onChange={(event) => {
                titleValue.current = event.target.value;
                setTitle(event.target.value);
                update();
              }}
            />
          </div>
        </div>
        {error ? (
          <div className="tasks-modal__errors office-editor-errors" role="alert">
            {error}
          </div>
        ) : null}
        <div className="office-paper">
          <div className="office-formatbar" role="toolbar" aria-label="Formatowanie dokumentu">
            <Select
              label="Styl akapitu"
              hideLabel
              value={block}
              options={[
                ['p', 'Zwykły tekst'],
                ['h1', 'Nagłówek 1'],
                ['h2', 'Nagłówek 2'],
                ['h3', 'Nagłówek 3'],
                ['blockquote', 'Cytat'],
              ]}
              onChange={(value) => command('formatBlock', value)}
            />
            {commands.map(([key, label, icon], index) => (
              <span key={key} className="react-icon">
                {index === 3 || index === 6 ? (
                  <span className="office-format-separator" aria-hidden="true" />
                ) : null}
                <button
                  type="button"
                  className="tasks-icon-button"
                  aria-label={label}
                  title={label}
                  aria-pressed={index < 5 ? !!pressed[key] : undefined}
                  data-office-command={key}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => command(key)}
                >
                  {key === 'bold' ? (
                    <b aria-hidden="true">B</b>
                  ) : key === 'italic' ? (
                    <i aria-hidden="true">I</i>
                  ) : key === 'underline' ? (
                    <u aria-hidden="true">U</u>
                  ) : icon.length <= 2 ? (
                    icon
                  ) : (
                    <Icon name={icon} />
                  )}
                </button>
              </span>
            ))}
          </div>
          <div
            ref={editor}
            className="office-content"
            contentEditable
            suppressContentEditableWarning
            role="textbox"
            aria-multiline="true"
            aria-label="Treść dokumentu"
            data-placeholder="Zacznij pisać…"
            onInput={update}
            onPaste={(event) => {
              event.preventDefault();
              document.execCommand('insertText', false, event.clipboardData.getData('text/plain'));
              update();
            }}
            onDrop={(event) => event.preventDefault()}
            onDragOver={(event) => event.preventDefault()}
          />
          <footer className="office-paper-footer">
            <span>Liczba słów: {words}</span>
            <span>Zapisz: Ctrl+S / ⌘S</span>
          </footer>
        </div>
      </div>
    </form>
  );
}
