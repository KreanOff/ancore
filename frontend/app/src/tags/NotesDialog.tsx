import { type FormEvent, useEffect, useRef, useState } from 'react';
import { Icon } from '../shared/Icon';
import { Modal } from '../shared/Modal';
import { type Page, type PageProps, pageRequest } from '../shared/page';
import { errorMessage } from '../shared/api';
import { dateLabel } from '../spaces/types';
import type { Tag, TagsData } from './types';
export default function NotesDialog({
  tag,
  canEdit,
  initial,
  csrfToken,
  close,
  updated,
}: PageProps & {
  tag: Tag;
  canEdit: boolean;
  close: () => void;
  updated: (data: TagsData) => void;
}) {
  const [message, setMessage] = useState(''),
    [editing, setEditing] = useState<number | null>(null),
    [draft, setDraft] = useState(''),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('');
  const life = useRef(new AbortController()),
    pending = useRef(false);
  useEffect(() => () => life.current.abort(), []);
  const edited = tag.notes.find((note) => note.id === editing);
  async function act(action: string, values: Record<string, string>) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError('');
    const body = new FormData();
    body.set('action', action);
    body.set('tag_id', String(tag.id));
    Object.entries(values).forEach(([key, value]) => body.set(key, value));
    try {
      const result = await pageRequest<{ redirect: string }>(
        initial.api_url,
        initial.url,
        csrfToken,
        life.current.signal,
        body,
      );
      const page = await pageRequest<Page>(
        initial.api_url,
        result.redirect,
        csrfToken,
        life.current.signal,
      );
      if (!life.current.signal.aborted) {
        updated(page.data as TagsData);
        if (action === 'add_tag_note') setMessage('');
        if (action === 'edit_tag_note') setEditing(null);
      }
    } catch (exception) {
      if (!life.current.signal.aborted) setError(errorMessage(exception));
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  function submit(event: FormEvent) {
    event.preventDefault();
    void act('add_tag_note', { message });
  }
  function stopEdit() {
    if (edited && draft !== edited.message)
      window.showConfirmModal({
        title: 'Niezapisane zmiany',
        message: 'Anulować edycję notatki?',
        confirmText: 'Anuluj edycję',
        cancelText: 'Wróć do edycji',
        onConfirm: () => {
          if (!life.current.signal.aborted) setEditing(null);
        },
      });
    else setEditing(null);
  }
  return (
    <Modal
      title="Notatki tagu"
      className="tasks-project-modal tasks-project-notes-modal"
      onClose={close}
      pending={busy}
      dirty={!!message || !!(edited && draft !== edited.message)}
    >
      <div className="tasks-modal__body tasks-project-modal__body tasks-project-edit-modal__body tasks-issue-modal__body">
        <div className="tasks-project-notes-modal__project">
          <span>Tag</span>
          <strong>{tag.name}</strong>
        </div>
        {error ? (
          <div className="tasks-modal__errors" role="alert">
            {error}
          </div>
        ) : null}
        {canEdit ? (
          <form className="tasks-project-notes-compose" onSubmit={submit}>
            <div className="tasks-form-field">
              <label htmlFor="react-tag-note-message">Nowa notatka</label>
              <textarea
                id="react-tag-note-message"
                className="tasks-project-notes-compose__input"
                rows={3}
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="Dodaj notatkę..."
                required
                disabled={busy}
              />
            </div>
            <div className="tasks-project-notes-compose__footer">
              <button className="tasks-project-note__primary" type="submit" disabled={busy}>
                <Icon name="plus" />
                <span>Dodaj notatkę</span>
              </button>
            </div>
          </form>
        ) : null}
        <div className="tasks-project-notes-list">
          <section className="tasks-project-notes-thread">
            {tag.notes.map((note) => (
              <article
                key={note.id}
                className={`tasks-project-note ${note.editable ? 'tasks-project-note--owned' : ''}`}
              >
                <div className="tasks-project-note__heading">
                  <span className="tasks-project-note__icon" aria-hidden="true">
                    <Icon name="file-text" />
                  </span>
                  <div className="tasks-project-note__meta">
                    <strong>{note.author}</strong>
                    <time dateTime={note.created_at}>{dateLabel(note.created_at, true)}</time>
                    {note.edited_at ? (
                      <span className="tasks-project-note__edited">
                        | Edytowano:{' '}
                        <time dateTime={note.edited_at}>{dateLabel(note.edited_at, true)}</time>
                      </span>
                    ) : null}
                  </div>
                  {note.editable ? (
                    <div className="tasks-project-note__actions">
                      <button
                        type="button"
                        className="tasks-project-note__icon-button"
                        aria-label="Edytuj notatkę"
                        disabled={busy || editing !== null}
                        onClick={() => {
                          setEditing(note.id);
                          setDraft(note.message);
                        }}
                      >
                        <Icon name="pencil" />
                      </button>
                      <button
                        type="button"
                        className="tasks-project-note__icon-button"
                        aria-label="Usuń notatkę"
                        disabled={busy}
                        onClick={() =>
                          window.showConfirmModal({
                            title: 'Usuń notatkę',
                            message: 'Usunąć notatkę?',
                            confirmText: 'Usuń',
                            cancelText: 'Anuluj',
                            confirmClass: 'btn-danger',
                            onConfirm: () => {
                              if (!life.current.signal.aborted)
                                void act('delete_tag_note', { note_id: String(note.id) });
                            },
                          })
                        }
                      >
                        <Icon name="trash-2" />
                      </button>
                    </div>
                  ) : null}
                </div>
                <div className="tasks-project-note__body">
                  {editing === note.id ? (
                    <form
                      className="tasks-project-note__edit-form"
                      onSubmit={(event) => {
                        event.preventDefault();
                        void act('edit_tag_note', { note_id: String(note.id), message: draft });
                      }}
                    >
                      <label className="u-sr-only" htmlFor={`tag-note-edit-${note.id}`}>
                        Treść notatki
                      </label>
                      <textarea
                        id={`tag-note-edit-${note.id}`}
                        className="tasks-project-note__edit-input"
                        rows={3}
                        value={draft}
                        onChange={(event) => setDraft(event.target.value)}
                        required
                        disabled={busy}
                      />
                      <div className="tasks-project-note__edit-actions">
                        <button
                          type="button"
                          className="tasks-project-note__secondary"
                          disabled={busy}
                          onClick={stopEdit}
                        >
                          Anuluj
                        </button>
                        <button
                          className="tasks-project-note__primary"
                          type="submit"
                          disabled={busy}
                        >
                          Zapisz zmiany
                        </button>
                      </div>
                    </form>
                  ) : (
                    <div className="tasks-project-note__message">{note.message}</div>
                  )}
                </div>
              </article>
            ))}
            {!tag.notes.length ? (
              <div className="tasks-project-notes-empty" role="status">
                <Icon name="file-text" />
                <p>Brak notatek.</p>
              </div>
            ) : null}
          </section>
        </div>
      </div>
      <footer className="tasks-modal__footer">
        <button
          className="btn btn-secondary"
          disabled={busy}
          onClick={() => {
            const modal = document.querySelector<HTMLElement>('.tasks-project-notes-modal.is-open');
            if (modal) window.AncoreTaskModals?.close(modal);
          }}
        >
          Zamknij
        </button>
      </footer>
    </Modal>
  );
}
