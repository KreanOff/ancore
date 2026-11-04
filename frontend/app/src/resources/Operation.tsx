import { useEffect, useId, useRef, useState, type FormEvent } from 'react';
import { ApiError, errorMessage, request } from '../shared/api';
import { Modal } from '../shared/Modal';
import { Select } from '../shared/Select';
import type { Editor, Errors, Resource, ResourceAction } from './types';

const labels: Record<ResourceAction, string> = {
  handover: 'Przekaż zasoby',
  return: 'Przyjmij zwrot',
  status: 'Zmień status',
  location: 'Zmień lokalizację',
  note: 'Dodaj notatkę',
};
export function ResourceOperation({
  action,
  resources,
  schema,
  apiUrl,
  csrfToken,
  onClose,
  onSaved,
  onRefresh,
}: {
  action: ResourceAction;
  resources: Resource[];
  schema: Editor;
  apiUrl: string;
  csrfToken: string;
  onClose: () => void;
  onSaved: () => void;
  onRefresh: () => void;
}) {
  const [assignedTo, setAssignedTo] = useState('');
  const [status, setStatus] = useState('');
  const [location, setLocation] = useState('');
  const [due, setDue] = useState('');
  const [note, setNote] = useState('');
  const [error, setError] = useState('');
  const [errors, setErrors] = useState<Errors>({});
  const [pending, setPending] = useState(false);
  const [conflict, setConflict] = useState(false);
  const lock = useRef(false);
  const life = useRef(new AbortController());
  const errorRef = useRef<HTMLDivElement>(null);
  const fieldId = useId();
  useEffect(() => () => life.current.abort(), []);
  useEffect(() => {
    if (error) errorRef.current?.focus();
  }, [error, errors]);
  const options = (name: string): [string, string][] =>
    (schema.fields.find((field) => field.name === name)?.choices || []).map((choice) => [
      choice.value,
      choice.label,
    ]);
  async function save(event: FormEvent) {
    event.preventDefault();
    if (lock.current || conflict) return;
    lock.current = true;
    setPending(true);
    setError('');
    setErrors({});
    try {
      await request(apiUrl + 'operate/', csrfToken, life.current.signal, {
        method: 'POST',
        body: JSON.stringify({
          action,
          ids: resources.map((resource) => resource.id).join(','),
          revisions: JSON.stringify(
            Object.fromEntries(resources.map((resource) => [resource.id, resource.updated_at])),
          ),
          assigned_to: assignedTo,
          status,
          location,
          return_due_on: due,
          note,
        }),
      });
      if (!life.current.signal.aborted) onSaved();
    } catch (exception) {
      if (life.current.signal.aborted) return;
      setError(errorMessage(exception));
      if (exception instanceof ApiError) {
        setErrors((exception.data.errors || {}) as Errors);
        setConflict(exception.status === 409 || exception.status === 404);
      }
    } finally {
      lock.current = false;
      setPending(false);
    }
  }
  return (
    <Modal
      title={action === 'handover' && resources.length === 1 ? 'Przekaż zasób' : labels[action]}
      className="resources-operation app-modal-panel--compact"
      onClose={onClose}
      pending={pending}
      dirty={!!(assignedTo || status || location || due || note)}
    >
      <form onSubmit={save} className="tasks-modal__form">
        <div className="tasks-modal__body resources-operation-body">
          <p>
            {resources.length === 1 ? resources[0].name : `Wybrane zasoby: ${resources.length}`}
          </p>
          {error ? (
            <div ref={errorRef} tabIndex={-1} className="tasks-modal__errors" role="alert">
              {error}
              {Object.entries(errors).map(([name, items]) => (
                <p key={name}>{items.map((item) => item.message).join(' ')}</p>
              ))}
              {conflict ? (
                <button type="button" className="btn btn-secondary" onClick={onRefresh}>
                  Odrzuć szkic i odśwież
                </button>
              ) : null}
            </div>
          ) : null}
          <fieldset disabled={pending || conflict} className="resources-operation-fields">
            {action === 'handover' ? (
              <>
                <Select
                  label="Osoba odpowiedzialna"
                  value={assignedTo}
                  options={options('assigned_to').map(([value, label]) => [
                    value,
                    value ? label : 'Wybierz osobę',
                  ])}
                  onChange={setAssignedTo}
                />
                <div className="documents-field">
                  <label htmlFor={`${fieldId}-due`}>Planowany zwrot (opcjonalnie)</label>
                  <input
                    id={`${fieldId}-due`}
                    className="form-input"
                    type="date"
                    value={due}
                    onChange={(event) => setDue(event.target.value)}
                  />
                </div>
                <p className="resources-detail-caption">
                  Zasoby otrzymają status „W użyciu”. Przekazanie i termin zostaną zapisane w
                  historii.
                </p>
              </>
            ) : null}
            {action === 'return' ? (
              <p>
                Zasoby otrzymają status „Dostępny”. Osoba odpowiedzialna i termin zwrotu zostaną
                wyczyszczone.
              </p>
            ) : null}
            {action === 'status' ? (
              <>
                <Select
                  label="Nowy status"
                  value={status}
                  options={[['', 'Wybierz status'], ...options('status')]}
                  onChange={setStatus}
                />
                <p className="resources-detail-caption">
                  Osoba odpowiedzialna pozostanie bez zmian. Status inny niż „W użyciu” usunie
                  termin zwrotu.
                </p>
              </>
            ) : null}
            {action === 'location' ? (
              <div className="documents-field">
                <label htmlFor={`${fieldId}-location`}>Nowa lokalizacja</label>
                <input
                  id={`${fieldId}-location`}
                  aria-describedby={`${fieldId}-location-help`}
                  className="form-input"
                  maxLength={200}
                  value={location}
                  onChange={(event) => setLocation(event.target.value)}
                  placeholder="np. Biuro, piętro 2"
                />
                <span id={`${fieldId}-location-help`} className="resources-detail-caption">
                  Puste pole wyczyści lokalizację wybranych zasobów.
                </span>
              </div>
            ) : null}
            <div className="documents-field">
              <label htmlFor={`${fieldId}-note`}>
                {action === 'note' ? 'Notatka' : 'Notatka do historii (opcjonalnie)'}
              </label>
              <textarea
                id={`${fieldId}-note`}
                className="form-input"
                rows={3}
                required={action === 'note'}
                maxLength={2000}
                value={note}
                onChange={(event) => setNote(event.target.value)}
              />
            </div>
          </fieldset>
        </div>
        <footer className="tasks-modal__footer">
          <button
            type="button"
            className="btn btn-secondary"
            disabled={pending}
            onClick={() => {
              // Use the shared close path so entered notes retain the dirty guard.
              const modal = document.querySelector<HTMLElement>('.resources-operation');
              if (modal) window.AncoreTaskModals?.close(modal);
            }}
          >
            Anuluj
          </button>
          <button type="submit" className="tasks-modal__submit" disabled={pending || conflict}>
            {pending ? 'Zapisywanie…' : 'Zastosuj'}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
