import { type FormEvent, useEffect, useRef, useState } from 'react';
import type { Field } from '../forms/FormDialog';
import { Icon } from '../shared/Icon';
import { errorMessage } from '../shared/api';
import { PageError, pageRequest, type Page, type PageProps } from '../shared/page';
import type { AuthData } from './types';

function Input({
  field,
  label,
  focus,
  disabled,
}: {
  field: Field;
  label: string;
  focus?: boolean;
  disabled: boolean;
}) {
  const [visible, setVisible] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const password = field.type === 'password';
  const id =
    field.name === 'username' ? 'email' : field.name === 'password' ? 'password' : field.id;
  return (
    <div className={`auth-field${field.errors.length ? ' auth-field--invalid' : ''}`}>
      <label className="auth-label" htmlFor={id}>
        {label}
      </label>
      <div className={password ? 'auth-password-control' : undefined}>
        <input
          ref={input}
          id={id}
          name={field.name}
          type={
            password
              ? visible
                ? 'text'
                : 'password'
              : field.name === 'username'
                ? 'email'
                : field.type
          }
          className={
            field.name === 'username' || field.name === 'password' ? 'auth-input' : 'form-input'
          }
          defaultValue={String(field.value || '')}
          autoFocus={focus}
          required={field.required}
          disabled={disabled}
          maxLength={field.attrs.maxlength ? Number(field.attrs.maxlength) : undefined}
          autoComplete={
            field.attrs.autocomplete ||
            (field.name === 'username' ? 'username' : password ? 'current-password' : undefined)
          }
          placeholder={
            field.name === 'username' || field.name === 'email' ? 'email@firma.pl' : undefined
          }
          aria-invalid={field.errors.length ? true : undefined}
          aria-describedby={
            [field.attrs['aria-describedby'], field.errors.length ? id + '-errors' : '']
              .filter(Boolean)
              .join(' ') || undefined
          }
        />
        {password ? (
          <button
            type="button"
            className="auth-password-toggle"
            aria-controls={id}
            disabled={disabled}
            aria-label={visible ? 'Ukryj hasło' : 'Pokaż hasło'}
            aria-pressed={visible}
            onClick={() => {
              setVisible(!visible);
              input.current?.focus({ preventScroll: true });
            }}
          >
            <Icon name="eye" className="auth-eye auth-eye--show" />
            <Icon name="eye-off" className="auth-eye auth-eye--hide" />
          </button>
        ) : null}
      </div>
      {field.errors.length ? (
        <div id={id + '-errors'}>
          {field.errors.map((text, i) => (
            <span key={i} className="auth-field-error">
              {text}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export default function AuthPage({ initial, csrfToken }: PageProps) {
  const data = initial.data as AuthData,
    register = data.mode === 'register',
    workspace = data.mode === 'workspace';
  const [schema, setSchema] = useState(data.form),
    [hasWorkspaces, setHasWorkspaces] = useState(Boolean(data.has_workspaces)),
    [message, setMessage] = useState(''),
    [pending, setPending] = useState(false);
  const busy = useRef(false),
    controller = useRef<AbortController>();
  const alert = useRef<HTMLDivElement>(null);
  const invalid = schema.errors.length > 0 || schema.fields.some((field) => field.errors.length);
  useEffect(() => () => controller.current?.abort(), []);
  useEffect(() => {
    if (message || invalid) alert.current?.focus();
  }, [message, schema, invalid]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current) return;
    const body = new FormData(event.currentTarget);
    busy.current = true;
    setPending(true);
    setMessage('');
    const abort = new AbortController();
    controller.current = abort;
    try {
      const result = await pageRequest<{ redirect: string }>(
        initial.api_url,
        initial.url,
        csrfToken,
        abort.signal,
        body,
      );
      // Changing identity rotates the session/CSRF and must refresh the entire shell.
      location.assign(result.redirect);
    } catch (error) {
      if (abort.signal.aborted) return;
      if (error instanceof PageError && error.data.type === 'account-auth') {
        const responseData = (error.data as unknown as Page).data as AuthData;
        setSchema(responseData.form);
        setHasWorkspaces(Boolean(responseData.has_workspaces));
      } else setMessage(errorMessage(error));
      busy.current = false;
      setPending(false);
    }
  }
  const renderField = (name: string, label: string, focus = false) => {
    const field = schema.fields.find((item) => item.name === name)!;
    return <Input key={name} field={field} label={label} focus={focus} disabled={pending} />;
  };
  const title = workspace ? 'Utwórz Workspace' : register ? 'Utwórz konto' : 'Zaloguj się';
  return (
    <main className="auth-shell" data-react-screen="account-auth">
      <header className="auth-topbar">
        <a href={data.urls.home} className="auth-brand" aria-label="Ancore — strona główna">
          <span className="auth-brand-mark" aria-hidden="true" />
          <span className="auth-brand-name">ANCORE</span>
        </a>
      </header>
      <div className="auth-content">
        <section className="auth-form-panel" aria-labelledby="auth-form-title">
          <div className="auth-form-inner">
            {workspace ? (
              <header className="auth-form-header">
                <h1 id="auth-form-title" tabIndex={-1}>
                  {title}
                </h1>
              </header>
            ) : (
              <>
                <header className="auth-form-header">
                  <h1 id="auth-form-title" tabIndex={-1}>
                    {register ? title : 'Witaj ponownie'}
                  </h1>
                </header>
                <nav className="auth-tabs" aria-label="Dostęp do konta">
                  <a
                    href={data.urls.register}
                    className="auth-tab"
                    aria-current={register ? 'page' : undefined}
                  >
                    Rejestracja
                  </a>
                  <a
                    href={data.urls.login}
                    className="auth-tab"
                    aria-current={!register ? 'page' : undefined}
                  >
                    Logowanie
                  </a>
                </nav>
              </>
            )}
            <form
              method="post"
              className={'auth-form' + (register ? ' auth-form--register' : '')}
              onSubmit={submit}
              noValidate
              aria-busy={pending}
            >
              <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
              {workspace && hasWorkspaces ? (
                <input type="hidden" name="create_another" value="1" />
              ) : null}
              {message || invalid ? (
                <div ref={alert} className="auth-alert" role="alert" tabIndex={-1}>
                  {message ||
                    (register || workspace
                      ? 'Sprawdź oznaczone pola.'
                      : 'Email lub hasło są nieprawidłowe. Spróbuj ponownie.')}
                  {register || workspace
                    ? schema.errors.map((text, i) => <span key={i}>{text}</span>)
                    : null}
                </div>
              ) : null}
              {workspace ? (
                renderField('name', 'Nazwa Workspace', true)
              ) : register ? (
                <>
                  <div className="auth-field-row auth-field-row--names">
                    {renderField('first_name', 'Imię', true)}
                    {renderField('last_name', 'Nazwisko')}
                  </div>
                  {renderField('middle_name', 'Drugie imię (opcjonalnie)')}
                  {renderField('email', 'Adres email')}
                  <div className="auth-field-row auth-field-row--passwords">
                    {renderField('password1', 'Hasło')}
                    {renderField('password2', 'Potwierdź hasło')}
                  </div>
                </>
              ) : (
                <>
                  {renderField('username', 'Adres email', true)}
                  {renderField('password', 'Hasło')}
                </>
              )}
              <button type="submit" className="auth-submit" disabled={pending}>
                <span className="auth-submit-label">
                  {pending
                    ? workspace
                      ? 'Przygotowywanie Workspace…'
                      : 'Zapisywanie…'
                    : workspace
                      ? 'Utwórz Workspace'
                      : title}
                </span>
              </button>
            </form>
            {workspace ? (
              <p className="auth-footer auth-footer--workspace">
                Masz już Workspace? <a href={data.urls.select_workspace}>Wybierz Workspace</a>
              </p>
            ) : null}
          </div>
        </section>
      </div>
    </main>
  );
}
