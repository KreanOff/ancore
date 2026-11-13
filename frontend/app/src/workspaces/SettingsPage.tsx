import { Toolbar } from '../shared/DirectoryToolbar';
import { useEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { Modal } from '../shared/Modal';
import { PageHeader } from '../shared/PageHeader';
import { useDirtyGuard } from '../shared/useDirtyGuard';
import { Icon } from '../shared/Icon';
import { FieldControl, type FormSchema } from '../forms/FormDialog';
import { pageRequest, PageError, type Page } from '../shared/page';
import { errorMessage } from '../shared/api';
import { SettingsFields, ErrorList, fieldValue } from './WorkspaceForm';
import TeamTable from './TeamTable';
import Picker from './Picker';
import type { DirectoryData, Team, Tab } from './types';
export default function SettingsPage({
  team,
  initialTab,
  backUrl,
  addOpen,
  api,
  token,
  onClose,
  onSaved,
  reload,
}: {
  team: Team;
  initialTab: Tab;
  backUrl: string;
  addOpen: boolean;
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
    [notice, setNotice] = useState(''),
    [child, setChild] = useState<'add' | null>(addOpen ? 'add' : null);
  const life = useRef(new AbortController()),
    sending = useRef(false),
    mainForm = useRef<HTMLFormElement>(null),
    errorBox = useRef<HTMLDivElement>(null),
    addButton = useRef<HTMLButtonElement>(null);
  useEffect(() => () => life.current.abort(), []);
  useEffect(() => {
    const form = mainForm.current!;
    // The shared avatar picker commits its selection with a native form change event.
    const changed = (event: Event) => {
      if (event.target === form) setDirty(true);
    };
    form.addEventListener('change', changed);
    return () => {
      form.removeEventListener('change', changed);
    };
  }, []);
  useDirtyGuard(dirty, pending || !!child);
  useEffect(() => {
    if (!error) return;
    const field = mainForm.current?.querySelector<HTMLElement>('[aria-invalid="true"]');
    if (field && tab === 'main') field.focus();
    else errorBox.current?.focus();
  }, [error, schema, tab]);
  async function act(url: string, values: Record<string, string>) {
    if (sending.current) return;
    sending.current = true;
    setPending(true);
    setError('');
    setNotice('');
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

  return (
    <>
      <div
        className="tasks-page work-page space-settings-page workspace-settings-page"
        data-react-screen="workspace-settings"
        aria-busy={pending}
      >
        <PageHeader
          heading={
            <>
              <a
                href={backUrl}
                className="tasks-issue-close"
                aria-label="Wróć do Workspace"
                title="Wróć do Workspace"
              >
                <Icon name="arrow-left" />
              </a>
              <h1 className="tasks-topbar-title">Ustawienia Workspace · {team.name}</h1>
            </>
          }
        />
        {error || schema?.errors.length || schema?.fields.some((field) => field.errors.length) ? (
          <div className="space-settings-message" ref={errorBox} tabIndex={-1}>
            <ErrorList schema={schema} message={error} />
          </div>
        ) : null}
        {notice ? (
          <p className="space-settings-message" role="status">
            {notice}
          </p>
        ) : null}

        <section
          id="workspace-panel-main"
          aria-label="Ustawienia Workspace"
          className="space-settings-panel"
          hidden={tab !== 'main'}
          data-workplace-tab-panel="main"
        >
          <form
            id="workspace-edit-form"
            className="tasks-modal__form"
            ref={mainForm}
            onInput={() => setDirty(true)}
            onChange={() => setDirty(true)}
            onSubmit={async (e) => {
              e.preventDefault();
              if (sending.current || !team.can_manage) return;
              const body = new FormData(e.currentTarget);
              body.set('view', 'workspaces');
              body.set('tab', 'main');
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
            <Toolbar
              className="app-toolbar--embedded member-access-toolbar"
              actions={
                <>
                  {team.can_manage ? (
                    <button
                      type="submit"
                      className="tasks-filter-button"
                      disabled={pending || !dirty}
                    >
                      <Icon name="check" />
                      {pending ? 'Zapisywanie…' : 'Zapisz'}
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className="tasks-filter-button"
                    disabled={pending}
                    onClick={onClose}
                  >
                    {team.can_manage ? 'Anuluj' : 'Wróć'}
                  </button>
                </>
              }
            />
            <div className="tasks-modal__body space-settings-main workspace-settings-main">
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
            </div>
          </form>
        </section>
        <section
          id="workspace-panel-members"
          aria-label="Członkowie"
          className="space-settings-panel space-settings-table-body"
          hidden={tab !== 'members'}
        >
          <Toolbar
            className="workplace-edit-modal__team-toolbar"
            filters={
              <span className="workplaces-management__count">
                {team.name} · Członkowie: {team.members.length}
              </span>
            }
            actions={
              team.can_manage ? (
                <button
                  type="button"
                  className="tasks-filter-button"
                  disabled={pending}
                  ref={addButton}
                  onClick={() => setChild('add')}
                >
                  <Icon name="plus" />
                  <span>Dodaj osobę</span>
                </button>
              ) : null
            }
          />
          <TeamTable rows={team.members} />
        </section>
        {team.can_manage ? (
          <section
            id="workspace-panel-links"
            aria-label="Linki do dołączenia"
            className="space-settings-panel"
            hidden={tab !== 'links'}
          >
            <div className="tasks-modal__body">
              <section className="workplace-invite-links" aria-label="Linki do dołączenia">
                <h3>Linki do dołączenia</h3>
                {!team.invite_links?.length ? (
                  <p className="workplace-team__hint">Brak aktywnych linków do dołączenia.</p>
                ) : null}
                {team.invite_links?.map((link) => (
                  <div key={link.id} className="workplace-invite-link">
                    <span>
                      {link.role} · {link.uses}/{link.limit} użyć · ważny do {link.date}
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
                      onClick={(event) => {
                        const input = event.currentTarget
                          .closest('.workplace-invite-link')
                          ?.querySelector<HTMLInputElement>('input');
                        const selectLink = () => {
                          input?.focus();
                          input?.select();
                          setNotice(
                            'Automatyczne kopiowanie jest niedostępne. Skopiuj zaznaczony adres z pola.',
                          );
                        };
                        if (!navigator.clipboard?.writeText) {
                          selectLink();
                          return;
                        }
                        void navigator.clipboard.writeText(link.url).catch(selectLink);
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
                    <summary>Utwórz link do dołączenia</summary>
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
            </div>
          </section>
        ) : null}
      </div>
      {child ? (
        <TeamAction
          team={team}
          returnFocus={addButton.current}
          api={api}
          token={token}
          onClose={() => setChild(null)}
          onSaved={async (url) => {
            await reload(url);
            setChild(null);
            setTab('members');
          }}
        />
      ) : null}
    </>
  );
}
function TeamAction({
  team,
  returnFocus,
  api,
  token,
  onClose,
  onSaved,
}: {
  team: Team;
  returnFocus: HTMLElement | null;
  api: string;
  token: string;
  onClose: () => void;
  onSaved: (url: string) => Promise<void>;
}) {
  const [schema, setSchema] = useState<FormSchema>(team.add_form!),
    [query, setQuery] = useState(''),
    [userId, setUserId] = useState(''),
    [pending, setPending] = useState(false),
    [dirty, setDirty] = useState(false),
    [error, setError] = useState('');
  const life = useRef(new AbortController()),
    sending = useRef(false);
  useEffect(() => () => life.current.abort(), []);
  const role = schema.fields.find((field) => field.name === 'role')!;

  return (
    <Modal
      title={'Dodaj osobę · ' + team.name}
      returnFocus={returnFocus}
      size="compact"
      dirty={dirty}
      pending={pending}
      onClose={onClose}
    >
      <form
        className="tasks-modal__form"
        onChange={() => setDirty(true)}
        onSubmit={async (e) => {
          e.preventDefault();
          if (sending.current || !userId) return;
          sending.current = true;
          const body = new FormData(e.currentTarget);
          setPending(true);
          setError('');
          try {
            const result = await pageRequest<{ redirect: string }>(
              api,
              team.add_url,
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
                  ?.add_form;
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

          <>
            <p className="workplace-team__hint">
              Wybierz istniejące konto Ancore. Osoba od razu uzyska dostęp do Workspace. Gość ma
              dostęp tylko do odczytu.
            </p>
            <fieldset className="resources-react-fieldset" disabled={pending}>
              <div className="workplace-invite__fields">
                <div className="tasks-form-field">
                  <label>Istniejące konto Ancore</label>
                  <input type="hidden" name="user_id" value={userId} />
                  <Picker
                    api={api}
                    url={team.candidates_url}
                    token={token}
                    value={query}
                    existingOnly
                    onSelect={(person) => setUserId(String(person.id || ''))}
                    onChange={(value) => {
                      setQuery(value);
                      setUserId('');
                      setDirty(true);
                    }}
                  />
                  {schema.fields
                    .find((f) => f.name === 'user_id')
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
          <button type="submit" className="tasks-modal__submit" disabled={pending || !userId}>
            {pending ? 'Zapisywanie…' : 'Dodaj do Workspace'}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
