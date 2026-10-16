import { type FormEvent, useEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { Modal } from '../shared/Modal';
import { Icon } from '../shared/Icon';
import AvatarControl from '../shared/AvatarControl';
import { errorMessage } from '../shared/api';
import { PageError, pageRequest, type Page } from '../shared/page';
import type { ProfileData } from './types';
import PresenceSelect from './PresenceSelect';

export default function ProfileEditor({
  data,
  api,
  token,
  avatar,
  onClose,
}: {
  data: ProfileData;
  api: string;
  token: string;
  avatar: boolean;
  onClose: () => void;
}) {
  const [schema, setSchema] = useState(data.form),
    [error, setError] = useState('');
  const [dirty, setDirty] = useState(data.form.bound),
    [pending, setPending] = useState(false);
  const initialValue = (name: string) =>
    String(data.form.fields.find((field) => field.name === name)?.value || '');
  const [status, setStatus] = useState(initialValue('presence_status'));
  const form = useRef<HTMLFormElement>(null),
    alert = useRef<HTMLDivElement>(null),
    sending = useRef(false);
  const [life] = useState(() => new AbortController());
  useEffect(() => () => life.abort(), [life]);
  useEffect(() => {
    if (avatar)
      form.current?.querySelector<HTMLButtonElement>('[data-workplace-avatar-open]')?.click();
  }, [avatar]);
  const errors = [
    ...(error ? [error] : []),
    ...schema.errors,
    ...schema.fields.flatMap((field) => field.errors.map((text) => field.label + ': ' + text)),
  ];
  useEffect(() => {
    if (error || schema.bound) alert.current?.focus();
  }, [error, schema]);
  const field = (name: string, label: string) => {
    const definition = schema.fields.find((item) => item.name === name)!;
    const attrs = {
      id: definition.id,
      name,
      defaultValue: initialValue(name),
      className: 'form-input profile-field-input',
      required: definition.required,
      disabled: pending,
      placeholder: definition.attrs.placeholder,
      autoComplete: definition.attrs.autocomplete,
      'aria-invalid': definition.errors.length ? (true as const) : undefined,
      'aria-describedby': definition.errors.length ? definition.id + '-errors' : undefined,
    };
    return (
      <div className="profile-stacked-field" key={name}>
        <label className="profile-field-label" htmlFor={definition.id}>
          {label}
        </label>
        {name === 'bio' ? (
          <textarea {...attrs} rows={4} />
        ) : (
          <input
            {...attrs}
            type={definition.type}
            maxLength={definition.attrs.maxlength ? Number(definition.attrs.maxlength) : undefined}
            spellCheck={name === 'username' ? false : undefined}
          />
        )}
        {definition.errors.length ? (
          <ul className="errorlist" id={definition.id + '-errors'}>
            {definition.errors.map((text, i) => (
              <li key={i}>{text}</li>
            ))}
          </ul>
        ) : null}
      </div>
    );
  };
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending.current) return;
    const body = new FormData(event.currentTarget);
    sending.current = true;
    setPending(true);
    setError('');
    try {
      const result = await pageRequest<{ redirect: string }>(
        api,
        data.urls.profile,
        token,
        life.signal,
        body,
      );
      // Refresh the shared shell avatar and identity after saving the profile.
      flushSync(() => {
        setDirty(false);
        setPending(false);
      });
      location.assign(result.redirect);
    } catch (e) {
      if (life.signal.aborted) return;
      if (e instanceof PageError && e.data.type === 'account-profile')
        setSchema(((e.data as unknown as Page).data as ProfileData).form);
      else setError(errorMessage(e));
      sending.current = false;
      setPending(false);
    }
  }
  return (
    <Modal
      title="Edytuj profil"
      className="profile-edit-overlay react-account-editor"
      dialogClassName="profile-edit-dialog"
      dirty={dirty}
      pending={pending}
      onClose={onClose}
      header={(close) => (
        <header className="profile-edit-header">
          <div>
            <h2>Edytuj profil</h2>
            <p>{data.user.name}</p>
          </div>
          <button
            type="button"
            className="profile-edit-close"
            disabled={pending}
            aria-label="Zamknij edycję profilu"
            title="Zamknij"
            onClick={close}
          >
            <Icon name="x" />
          </button>
        </header>
      )}
    >
      <form
        ref={form}
        id="profile-detail-form"
        className="profile-edit-form"
        method="post"
        encType="multipart/form-data"
        noValidate
        onSubmit={submit}
        onInput={() => setDirty(true)}
        onChange={() => setDirty(true)}
        aria-busy={pending}
      >
        <input type="hidden" name="csrfmiddlewaretoken" value={token} />
        <input type="hidden" name="presence_status" value={status} />
        {errors.length ? (
          <div className="tasks-error-banner" role="alert" ref={alert} tabIndex={-1}>
            <strong>Wystąpiły błędy:</strong>
            <ul>
              {errors.map((text, i) => (
                <li key={i}>{text}</li>
              ))}
            </ul>
          </div>
        ) : null}
        <div className="profile-edit-body">
          <AvatarControl schema={data.form} formId="profile-detail-form" account />
          <div className="profile-edit-fields">
            <div className="profile-name-fields">
              {field('first_name', 'Imię')}
              {field('middle_name', 'Drugie imię')}
              {field('last_name', 'Nazwisko')}
            </div>
            {field('email', 'Email')}
            {field('username', 'ID Ancore')}
            <div className="profile-status-field">
              <span>Status</span>
              <PresenceSelect
                value={status}
                choices={
                  schema.fields.find((item) => item.name === 'presence_status')!.choices || []
                }
                disabled={pending}
                onChange={(value) => {
                  setStatus(value);
                  setDirty(true);
                }}
              />
            </div>
            <div className="profile-contact-fields">
              {field('phone_number', 'Numer telefonu')}
              {field('job_title', 'Stanowisko')}
            </div>
            {field('bio', 'Bio')}
          </div>
        </div>
        <footer className="profile-edit-footer">
          <button
            type="button"
            className="tasks-issue-side-button profile-edit-cancel"
            disabled={pending}
            onClick={() => window.AncoreTaskModals?.close(form.current!.closest('.tasks-modal')!)}
          >
            Anuluj
          </button>
          <button type="submit" className="tasks-issue-save" disabled={pending}>
            {pending ? 'Zapisywanie…' : 'Zapisz'}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
