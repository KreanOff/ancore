import { useEffect, useRef, useState } from 'react';
import { FormFields, type FormSchema } from '../forms/FormDialog';
import Picker, { PersonIdentity } from '../workspaces/Picker';
import type { MemberRow } from './Members';
import { Modal } from './Modal';
import { PageError, pageRequest } from './page';
import { errorMessage } from './api';

export default function SharingDialog<T>({
  name,
  schema,
  person,
  api,
  url,
  csrfToken,
  onClose,
  onSaved,
  hostId,
}: {
  name: string;
  schema: FormSchema;
  person?: MemberRow;
  api: string;
  url: string;
  csrfToken: string;
  onClose: () => void;
  onSaved: (result: T) => void;
  hostId?: string;
}) {
  const [email, setEmail] = useState('');
  const [dirty, setDirty] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [life] = useState(() => new AbortController());
  const sending = useRef(false);
  useEffect(() => () => life.abort(), [life]);
  const [roles] = useState<FormSchema>(() => ({
    ...schema,
    fields: schema.fields
      .filter((field) => field.name === 'role')
      .map((field) => ({
        ...field,
        value:
          person?.role || (Array.isArray(field.value) ? field.value[0] : field.value) || 'member',
      })),
  }));
  return (
    <Modal
      title={person ? 'Zmień rolę' : 'Udostępnij · ' + name}
      className="app-modal-panel--compact"
      hostId={hostId}
      dirty={dirty}
      pending={pending}
      onClose={onClose}
    >
      <form
        className="tasks-modal__form"
        onChange={() => setDirty(true)}
        onSubmit={async (event) => {
          event.preventDefault();
          if (sending.current) return;
          const body = new FormData(event.currentTarget);
          body.set('action', person ? 'role' : 'share');
          if (person) body.set('member_id', String(person.id));
          sending.current = true;
          setPending(true);
          setError('');
          try {
            const result = await pageRequest<T>(api, url, csrfToken, life.signal, body);
            if (!life.signal.aborted) onSaved(result);
          } catch (exception) {
            if (!life.signal.aborted) {
              const errors = exception instanceof PageError ? exception.data.errors : undefined;
              setError(
                errors
                  ? Object.values(errors as Record<string, { message: string }[]>)
                      .flatMap((rows) => rows.map((row) => row.message))
                      .join(' ')
                  : errorMessage(exception),
              );
            }
          } finally {
            sending.current = false;
            if (!life.signal.aborted) setPending(false);
          }
        }}
      >
        <div className="tasks-modal__body">
          {error ? (
            <p className="tasks-modal__errors" role="alert">
              {error}
            </p>
          ) : null}
          <p className="workplace-team__hint">
            {person ? (
              <PersonIdentity person={person} />
            ) : (
              'Wybrana osoba od razu uzyska dostęp z wybraną rolą. Wybierz osobę z bieżącego Workspace.'
            )}
          </p>
          <fieldset className="resources-react-fieldset" disabled={pending}>
            <div className={person ? undefined : 'workplace-invite__fields'}>
              {!person ? (
                <div className="tasks-form-field">
                  <span>Osoba lub adres e-mail konta Ancore</span>
                  <Picker
                    api={api}
                    url={url + 'candidates/'}
                    token={csrfToken}
                    value={email}
                    sharing
                    onChange={(value) => {
                      setEmail(value);
                      setDirty(true);
                    }}
                  />
                </div>
              ) : null}
              <FormFields schema={roles} />
            </div>
          </fieldset>
        </div>
        <footer className="tasks-modal__footer">
          <button
            type="button"
            className="btn btn-secondary"
            disabled={pending}
            onClick={(event) => {
              const modal = event.currentTarget.closest<HTMLElement>('.tasks-modal');
              if (modal) window.AncoreTaskModals?.close(modal);
            }}
          >
            Anuluj
          </button>
          <button type="submit" className="tasks-modal__submit" disabled={pending}>
            {pending ? 'Zapisywanie…' : person ? 'Zapisz rolę' : 'Udostępnij'}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
