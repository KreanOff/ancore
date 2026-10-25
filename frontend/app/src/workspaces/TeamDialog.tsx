import { useEffect, useMemo, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { Modal } from '../shared/Modal';
import { Icon } from '../shared/Icon';
import { FieldControl, type FormSchema } from '../forms/FormDialog';
import { pageRequest, PageError, type Page } from '../shared/page';
import { errorMessage } from '../shared/api';
import { CrumbHeader, SettingsFields, ErrorList, fieldValue } from './WorkspaceForm';
import TeamTable from './TeamTable';
import Picker from './Picker';
import type { DirectoryData, Team, Tab, Person } from './types';
export default function TeamDialog({
  team,
  initialTab,
  inviteOpen,
  api,
  token,
  onClose,
  onSaved,
  reload,
}: {
  team: Team;
  initialTab: Tab;
  inviteOpen: boolean;
  api: string;
  token: string;
  onClose: () => void;
  onSaved: (url: string) => unknown;
  reload: (url: string) => Promise<void>;
}) {
  const [tab, setTab] = useState<Tab>(initialTab),
    [schema, setSchema] = useState(team.form),
    [name, setName] = useState(team.form ? fieldValue(team.form, 'name') : team.name),
    [description, setDescription] = useState(
      team.form ? fieldValue(team.form, 'description') : team.description,
    ),
    [dirty, setDirty] = useState(!!team.form?.bound),
    [pending, setPending] = useState(false),
    [error, setError] = useState(''),
    [child, setChild] = useState<'invite' | Person | null>(inviteOpen ? 'invite' : null);
  const life = useRef(new AbortController()),
    sending = useRef(false),
    tabs = useRef<HTMLDivElement>(null);
  useEffect(() => () => life.current.abort(), []);
  async function act(url: string, values: Record<string, string>) {
    if (sending.current) return;
    sending.current = true;
    setPending(true);
    setError('');
    try {
      const body = new FormData();
      Object.entries(values).forEach(([key, value]) => body.set(key, value));
      const result = await pageRequest<{ redirect: string }>(
        api,
        url,
        token,
        life.current.signal,
        body,
      );
      if (!life.current.signal.aborted) await reload(result.redirect);
    } catch (e) {
      if (!life.current.signal.aborted) setError(errorMessage(e));
    } finally {
      sending.current = false;
      setPending(false);
    }
  }
  function remove(person: Person) {
    window.showConfirmModal({
      title: 'Odebrać dostęp do Workspace?',
      message:
        'Dane zespołu pozostaną bez zmian. Otwarte edytory Office zostaną zamknięte — pozostali członkowie muszą ponownie otworzyć pliki.',
      confirmText: 'Odbierz dostęp',
      cancelText: 'Anuluj',
      onConfirm: () => void act(person.change_url!, { action: 'remove' }),
    });
  }
  const available: Tab[] = team.can_manage
    ? ['main', 'members', 'invitations']
    : ['main', 'members'];
  return (
    <>
      <Modal
        title={team.can_manage ? 'Edytuj miejsce pracy' : 'Miejsce pracy'}
        className="tasks-project-modal tasks-project-edit-modal tasks-issue-modal workplace-edit-modal"
        dialogClassName="tasks-project-modal__dialog tasks-project-edit-modal__dialog tasks-issue-modal__dialog workplace-edit-modal__dialog"
        header={(close) => (
          <CrumbHeader
            title={team.can_manage ? 'Edytuj miejsce pracy' : 'Miejsce pracy'}
            close={close}
          />
        )}
        dirty={dirty}
        pending={pending || !!child}
        onClose={onClose}
      >
        <div className="tasks-modal__form tasks-project-modal__form tasks-project-edit-modal__form tasks-issue-modal__form workplace-edit-modal__form">
          <div className="tasks-modal__body tasks-project-modal__body tasks-project-edit-modal__body tasks-issue-modal__body workplace-edit-modal__body">
            <div className="tasks-issue-tabbar workplace-edit-modal__tabbar">
              <div
                ref={tabs}
                className="notifications-tabs tasks-issue-tabs"
                role="tablist"
                aria-label="Miejsce pracy"
              >
                {available.map((key) => (
                  <button
                    key={key}
                    id={'workspace-tab-' + key}
                    type="button"
                    role="tab"
                    aria-controls={'workspace-panel-' + key}
                    aria-selected={tab === key}
                    tabIndex={tab === key ? 0 : -1}
                    onClick={() => setTab(key)}
                    onKeyDown={(e) => {
                      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) return;
                      e.preventDefault();
                      const i = available.indexOf(key),
                        next =
                          e.key === 'Home'
                            ? 0
                            : e.key === 'End'
                              ? available.length - 1
                              : (i + (e.key === 'ArrowRight' ? 1 : -1) + available.length) %
                                available.length;
                      setTab(available[next]);
                      tabs.current
                        ?.querySelector<HTMLButtonElement>('#workspace-tab-' + available[next])
                        ?.focus();
                    }}
                  >
                    {key === 'main'
                      ? 'Główna'
                      : key === 'members'
                        ? 'Członkowie'
                        : 'Wysłane zaproszenia'}
                  </button>
                ))}
              </div>
            </div>
            <ErrorList schema={schema} message={error} />
            <section
              role="tabpanel"
              id="workspace-panel-main"
              aria-labelledby="workspace-tab-main"
              hidden={tab !== 'main'}
              data-workplace-tab-panel="main"
            >
              <form
                id="workspace-edit-form"
                onInput={() => setDirty(true)}
                onChange={() => setDirty(true)}
                onSubmit={async (e) => {
                  e.preventDefault();
                  if (sending.current || !team.can_manage) return;
                  const body = new FormData(e.currentTarget);
                  body.set('view', 'workspaces');
                  sending.current = true;
                  setPending(true);
                  setError('');
                  try {
                    const result = await pageRequest<{ redirect: string }>(
                      api,
                      team.update_url,
                      token,
                      life.current.signal,
                      body,
                    );
                    if (life.current.signal.aborted) return;
                    flushSync(() => {
                      setPending(false);
                      setDirty(false);
                    });
                    await onSaved(result.redirect);
                  } catch (e) {
                    if (!life.current.signal.aborted) {
                      if (e instanceof PageError) {
                        const corrected = ((e.data as unknown as Page).data as DirectoryData)?.team
                          ?.form;
                        if (corrected) setSchema(corrected);
                      }
                      setError(errorMessage(e));
                    }
                  } finally {
                    sending.current = false;
                    setPending(false);
                  }
                }}
              >
                <fieldset className="resources-react-fieldset" disabled={pending}>
                  <SettingsFields
                    schema={schema}
                    id="workspace-edit-form"
                    name={name}
                    description={description}
                    setName={setName}
                    setDescription={setDescription}
                    code={team.code}
                    readonly={!team.can_manage}
                  />
                </fieldset>
              </form>
            </section>
            {(['members', 'invitations'] as const)
              .filter((key) => key !== 'invitations' || team.can_manage)
              .map((key) => (
                <section
                  key={key}
                  id={'workspace-panel-' + key}
                  role="tabpanel"
                  aria-labelledby={'workspace-tab-' + key}
                  data-workplace-tab-panel={key}
                  hidden={tab !== key}
                >
                  <div className="workplace-edit-modal__team-toolbar">
                    <span className="workplaces-management__count">
                      {team.name} · {key === 'members' ? 'Członkowie' : 'Wysłane zaproszenia'}:{' '}
                      {key === 'members' ? team.members.length : team.invitations.length}
                    </span>
                    {team.can_manage ? (
                      <button
                        type="button"
                        className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
                        disabled={pending}
                        onClick={() => setChild('invite')}
                      >
                        <Icon name="plus" />
                        <span>Zaproś osobę</span>
                      </button>
                    ) : null}
                  </div>
                  <TeamTable
                    rows={key === 'members' ? team.members : team.invitations}
                    invitations={key === 'invitations'}
                    busy={pending}
                    onRole={setChild}
                    onAction={
                      key === 'members' ? remove : (person) => void act(person.cancel_url!, {})
                    }
                  />
                  {key === 'invitations' && team.can_manage ? (
                    <section className="workplace-invite-links" aria-label="Linki zaproszeń">
                      <h3>Zaproszenia e-mail</h3>
                      {team.invitations.map((invitation) => (
                        <div key={invitation.id} className="workplace-invite-link">
                          <span>
                            {invitation.email} ·{' '}
                            {invitation.email_sent ? 'E-mail wysłany' : 'E-mail niewysłany'}
                          </span>
                          <input
                            className="form-input"
                            aria-label={'Link zaproszenia dla ' + invitation.email}
                            value={invitation.share_url || ''}
                            readOnly
                          />
                          <button
                            type="button"
                            className="btn btn-secondary"
                            disabled={pending}
                            onClick={() => {
                              navigator.clipboard
                                .writeText(invitation.share_url || '')
                                .catch(() =>
                                  setError(
                                    'Nie udało się skopiować linku. Zaznacz i skopiuj adres z pola.',
                                  ),
                                );
                            }}
                          >
                            Kopiuj link
                          </button>
                          {invitation.resend_url ? (
                            <button
                              type="button"
                              className="btn btn-secondary"
                              disabled={pending}
                              onClick={() => void act(invitation.resend_url!, {})}
                            >
                              Wyślij ponownie
                            </button>
                          ) : null}
                        </div>
                      ))}
                      <h3>Linki do dołączenia</h3>
                      {team.invite_links?.map((link) => (
                        <div key={link.id} className="workplace-invite-link">
                          <span>
                            {link.role} · {link.uses}/{link.limit} użyć · ważny do {link.date}
                            {link.domain ? ' · @' + link.domain : ''}
                          </span>
                          <input
                            className="form-input"
                            aria-label={'Link do Workspace ' + team.name}
                            value={link.url}
                            readOnly
                          />
                          <button
                            type="button"
                            className="btn btn-secondary"
                            disabled={pending}
                            onClick={() => {
                              navigator.clipboard
                                .writeText(link.url)
                                .catch(() =>
                                  setError(
                                    'Nie udało się skopiować linku. Zaznacz i skopiuj adres z pola.',
                                  ),
                                );
                            }}
                          >
                            Kopiuj link
                          </button>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            disabled={pending}
                            onClick={() => void act(link.revoke_url, {})}
                          >
                            Unieważnij link
                          </button>
                        </div>
                      ))}
                      {team.link_form ? (
                        <details>
                          <summary>Utwórz link zaproszenia</summary>
                          <form
                            className="workplace-invite-link-form"
                            onSubmit={(event) => {
                              event.preventDefault();
                              void act(
                                team.link_create_url!,
                                Object.fromEntries(new FormData(event.currentTarget)) as Record<
                                  string,
                                  string
                                >,
                              );
                            }}
                          >
                            <fieldset className="resources-react-fieldset" disabled={pending}>
                              {team.link_form.fields.map((field) => (
                                <FieldControl key={field.name} field={field} />
                              ))}
                            </fieldset>
                            <button className="btn btn-primary" type="submit" disabled={pending}>
                              Utwórz link
                            </button>
                          </form>
                        </details>
                      ) : null}
                    </section>
                  ) : null}
                </section>
              ))}
          </div>
          <footer className="tasks-modal__footer tasks-project-edit-modal__footer tasks-issue-modal__footer workplace-edit-modal__footer">
            <button
              type="button"
              className="btn btn-secondary"
              disabled={pending}
              onClick={(e) =>
                window.AncoreTaskModals?.close(
                  e.currentTarget.closest('.tasks-modal') as HTMLElement,
                )
              }
            >
              Zamknij
            </button>
            {team.can_manage && tab === 'main' ? (
              <button
                type="submit"
                form="workspace-edit-form"
                className="tasks-modal__submit"
                disabled={pending}
              >
                Zapisz zmiany
              </button>
            ) : null}
          </footer>
        </div>
      </Modal>
      {child ? (
        <TeamAction
          key={typeof child === 'string' ? 'invite' : child.id}
          team={team}
          person={typeof child === 'string' ? undefined : child}
          api={api}
          token={token}
          onClose={() => setChild(null)}
          onSaved={async (url) => {
            await reload(url);
            setChild(null);
            setTab(typeof child === 'string' ? 'invitations' : 'members');
          }}
        />
      ) : null}
    </>
  );
}
function TeamAction({
  team,
  person,
  api,
  token,
  onClose,
  onSaved,
}: {
  team: Team;
  person?: Person;
  api: string;
  token: string;
  onClose: () => void;
  onSaved: (url: string) => Promise<void>;
}) {
  const [schema, setSchema] = useState<FormSchema>(team.invite_form!),
    [email, setEmail] = useState(
      String(team.invite_form?.fields.find((field) => field.name === 'email')?.value || ''),
    ),
    [pending, setPending] = useState(false),
    [dirty, setDirty] = useState(false),
    [error, setError] = useState('');
  const life = useRef(new AbortController()),
    sending = useRef(false);
  useEffect(() => () => life.current.abort(), []);
  const role = schema.fields.find((field) => field.name === 'role')!;
  const roleField = useMemo(
    () => ({ ...role, id: 'workspace-person-role', value: person?.role || 'member' }),
    [role, person?.role],
  );
  return (
    <Modal
      title={person ? 'Zmień rolę' : 'Zaproś osobę · ' + team.name}
      className="app-modal-panel--compact"
      dirty={dirty}
      pending={pending}
      onClose={onClose}
    >
      <form
        className="tasks-modal__form"
        onChange={() => setDirty(true)}
        onSubmit={async (e) => {
          e.preventDefault();
          if (sending.current) return;
          sending.current = true;
          const body = new FormData(e.currentTarget);
          if (person) body.set('action', 'role');
          setPending(true);
          setError('');
          try {
            const result = await pageRequest<{ redirect: string }>(
              api,
              person?.change_url || team.invite_url,
              token,
              life.current.signal,
              body,
            );
            if (life.current.signal.aborted) return;
            flushSync(() => {
              setPending(false);
              setDirty(false);
            });
            await onSaved(result.redirect);
          } catch (e) {
            if (!life.current.signal.aborted) {
              if (e instanceof PageError) {
                const corrected = ((e.data as unknown as Page).data as DirectoryData)?.team
                  ?.invite_form;
                if (corrected) setSchema(corrected);
              }
              setError(errorMessage(e));
            }
          } finally {
            sending.current = false;
            setPending(false);
          }
        }}
      >
        <div className="tasks-modal__body">
          {error ? (
            <div className="tasks-modal__errors" role="alert">
              {error}
            </div>
          ) : null}
          {schema.errors.map((text, index) => (
            <p key={index} role="alert">
              {text}
            </p>
          ))}
          {person ? (
            <>
              <p className="workplace-team__hint">{person.name}</p>
              <fieldset className="resources-react-fieldset" disabled={pending}>
                <FieldControl field={roleField} />
              </fieldset>
            </>
          ) : (
            <>
              <p className="workplace-team__hint">
                Zaproszenie jest ważne przez 7 dni. Osoba otrzyma link e-mailem, a po zalogowaniu
                zobaczy je również w powiadomieniach. Gość ma dostęp tylko do odczytu.
              </p>
              <fieldset className="resources-react-fieldset" disabled={pending}>
                <div className="workplace-invite__fields">
                  <div className="tasks-form-field">
                    <label>Osoba lub adres e-mail</label>
                    <Picker
                      api={api}
                      url={team.candidates_url}
                      token={token}
                      value={email}
                      onChange={(value) => {
                        setEmail(value);
                        setDirty(true);
                      }}
                    />
                    {schema.fields
                      .find((f) => f.name === 'email')
                      ?.errors.map((message, index) => (
                        <p className="tasks-modal__errors" role="alert" key={index}>
                          {message}
                        </p>
                      ))}
                  </div>
                  <FieldControl field={role} />
                </div>
              </fieldset>
            </>
          )}
        </div>
        <footer className="tasks-modal__footer">
          <button
            type="button"
            className="btn btn-secondary"
            disabled={pending}
            onClick={(e) =>
              window.AncoreTaskModals?.close(e.currentTarget.closest('.tasks-modal') as HTMLElement)
            }
          >
            Anuluj
          </button>
          <button type="submit" className="tasks-modal__submit" disabled={pending}>
            {pending ? 'Zapisywanie…' : person ? 'Zapisz rolę' : 'Zaproś do Workspace'}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
