import { useEffect, useRef, useState } from 'react';
import { FormFields, type FormSchema } from '../forms/FormDialog';
import Picker, { PersonIdentity, type Candidate } from '../workspaces/Picker';
import type { MemberRow } from './Members';
import { Modal } from './Modal';
import { PageError, pageRequest } from './page';
import { errorMessage } from './api';

export type SharingChange =
  | { people: MemberRow[]; role: string }
  | { person: Candidate; role: string };

export default function SharingDialog<T>({
  name,
  schema,
  person,
  people,
  api,
  url,
  csrfToken,
  onClose,
  onSaved,
  onStage,
  candidatesUrl,
  hostId,
  saveOnStage = false,
  stageBlocked = false,
}: {
  name: string;
  schema: FormSchema;
  person?: MemberRow;
  people?: MemberRow[];
  api: string;
  url: string;
  csrfToken: string;
  onClose: () => void;
  onSaved?: (result: T) => void;
  onStage?: (change: SharingChange) => Promise<void> | void;
  candidatesUrl?: string;
  hostId?: string;
  saveOnStage?: boolean;
  stageBlocked?: boolean;
}) {
  const bulk = !!people?.length;
  const roleMembers = bulk ? people : person ? [person] : [];
  const changingRole = roleMembers.length > 0;
  const commonRole = roleMembers.every((member) => member.role === roleMembers[0]?.role)
    ? roleMembers[0]?.role
    : undefined;
  const [email, setEmail] = useState('');
  const [candidate, setCandidate] = useState<Candidate | null>(null);
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
          commonRole || (Array.isArray(field.value) ? field.value[0] : field.value) || 'member',
      })),
  }));
  return (
    <Modal
      title={changingRole ? 'Zmień rolę' : 'Udostępnij · ' + name}
      size="compact"
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
          if (sending.current || stageBlocked) return;
          const body = new FormData(event.currentTarget);
          body.set('action', changingRole ? 'role' : 'share');
          if (bulk) {
            roleMembers.forEach((member) => body.append('member_ids', String(member.id)));
          } else if (person) body.set('member_id', String(person.id));
          sending.current = true;
          setPending(true);
          setError('');
          try {
            if (onStage) {
              const role = String(body.get('role') || '');
              if (changingRole) await onStage({ people: roleMembers, role });
              else {
                if (!candidate?.id || candidate.email !== email)
                  throw new Error('Wybierz osobę z listy kont Workspace.');
                await onStage({ person: candidate, role });
              }
            } else {
              const result = await pageRequest<T>(api, url, csrfToken, life.signal, body);
              if (!life.signal.aborted) onSaved?.(result);
            }
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
          {stageBlocked ? (
            <p className="tasks-modal__errors" role="alert">
              Dostęp zmienił się w innym oknie. Wybierz „Anuluj”, aby wczytać aktualny stan.
            </p>
          ) : null}
          {onStage && !saveOnStage ? (
            <p className="workplace-team__hint">
              Dostęp zmieni się po kliknięciu „Zapisz” w sekcji „Udostępnienia”.
            </p>
          ) : null}
          {changingRole ? (
            <>
              {roleMembers.length > 1 ? (
                <p className="workplace-team__hint">Wybrane osoby: {roleMembers.length}</p>
              ) : null}
              {roleMembers.map((member) => (
                <p className="workplace-team__hint" key={member.id}>
                  <PersonIdentity person={member} />
                </p>
              ))}
            </>
          ) : (
            <p className="workplace-team__hint">
              {onStage && !saveOnStage
                ? 'Wybierz osobę z bieżącego Workspace i jej rolę.'
                : 'Wybrana osoba od razu uzyska dostęp z wybraną rolą. Wybierz osobę z bieżącego Workspace.'}
            </p>
          )}
          <fieldset className="resources-react-fieldset" disabled={pending || stageBlocked}>
            <div className={changingRole ? undefined : 'workplace-invite__fields'}>
              {!changingRole ? (
                <div className="tasks-form-field">
                  <span>Osoba lub adres e-mail konta Ancore</span>
                  <Picker
                    api={api}
                    url={candidatesUrl || url + 'candidates/'}
                    token={csrfToken}
                    value={email}
                    sharing
                    onChange={(value) => {
                      setEmail(value);
                      setCandidate(null);
                      setDirty(true);
                    }}
                    onSelect={onStage ? setCandidate : undefined}
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
          <button type="submit" className="tasks-modal__submit" disabled={pending || stageBlocked}>
            {pending
              ? 'Zapisywanie…'
              : onStage && !saveOnStage
                ? changingRole
                  ? 'Zastosuj'
                  : 'Dodaj'
                : changingRole
                  ? 'Zapisz rolę'
                  : 'Udostępnij'}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
