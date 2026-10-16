import { type FormEvent, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { ApiError, errorMessage, request } from '../shared/api';
import type { Editor, Errors, Field } from './types';

function FieldControl({ field, errors }: { field: Field; errors?: Errors[string] }) {
  const ref = useRef<HTMLDivElement>(null);
  const control = useRef<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>();
  useLayoutEffect(() => {
    const host = ref.current;
    if (!host) return;
    const element = document.createElement(
      field.type === 'select' ? 'select' : field.type === 'textarea' ? 'textarea' : 'input',
    );
    element.name = field.name;
    element.id = `id_${field.name}`;
    element.required = field.required;
    element.className = field.type === 'select' ? 'form-select' : 'form-input';
    if (element instanceof HTMLSelectElement) {
      for (const choice of field.choices || []) {
        const option = new Option(choice.label, choice.value);
        if (choice.avatar) {
          const template = document.createElement('template');
          template.id = `${element.id}_preview_${choice.value}`;
          const avatar = document.createElement('span');
          avatar.className = `profile-avatar profile-avatar--user ${choice.avatar.color_class} ${choice.avatar.photo_url ? 'has-photo' : choice.avatar.preset_class ? `user-avatar-art ${choice.avatar.preset_class}` : ''}`;
          avatar.style.setProperty('--profile-avatar-bg', choice.avatar.background_color);
          avatar.style.setProperty('--profile-avatar-fg', choice.avatar.foreground_color);
          avatar.setAttribute('aria-hidden', 'true');
          if (choice.avatar.photo_url) {
            const image = document.createElement('img');
            image.src = choice.avatar.photo_url;
            image.alt = '';
            avatar.append(image);
          } else if (!choice.avatar.preset_class) {
            const icon = window.AncoreIcons?.create('user-round', {
              className: 'profile-avatar-icon',
            });
            if (icon) avatar.append(icon);
          }
          template.content.append(avatar);
          host.append(template);
          option.dataset.ancoreOptionPreview = template.id;
        }
        element.add(option);
      }
    } else {
      element.placeholder = field.placeholder;
      if (field.max_length) element.maxLength = field.max_length;
      if (element instanceof HTMLInputElement) element.type = field.type;
      else element.rows = 3;
    }
    element.value = field.value;
    host.append(element);
    control.current = element;
    window.AncoreCustomSelect?.refresh(host);
    window.AncoreIcons?.render(host);
    return () => {
      host.replaceChildren();
    };
  }, [field]);
  useLayoutEffect(() => {
    if (!control.current) return;
    control.current.setAttribute('aria-invalid', errors?.length ? 'true' : 'false');
    control.current.setAttribute(
      'aria-describedby',
      [
        field.help_text ? `id_${field.name}_helptext` : '',
        errors?.length ? `id_${field.name}_error` : '',
      ]
        .filter(Boolean)
        .join(' '),
    );
    window.AncoreCustomSelect?.refresh(ref.current!);
  }, [errors, field]);
  return (
    <div
      className={`documents-field tasks-form-field ${['name', 'notes'].includes(field.name) ? 'resources-form-wide' : ''}`}
    >
      <label htmlFor={`id_${field.name}`}>
        {field.label}
        {field.required ? <span aria-hidden="true"> *</span> : null}
      </label>
      <div ref={ref} className="react-field-control" />
      {field.help_text ? <small id={`id_${field.name}_helptext`}>{field.help_text}</small> : null}
      {errors?.length ? (
        <div className="tasks-modal__errors" id={`id_${field.name}_error`} role="alert">
          {errors.map((error, index) => (
            <p key={index}>{error.message}</p>
          ))}
        </div>
      ) : null}
    </div>
  );
}

const formValues = (form: HTMLFormElement) => JSON.stringify([...new FormData(form)]);
function focusFirst(form: HTMLFormElement, invalid = false) {
  const target = form.querySelector<HTMLElement>(
    invalid ? '[aria-invalid="true"]' : 'input:not([type="hidden"])',
  );
  (
    target?.closest('.ancore-custom-select')?.querySelector<HTMLElement>('button') || target
  )?.focus();
}

export function ResourceEditor({
  editor,
  apiUrl,
  csrfToken,
  onClose,
  onSaved,
}: {
  editor: Editor;
  apiUrl: string;
  csrfToken: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [fields, setFields] = useState(editor.fields);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [errors, setErrors] = useState<Errors>({});
  const modal = useRef<HTMLDivElement>(null);
  const form = useRef<HTMLFormElement>(null);
  const state = useRef({ pending: false, discard: false, initial: '' });
  const controller = useRef(new AbortController());
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    const element = modal.current!,
      formElement = form.current!;
    const previousFocus = document.activeElement;
    state.current.initial = formValues(formElement);
    const background: HTMLElement[] = [];
    const dirty = () => !state.current.discard && formValues(formElement) !== state.current.initial;
    const beforeClose = (event: Event) => {
      if (state.current.pending) {
        event.preventDefault();
        return;
      }
      if (!dirty()) return;
      event.preventDefault();
      window.showConfirmModal({
        title: 'Niezapisane zmiany',
        message: 'Zamknąć zasób bez zapisania zmian?',
        confirmText: 'Zamknij bez zapisu',
        cancelText: 'Wróć do edycji',
        onConfirm: () => {
          if (!element.isConnected) return;
          state.current.discard = true;
          window.AncoreTaskModals?.close(element);
        },
      });
    };
    const closed = () => closeRef.current();
    const beforeNavigate = (event: Event) => {
      if (state.current.pending || dirty()) {
        event.preventDefault();
        window.AncoreTaskModals?.close(element);
      }
    };
    const beforeUnload = (event: BeforeUnloadEvent) => {
      if (dirty() || state.current.pending) {
        event.preventDefault();
        event.returnValue = '';
      }
    };
    element.addEventListener('ancore:task-modal-before-close', beforeClose);
    element.addEventListener('ancore:task-modal-closed', closed);
    document.addEventListener('ancore:before-navigate', beforeNavigate);
    window.addEventListener('beforeunload', beforeUnload);
    window.AncoreTaskModals?.open(
      element,
      formElement.querySelector<HTMLElement>('input:not([type="hidden"])'),
    );
    // Preserve the shared modal's background/focus contract.
    for (
      let node: HTMLElement | null = element.parentElement;
      node && node !== document.body;
      node = node.parentElement
    ) {
      [...node.parentElement!.children].forEach((sibling) => {
        if (sibling !== node && sibling instanceof HTMLElement && !sibling.inert) {
          sibling.inert = true;
          background.push(sibling);
        }
      });
    }
    return () => {
      controller.current.abort();
      window.AncoreCustomSelect?.closeAll();
      element.removeEventListener('ancore:task-modal-before-close', beforeClose);
      element.removeEventListener('ancore:task-modal-closed', closed);
      document.removeEventListener('ancore:before-navigate', beforeNavigate);
      window.removeEventListener('beforeunload', beforeUnload);
      background.forEach((sibling) => {
        sibling.inert = false;
      });
      if (!document.querySelector('.tasks-modal.is-open'))
        document.body.classList.remove('modal-open');
      if (previousFocus instanceof HTMLElement && previousFocus.isConnected)
        previousFocus.focus({ preventScroll: true });
    };
  }, []);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (state.current.pending) return;
    const element = form.current!;
    const data = Object.fromEntries(new FormData(element));
    state.current.pending = true;
    setPending(true);
    setError('');
    setErrors({});
    try {
      await request(
        apiUrl + (editor.id ? `${editor.id}/` : ''),
        csrfToken,
        controller.current.signal,
        {
          method: editor.id ? 'PUT' : 'POST',
          body: JSON.stringify(data),
        },
      );
      state.current.pending = false;
      state.current.discard = true;
      onSaved();
    } catch (exception) {
      if (controller.current.signal.aborted) return;
      if (exception instanceof ApiError && exception.data.errors) {
        setErrors(exception.data.errors as Errors);
        if (exception.data.editor) setFields((exception.data.editor as Editor).fields);
        requestAnimationFrame(() => focusFirst(element, true));
      }
      setError(errorMessage(exception));
    } finally {
      state.current.pending = false;
      setPending(false);
    }
  }
  const host = document.querySelector('[data-resource-modal-host]');
  if (!host) return null;
  return createPortal(
    <div
      ref={modal}
      className="tasks-modal app-modal-panel tasks-form-modal resources-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="resource-modal-title"
      aria-hidden="true"
      data-resource-modal
    >
      <div className="tasks-modal__dialog">
        <form ref={form} className="tasks-modal__form" onSubmit={save} aria-busy={pending}>
          <header className="tasks-modal__header">
            <h2 id="resource-modal-title">{editor.id ? 'Edytuj zasób' : 'Dodaj zasób'}</h2>
            <button
              type="button"
              className="tasks-modal__close"
              aria-label="Zamknij"
              disabled={pending}
              onClick={() => window.AncoreTaskModals?.close(modal.current!)}
            />
          </header>
          <fieldset className="resources-react-fieldset" disabled={pending}>
            <div className="tasks-modal__body documents-form resources-form">
              {error ? (
                <div className="tasks-modal__errors resources-form-wide" role="alert">
                  {error}
                  {errors.__all__?.map((item, index) => (
                    <p key={index}>{item.message}</p>
                  ))}
                </div>
              ) : null}
              {fields.map((field) => (
                <FieldControl key={field.name} field={field} errors={errors[field.name]} />
              ))}
            </div>
            <footer className="tasks-modal__footer">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => window.AncoreTaskModals?.close(modal.current!)}
              >
                Anuluj
              </button>
              <button type="submit" className="tasks-modal__submit">
                {pending ? 'Zapisywanie…' : 'Zapisz'}
              </button>
            </footer>
          </fieldset>
        </form>
      </div>
    </div>,
    host,
  );
}
