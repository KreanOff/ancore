import { type FormEvent, useEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { FieldControl, type FormSchema } from '../forms/FormDialog';
import { FieldLabel } from '../shared/FieldLabel';
import { Modal } from '../shared/Modal';
import { Icon } from '../shared/Icon';
import { errorMessage } from '../shared/api';
import { type Page, PageError, pageRequest } from '../shared/page';
import { DriveIcon, FileIcon, FolderIcon } from './Icons';
import { bytes, type DocumentModal } from './types';
export default function DocumentDialog({
  data,
  api,
  token,
  files = [],
  onClose,
  onOpen,
  onSaved,
}: {
  data: DocumentModal;
  api: string;
  token: string;
  files?: File[];
  onClose: () => void;
  onOpen: (url: string) => void;
  onSaved: (url: string) => unknown;
}) {
  const [schema, setSchema] = useState(data.form),
    [pending, setPending] = useState(false),
    [dirty, setDirty] = useState(false),
    [error, setError] = useState(''),
    [color, setColor] = useState(data.preview_color),
    [selected, setSelected] = useState<File[]>(files),
    [created, setCreated] = useState<{ editor_url: string; redirect: string } | null>(null),
    [imageState, setImageState] = useState('loading');
  const form = useRef<HTMLFormElement>(null),
    input = useRef<HTMLInputElement>(null),
    life = useRef(new AbortController()),
    sending = useRef(false);
  const item = data.document,
    preview = data.preview;
  useEffect(() => {
    const element = form.current;
    const change = () => setDirty(true);
    element?.addEventListener('input', change);
    element?.addEventListener('change', change);
    return () => {
      life.current.abort();
      element?.removeEventListener('input', change);
      element?.removeEventListener('change', change);
    };
  }, []);
  useEffect(() => {
    if (files.length && input.current) {
      const transfer = new DataTransfer();
      files.forEach((file) => transfer.items.add(file));
      input.current.files = transfer.files;
      setDirty(true);
      form.current?.requestSubmit();
    }
  }, []);
  function close() {
    const element =
      form.current?.closest<HTMLElement>('.tasks-modal') ||
      document.querySelector<HTMLElement>('.documents-preview-modal');
    if (element) window.AncoreTaskModals?.close(element);
  }
  function switchModal(url: string) {
    if (!dirty) {
      onOpen(url);
      return;
    }
    window.showConfirmModal({
      title: 'Niezapisane zmiany',
      message: 'Otworzyć inny widok bez zapisania zmian?',
      confirmText: 'Otwórz bez zapisu',
      cancelText: 'Wróć do edycji',
      onConfirm: () => {
        setDirty(false);
        onOpen(url);
      },
    });
  }
  function dropFiles(files: File[]) {
    if (!input.current || pending) return;
    const transfer = new DataTransfer();
    files.forEach((file) => transfer.items.add(file));
    input.current.files = transfer.files;
    setSelected(files);
    setDirty(true);
  }
  async function save(event?: FormEvent) {
    event?.preventDefault();
    if (sending.current || created || !form.current) return;
    const body = new FormData(form.current);
    sending.current = true;
    setPending(true);
    setError('');
    let tab: Window | null = null;
    if (data.create_editor) {
      tab = window.open('about:blank', '_blank');
      if (tab) {
        tab.opener = null;
        tab.document.title = 'Otwieranie dokumentu | Ancore';
        tab.document.body.textContent = 'Tworzenie dokumentu…';
      }
    }
    try {
      const result = await pageRequest<{ redirect: string; editor_url?: string }>(
        api,
        data.action,
        token,
        life.current.signal,
        body,
      );
      if (life.current.signal.aborted) return;
      if (result.editor_url) {
        if (tab && !tab.closed) {
          tab.location.replace(result.editor_url);
          tab = null;
        } else {
          setCreated({ editor_url: result.editor_url, redirect: result.redirect });
          setDirty(false);
          return;
        }
      }
      flushSync(() => {
        setDirty(false);
        setPending(false);
      });
      await onSaved(result.redirect);
    } catch (e) {
      if (life.current.signal.aborted) return;
      if (e instanceof PageError) {
        const corrected = (e.data as unknown as Page).data as DocumentModal | undefined;
        if (corrected?.form) setSchema(corrected.form);
      }
      setError(errorMessage(e));
      requestAnimationFrame(() => {
        const invalid = form.current?.querySelector<HTMLElement>('[aria-invalid=true]');
        (
          invalid?.closest('.ancore-custom-select')?.querySelector<HTMLElement>('button') || invalid
        )?.focus();
      });
    } finally {
      if (tab && !tab.closed) tab.close();
      sending.current = false;
      setPending(false);
    }
  }
  async function operation(url: string, newTab = false) {
    if (sending.current) return;
    sending.current = true;
    setPending(true);
    setError('');
    let tab: Window | null = newTab ? window.open('about:blank', '_blank') : null;
    if (tab) tab.opener = null;
    try {
      const result = await pageRequest<{ redirect: string }>(
        api,
        url,
        token,
        life.current.signal,
        new FormData(),
      );
      if (newTab && result.redirect.endsWith('/editor/')) {
        if (tab && !tab.closed) {
          tab.location.replace(result.redirect);
          tab = null;
          flushSync(() => setPending(false));
          close();
        } else setCreated({ editor_url: result.redirect, redirect: data.return_url });
      } else {
        tab?.close();
        tab = null;
        flushSync(() => setPending(false));
        await onSaved(result.redirect);
      }
    } catch (e) {
      if (!life.current.signal.aborted) setError(errorMessage(e));
    } finally {
      tab?.close();
      sending.current = false;
      setPending(false);
    }
  }
  const errors = (schema: FormSchema | null) => (
    <>
      {error ? (
        <div className="tasks-modal__errors app-form-wide" role="alert">
          {error}
        </div>
      ) : null}
      {schema?.errors.length ? (
        <div className="tasks-modal__errors app-form-wide" role="alert">
          {schema.errors.map((message, index) => (
            <p key={index}>{message}</p>
          ))}
        </div>
      ) : null}
    </>
  );
  if (preview)
    return (
      <Modal
        title={data.title}
        className="documents-modal documents-preview-modal"
        pending={pending}
        onClose={() => {
          if (created) void onSaved(created.redirect);
          else onClose();
        }}
      >
        <div className="tasks-modal__form">
          <div
            className="tasks-modal__body documents-preview-body"
            tabIndex={0}
            aria-label="Zawartość pliku"
          >
            {errors(null)}
            {data.convert_url ? (
              <div className="office-import-form">
                <p className="documents-preview-notice">
                  Utwórz kopię w nowym formacie do edycji. Oryginalny plik zostanie zachowany.
                </p>
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={pending}
                  onClick={() => void operation(data.convert_url, true)}
                >
                  Otwórz kopię w pełnym edytorze
                </button>
              </div>
            ) : null}
            {data.import_url ? (
              <div className="office-import-form">
                <p className="documents-preview-notice">
                  Możesz redagować kopię samego tekstu, bez obrazów i układu oryginału. Oryginalny
                  plik zostanie zachowany.
                </p>
                <button
                  type="button"
                  className="btn btn-secondary"
                  disabled={pending}
                  onClick={() => void operation(data.import_url)}
                >
                  Utwórz edytowalną kopię
                </button>
              </div>
            ) : null}
            {created ? (
              <p className="documents-preview-notice">
                <a href={created.editor_url} target="_blank" rel="noopener">
                  Otwórz edytor w nowej karcie
                </a>
              </p>
            ) : null}
            {preview.note ? <p className="documents-preview-notice">{preview.note}</p> : null}
            {preview.truncated ? (
              <p className="documents-preview-notice" role="status">
                Wyświetlono część zawartości ze względu na rozmiar pliku. Pobierz plik, aby zobaczyć
                całość.
              </p>
            ) : null}
            {preview.kind === 'image' ? (
              <>
                {imageState === 'loading' ? (
                  <p className="documents-preview-notice" role="status">
                    Ładowanie podglądu…
                  </p>
                ) : null}
                <img
                  className="documents-preview-image"
                  src={data.content_url}
                  alt={item?.name || data.title}
                  hidden={imageState === 'error'}
                  onLoad={() => setImageState('loaded')}
                  onError={() => setImageState('error')}
                />
                {imageState === 'error' ? (
                  <p className="documents-preview-notice" role="alert">
                    Nie udało się wyświetlić obrazu. Spróbuj ponownie lub pobierz plik.
                  </p>
                ) : null}
              </>
            ) : preview.kind === 'pdf' ? (
              <iframe
                className="documents-preview-pdf"
                src={data.content_url}
                title={`Podgląd PDF: ${data.title}`}
              />
            ) : preview.kind === 'text' ? (
              preview.text ? (
                <pre className="documents-preview-text">{preview.text}</pre>
              ) : (
                <p className="documents-preview-notice">Brak tekstu do wyświetlenia.</p>
              )
            ) : preview.kind === 'sheets' ? (
              preview.sheets?.length ? (
                preview.sheets.map((sheet, index) => (
                  <section key={index} className="documents-preview-sheet" aria-label={sheet.name}>
                    <h3>{sheet.name}</h3>
                    {sheet.rows.length ? (
                      <div
                        className="documents-preview-table-scroll"
                        tabIndex={0}
                        role="region"
                        aria-label={`Dane: ${sheet.name}`}
                      >
                        <table className="documents-preview-table">
                          <tbody>
                            {sheet.rows.map((row, index) => (
                              <tr key={index}>
                                <th scope="row">{row.number}</th>
                                {row.cells.map((cell, index) => (
                                  <td key={index}>{cell}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <p className="documents-preview-notice">Arkusz jest pusty.</p>
                    )}
                  </section>
                ))
              ) : (
                <p className="documents-preview-notice">Brak danych do wyświetlenia.</p>
              )
            ) : preview.kind === 'archive' || preview.kind === 'hard-drive' ? (
              preview.entries?.length ? (
                <div
                  className="documents-preview-table-scroll"
                  tabIndex={0}
                  role="region"
                  aria-label="Zawartość archiwum"
                >
                  <table className="documents-preview-table">
                    <thead>
                      <tr>
                        <th scope="col">Nazwa</th>
                        <th scope="col">Rozmiar</th>
                      </tr>
                    </thead>
                    <tbody>
                      {preview.entries.map((entry, index) => (
                        <tr key={index}>
                          <td>
                            {entry.name}
                            {entry.folder ? ' (folder)' : ''}
                          </td>
                          <td>{bytes(entry.size)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="documents-preview-notice">Archiwum jest puste.</p>
              )
            ) : (
              <div className="documents-preview-fallback" role="status">
                <FileIcon variant={item?.variant} />
                <p>{preview.message}</p>
              </div>
            )}
          </div>
          <footer className="tasks-modal__footer">
            <button
              type="button"
              className="btn btn-secondary"
              disabled={pending}
              onClick={() => onOpen(item!.edit_url)}
            >
              Edytuj dane
            </button>
            {preview.kind !== 'unavailable' ? (
              <a href={item?.download_url} className="btn btn-primary" download>
                <Icon name="download" />
                Pobierz
              </a>
            ) : null}
            <button type="button" className="btn btn-secondary" disabled={pending} onClick={close}>
              Zamknij
            </button>
          </footer>
        </div>
      </Modal>
    );
  return (
    <Modal
      title={created ? 'Dokument utworzony' : data.title}
      className="documents-modal"
      dirty={dirty}
      pending={pending}
      onClose={() => {
        if (created) void onSaved(created.redirect);
        else onClose();
      }}
    >
      <form
        ref={form}
        className="tasks-modal__form"
        onSubmit={save}
        aria-busy={pending}
        encType="multipart/form-data"
        onDragOver={(e) => {
          if (data.upload && e.dataTransfer.types.includes('Files')) {
            e.preventDefault();
            e.stopPropagation();
          }
        }}
        onDrop={(e) => {
          if (!data.upload) return;
          e.preventDefault();
          e.stopPropagation();
          const directories = Array.from(e.dataTransfer.items).some(
            (item) => item.webkitGetAsEntry?.()?.isDirectory,
          );
          if (directories) {
            setError(
              'Przeciągnij pojedyncze pliki. Przesyłanie folderów z komputera nie jest obsługiwane.',
            );
            return;
          }
          dropFiles(Array.from(e.dataTransfer.files));
        }}
      >
        <div className="tasks-modal__body documents-form app-form-layout">
          {errors(schema)}
          {created ? (
            <p className="documents-muted app-form-wide" role="status">
              Dokument został zapisany. Otwórz edytor w nowej karcie.
            </p>
          ) : (
            <>
              {data.template_create ? (
                <p className="documents-muted app-form-wide">
                  {data.has_templates
                    ? 'Powstanie niezależna kopia ostatnio zapisanej treści szablonu. Najpierw zapisz zmiany w jego edytorze.'
                    : 'Nie masz jeszcze szablonów. W menu dokumentu DOCX, XLSX, PPTX lub PDF wybierz „Używaj jako szablonu”.'}
                </p>
              ) : null}
              {data.location ? (
                <p className="documents-muted documents-modal-location app-form-wide">
                  {data.location}
                </p>
              ) : null}
              {item ? (
                <div className="documents-file-summary app-form-wide">
                  <span className="documents-file-icon">
                    <FileIcon variant={item.variant} />
                  </span>
                  <div>
                    {item.filename}
                    <small>
                      {item.extension} · {item.size} · Dodano {item.created}
                    </small>
                  </div>
                  <a
                    className="tasks-icon-button documents-icon-button"
                    href={item.download_url}
                    download
                    aria-label="Pobierz plik"
                  >
                    <Icon name="download" />
                  </a>
                </div>
              ) : null}
              <fieldset className="resources-react-fieldset" disabled={pending}>
                {schema?.fields
                  .filter((field) => ['name', 'title'].includes(field.name))
                  .map((field) => (
                    <div key={field.name} className="app-form-heading" hidden={field.hidden}>
                      <FieldControl field={field} />
                    </div>
                  ))}
                {schema?.fields
                  .filter((field) => field.name === 'description')
                  .map((field) => (
                    <div key={field.name} className="app-form-description" hidden={field.hidden}>
                      <FieldControl field={field} />
                    </div>
                  ))}
                {schema?.fields
                  .filter((field) => !['name', 'title', 'description'].includes(field.name))
                  .map((field) =>
                    field.name === 'color' ? (
                      <div
                        key={field.name}
                        className="documents-field tasks-form-field app-form-field"
                      >
                        <FieldLabel
                          htmlFor={field.id}
                          label={field.label}
                          helpText="Kliknij próbkę, aby wybrać kolor."
                          helpId={`${field.id}_help`}
                          helpLabel={field.label}
                        />
                        <div className="documents-color-control">
                          <span className="documents-color-preview" aria-hidden="true">
                            {data.color_kind === 'library' ? (
                              <DriveIcon color={color} />
                            ) : (
                              <FolderIcon color={color} />
                            )}
                          </span>
                          <input
                            id={field.id}
                            type="color"
                            className="documents-color-input"
                            name={field.name}
                            aria-describedby={`${field.id}_help`}
                            value={/^#[0-9a-f]{6}$/i.test(color) ? color : data.default_color}
                            onChange={(event) => {
                              setColor(event.target.value);
                              setDirty(true);
                            }}
                          />
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            onClick={() => {
                              setColor(data.default_color);
                              setDirty(true);
                            }}
                          >
                            Domyślny
                          </button>
                        </div>
                        {field.errors.length ? (
                          <div className="tasks-modal__errors" role="alert">
                            {field.errors.join(' ')}
                          </div>
                        ) : null}
                      </div>
                    ) : field.type === 'file' ? (
                      <div
                        key={field.name}
                        className="documents-field tasks-form-field app-form-field app-form-wide"
                      >
                        <label htmlFor={field.id}>
                          {field.label}
                          {field.label_required ? ' *' : ''}
                        </label>
                        <div className={data.upload ? 'documents-upload-control' : undefined}>
                          {data.upload ? (
                            <p className="documents-upload-hint">
                              <Icon name="cloud-upload" />
                              <span>
                                Przeciągnij pliki tutaj lub wybierz je z komputera
                                <small>
                                  {data.office_upload
                                    ? 'Dokumenty, arkusze i prezentacje: PDF, DOCX, XLSX, PPTX, DOC, XLS, PPT, CSV, RTF i TXT.'
                                    : 'Dokumenty, arkusze, obrazy i archiwa.'}{' '}
                                  Maks. {data.max_size} na plik, do 20 plików jednocześnie.
                                </small>
                              </span>
                            </p>
                          ) : null}
                          <input
                            ref={input}
                            id={field.id}
                            name={field.name}
                            type="file"
                            className="form-input"
                            multiple={field.multiple}
                            accept={field.attrs.accept}
                            required={field.required}
                            aria-invalid={!!field.errors.length}
                            onChange={(e) => {
                              setSelected(Array.from(e.target.files || []));
                              setDirty(true);
                            }}
                          />
                        </div>
                        {selected.length ? (
                          <ul
                            className="file-list documents-upload-files"
                            aria-label="Wybrane pliki"
                            aria-live="polite"
                            aria-atomic="true"
                          >
                            {selected.map((file, index) => (
                              <li key={index} className="file-item">
                                <div className="file-details">
                                  <div className="file-name">{file.name}</div>
                                  <div className="file-size">{bytes(file.size)}</div>
                                </div>
                              </li>
                            ))}
                          </ul>
                        ) : null}
                        {field.errors.length ? (
                          <div className="tasks-modal__errors" role="alert">
                            {field.errors.join(' ')}
                          </div>
                        ) : null}
                      </div>
                    ) : (
                      <FieldControl key={field.name} field={field} />
                    ),
                  )}
              </fieldset>
            </>
          )}
        </div>
        <footer className="tasks-modal__footer">
          {item && !created ? (
            <button
              type="button"
              className="btn btn-secondary"
              disabled={pending}
              onClick={() => {
                if (item.full_editor) window.open(item.editor_url, '_blank', 'noopener');
                else switchModal(item.preview_url!);
              }}
            >
              {item.full_editor ? 'Otwórz edytor' : 'Podgląd pliku'}
            </button>
          ) : null}
          <button
            type="button"
            className="btn btn-secondary"
            disabled={pending}
            onClick={() => {
              if (created) {
                void onSaved(created.redirect);
              } else close();
            }}
          >
            {created ? 'Wróć do dokumentów' : 'Anuluj'}
          </button>
          {created ? (
            <a href={created.editor_url} className="btn btn-primary" target="_blank" rel="noopener">
              Otwórz edytor
            </a>
          ) : (
            <button
              type="submit"
              className="tasks-modal__submit"
              disabled={pending || (data.template_create && !data.has_templates)}
            >
              {pending ? 'Zapisywanie…' : schema?.submit_label}
            </button>
          )}
        </footer>
      </form>
    </Modal>
  );
}
