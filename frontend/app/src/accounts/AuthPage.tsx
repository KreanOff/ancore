import { type FormEvent, useEffect, useRef, useState } from 'react';
import type { Field } from '../forms/FormDialog';
import { Icon } from '../shared/Icon';
import { errorMessage } from '../shared/api';
import { PageError, pageRequest, type Page, type PageProps } from '../shared/page';
import type { AuthData } from './types';

function Input({
  field,
  label,
  modern,
  focus,
  disabled,
}: {
  field: Field;
  label: string;
  modern: boolean;
  focus?: boolean;
  disabled: boolean;
}) {
  const [visible, setVisible] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const password = field.type === 'password';
  const id =
    field.name === 'username' ? 'email' : field.name === 'password' ? 'password' : field.id;
  return (
    <div
      className={`${modern ? 'auth-field' : 'form-group'}${field.errors.length ? ' auth-field--invalid' : ''}`}
    >
      <label className={modern ? 'auth-label' : 'form-label'} htmlFor={id}>
        {label}
      </label>
      <div className={password && modern ? 'auth-password-control' : undefined}>
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
            modern
              ? field.name === 'username' || field.name === 'password'
                ? 'auth-input'
                : 'form-input'
              : 'form-input'
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
            field.attrs.placeholder ||
            (field.name === 'username' ? 'email@firma.pl' : 'Wpisz hasło')
          }
          aria-invalid={field.errors.length ? true : undefined}
          aria-describedby={field.errors.length ? id + '-errors' : undefined}
        />
        {password && modern ? (
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
    add = data.mode === 'add';
  const [schema, setSchema] = useState(data.form),
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
      if (error instanceof PageError && error.data.type === 'account-auth')
        setSchema(((error.data as unknown as Page).data as AuthData).form);
      else setMessage(errorMessage(error));
      busy.current = false;
      setPending(false);
    }
  }
  const renderField = (name: string, label: string, focus = false) => {
    const field = schema.fields.find((item) => item.name === name)!;
    return (
      <Input
        key={name}
        field={field}
        label={label}
        modern={!add}
        focus={focus}
        disabled={pending}
      />
    );
  };
  const title = register ? 'Utwórz konto' : add ? 'Dodaj konto' : 'Zaloguj się';
  return (
    <main className="auth-shell" data-react-screen="account-auth">
      <header className="auth-topbar">
        <a href={data.urls.home} className="auth-brand" aria-label="Ancore — strona główna">
          <img src={data.logo} alt="" className="auth-brand-mark" />
          <span className="auth-brand-name">ANCORE</span>
        </a>
        <div className="auth-topbar-switch">
          <span className="auth-switch-prompt">
            {add ? '' : register ? 'Masz już konto?' : 'Nie masz konta?'}
          </span>
          <div className="auth-topbar-action">
            {!add ? (
              <a
                className="auth-switch-link"
                href={register ? data.urls.login : data.urls.register}
              >
                {register ? 'Zaloguj się' : 'Utwórz konto'}
              </a>
            ) : null}
          </div>
        </div>
      </header>
      <div className="auth-content">
        <section className="auth-story" aria-labelledby="auth-page-title">
          <div className="auth-story-copy">
            <h1 id="auth-page-title" className="auth-story-title">
              {register ? (
                <>
                  Zacznij
                  <br />
                  po swojemu.
                </>
              ) : add ? (
                'Dodaj konto'
              ) : (
                <>
                  Wszystko
                  <br />
                  na swoim
                  <br />
                  miejscu.
                </>
              )}
            </h1>
            <p className="auth-story-lead">
              {register ? (
                <>
                  Jedno konto. Jasny plan.
                  <br />
                  Więcej przestrzeni na właściwą pracę.
                </>
              ) : add ? (
                'Podłącz drugi profil do bieżącej sesji.'
              ) : (
                <>
                  Wracaj do projektów, ludzi i terminów
                  <br />
                  bez szukania.
                </>
              )}
            </p>
            <div className="auth-steps" aria-label="Etapy pracy">
              {(register
                ? ['Profil', 'Kontakty', 'Pierwszy plan']
                : add
                  ? ['Profil', 'Kontakty', 'Plan dnia']
                  : ['Priorytety', 'Rozmowy', 'Plan dnia']
              ).map((step, index) => (
                <span className="auth-step" key={step}>
                  <strong>0{index + 1}</strong>
                  <span>{step}</span>
                </span>
              ))}
            </div>
          </div>
          <svg
            className="auth-watermark"
            viewBox="0 0 1254 1254"
            aria-hidden="true"
            focusable="false"
          >
            <defs>
              <filter
                id="auth-logo-outline"
                x="-5%"
                y="-5%"
                width="110%"
                height="110%"
                colorInterpolationFilters="sRGB"
              >
                <feMorphology
                  in="SourceAlpha"
                  operator="dilate"
                  radius="4"
                  result="outline-outer"
                />
                <feMorphology in="SourceAlpha" operator="erode" radius="4" result="outline-inner" />
                <feComposite
                  in="outline-outer"
                  in2="outline-inner"
                  operator="out"
                  result="outline"
                />
                <feFlood floodColor="#5bbcbe" floodOpacity="0.52" result="outline-color" />
                <feComposite in="outline-color" in2="outline" operator="in" />
              </filter>
            </defs>
            <image href={data.logo} width="1254" height="1254" filter="url(#auth-logo-outline)" />
          </svg>
        </section>
        <section className="auth-form-panel" aria-labelledby="auth-form-title">
          <div className="auth-form-inner">
            <header className="auth-form-header">
              <h2 id="auth-form-title">{title}</h2>
              <p className="auth-form-subtitle">
                {register
                  ? 'Zajmie Ci to mniej niż minutę.'
                  : add
                    ? 'Dodaj konto do szybkiego przełączania'
                    : 'Wpisz dane swojego konta.'}
              </p>
            </header>
            <form
              method="post"
              className={'auth-form' + (register ? ' auth-form--register' : '')}
              onSubmit={submit}
              noValidate
              aria-busy={pending}
            >
              <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
              {message || invalid ? (
                <div
                  ref={alert}
                  className={add ? 'alert alert-error' : 'auth-alert'}
                  role="alert"
                  tabIndex={-1}
                >
                  {message ||
                    (register
                      ? 'Sprawdź oznaczone pola.'
                      : add
                        ? 'Nieprawidłowy email lub hasło.'
                        : 'Email lub hasło są nieprawidłowe. Spróbuj ponownie.')}
                  {register ? schema.errors.map((text, i) => <span key={i}>{text}</span>) : null}
                </div>
              ) : null}
              {register ? (
                <>
                  <div className="auth-field-row auth-field-row--names">
                    {renderField('first_name', 'Imię', true)}
                    {renderField('middle_name', 'Drugie imię')}
                    {renderField('last_name', 'Nazwisko')}
                  </div>
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
              <button
                type="submit"
                className={add ? 'btn btn-primary btn-block auth-submit' : 'auth-submit'}
                disabled={pending}
              >
                <span className="auth-submit-label">
                  {pending
                    ? 'Zapisywanie…'
                    : register
                      ? 'Zacznij w Ancore'
                      : add
                        ? 'Dodaj konto'
                        : 'Przejdź do Ancore'}
                </span>
                <span className="auth-submit-icon" aria-hidden="true">
                  <Icon name="arrow-right" />
                </span>
              </button>
            </form>
            {register ? (
              <a href={data.urls.home} className="auth-home-link">
                <Icon name="arrow-left" />
                <span>Wróć do strony głównej</span>
              </a>
            ) : add ? (
              <p className="auth-footer">
                <a href={data.urls.profile}>Wróć do profilu</a>
              </p>
            ) : null}
            <p className="icon-credit">
              Ikony UIcons:{' '}
              <a href="https://www.flaticon.com/uicons" target="_blank" rel="noopener noreferrer">
                Flaticon
              </a>
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
