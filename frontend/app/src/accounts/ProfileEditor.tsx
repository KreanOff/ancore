import { type FormEvent, useEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { Modal } from '../shared/Modal';
import { Icon } from '../shared/Icon';
import { FieldLabel } from '../shared/FieldLabel';
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
  focusField,
  onClose,
}: {
  data: ProfileData;
  api: string;
  token: string;
  avatar: boolean;
  focusField?: string;
  onClose: () => void;
}) {
  const [schema, setSchema] = useState(data.form),
    [error, setError] = useState('');
  const [dirty, setDirty] = useState(data.form.bound),
    [pending, setPending] = useState(false);
  const initialValue = (name: string) =>
    String(data.form.fields.find((field) => field.name === name)?.value || '');
  const [status, setStatus] = useState(initialValue('presence_status'));
  const statusField = schema.fields.find((item) => item.name === 'presence_status')!;
  const avatarErrors = schema.fields
    .filter((item) => item.name === 'avatar' || item.name.startsWith('profile_photo'))
    .flatMap((item) => item.errors);
  const avatarDescription = avatarErrors.length ? 'profile-avatar-errors' : undefined;
  const form = useRef<HTMLFormElement>(null),
    alert = useRef<HTMLDivElement>(null),
    sending = useRef(false);
  const [life] = useState(() => new AbortController());
  useEffect(() => () => life.abort(), [life]);
  useEffect(() => {
    // The shared avatar picker is portalled outside this form and announces
    // its changes with a native event on the form, rather than an input.
    const element = form.current;
    const changed = () => setDirty(true);
    element?.addEventListener('change', changed);
    return () => element?.removeEventListener('change', changed);
  }, []);
  useEffect(() => {
    if (avatar)
      form.current?.querySelector<HTMLButtonElement>('[data-workplace-avatar-open]')?.click();
  }, [avatar]);
  useEffect(() => {
    if (!focusField || avatar || data.form.bound) return;
    const frame = requestAnimationFrame(() => {
      const control = form.current?.elements.namedItem(focusField);
      if (control instanceof HTMLElement) control.focus();
    });
    return () => cancelAnimationFrame(frame);
  }, [focusField, avatar, data.form.bound]);
  useEffect(() => {
    // AvatarControl owns these controls; retain its selected image and crop after validation.
    form.current?.querySelectorAll('[data-workplace-avatar-open]').forEach((control) => {
      if (avatarDescription) {
        control.setAttribute('aria-invalid', 'true');
        control.setAttribute('aria-describedby', avatarDescription);
      } else {
        control.removeAttribute('aria-invalid');
        control.removeAttribute('aria-describedby');
      }
    });
  }, [avatarDescription]);
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
      disabled: pending || definition.disabled,
      placeholder: definition.attrs.placeholder,
      autoComplete:
        definition.attrs.autocomplete ||
        (name === 'first_name' ? 'given-name' : name === 'last_name' ? 'family-name' : undefined),
      'aria-invalid': definition.errors.length ? (true as const) : undefined,
      'aria-describedby':
        [
          definition.help_text ? definition.id + '-help' : '',
          definition.errors.length ? definition.id + '-errors' : '',
        ]
          .filter(Boolean)
          .join(' ') || undefined,
    };
    return (
      <div
        className={`profile-stacked-field app-form-field${name === 'bio' ? ' app-form-description' : name === 'middle_name' ? ' app-form-wide' : ''}`}
        key={name}
      >
        <FieldLabel
          htmlFor={definition.id}
          label={label}
          required={definition.required}
          helpText={definition.help_text}
          helpId={definition.id + '-help'}
        />
        {name === 'bio' ? (
          <textarea {...attrs} rows={4} />
        ) : (
          <input
            {...attrs}
            type={name === 'phone_number' ? 'tel' : definition.type}
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
        <fieldset className="resources-react-fieldset" disabled={pending}>
          <div className="profile-edit-body app-form-avatar-layout">
            <div className="profile-edit-avatar" role="group" aria-label="Awatar użytkownika">
              <AvatarControl schema={data.form} formId="profile-detail-form" account />
              {avatarErrors.length ? (
                <ul className="errorlist" id="profile-avatar-errors">
                  {avatarErrors.map((text, i) => (
                    <li key={i}>{text}</li>
                  ))}
                </ul>
              ) : null}
            </div>
            <div className="profile-edit-fields app-form-layout">
              <div className="app-form-heading">
                <div className="profile-name-fields">
                  {field('first_name', 'Imię')}
                  {field('last_name', 'Nazwisko')}
                </div>
              </div>
              {field('middle_name', 'Drugie imię (opcjonalne)')}
              {field('bio', 'O mnie')}
              {field('email', 'E-mail')}
              {field('username', 'ID Ancore')}
              <div className="profile-status-field app-form-field">
                <FieldLabel
                  htmlFor={statusField.id}
                  label="Status"
                  required={statusField.required}
                  helpText={statusField.help_text}
                  helpId={statusField.id + '-help'}
                />
                <PresenceSelect
                  id={statusField.id}
                  value={status}
                  choices={statusField.choices || []}
                  invalid={!!statusField.errors.length}
                  describedBy={
                    [
                      statusField.help_text ? statusField.id + '-help' : '',
                      statusField.errors.length ? statusField.id + '-errors' : '',
                    ]
                      .filter(Boolean)
                      .join(' ') || undefined
                  }
                  disabled={pending}
                  onChange={(value) => {
                    setStatus(value);
                    setDirty(true);
                  }}
                />
                {statusField.errors.length ? (
                  <ul className="errorlist" id={statusField.id + '-errors'}>
                    {statusField.errors.map((text, i) => (
                      <li key={i}>{text}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
              {field('phone_number', 'Numer telefonu')}
              {field('job_title', 'Stanowisko')}
            </div>
          </div>
        </fieldset>
        <footer className="profile-edit-footer">
          <button
            type="button"
            className="tasks-issue-side-button profile-edit-cancel"
            disabled={pending}
            onClick={() => window.AncoreTaskModals?.close(form.current!.closest('.tasks-modal')!)}
          >
            Anuluj
          </button>
          <button type="submit" className="tasks-issue-save" disabled={pending || !dirty}>
            {pending ? 'Zapisywanie…' : 'Zapisz'}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
