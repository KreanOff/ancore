import { useEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { Modal } from '../shared/Modal';
import { Icon } from '../shared/Icon';
import { FieldLabel } from '../shared/FieldLabel';
import { errorMessage } from '../shared/api';
import { PageError, pageRequest, type Page } from '../shared/page';
import AvatarControl from './AvatarControl';
import type { Field } from '../forms/FormDialog';
import type { DirectoryData, WorkspaceForm as Schema } from './types';

function ModuleFields({ field, id }: { field: Field; id: string }) {
  const selected = new Set(Array.isArray(field.value) ? field.value : []);
  return (
    <div className="tasks-form-field workplace-module-fields app-form-field app-form-wide">
      <FieldLabel
        label={<span id={id + '-modules-label'}>{field.label}</span>}
        helpText={field.help_text}
        helpId={id + '-modules-hint'}
        helpLabel={field.label}
      />
      <input type="hidden" name="modules_submitted" value="1" />
      <div
        className="workplace-module-grid"
        role="group"
        aria-labelledby={id + '-modules-label'}
        aria-describedby={field.help_text ? id + '-modules-hint' : undefined}
      >
        {(field.choices || []).map((choice) => {
          const controlId = id + '-module-' + choice.value;
          return (
            <label key={choice.value} className="workplace-module-card" htmlFor={controlId}>
              <Icon name={choice.icon || 'layers'} />
              <span className="workplace-module-card__body">
                <span className="workplace-module-card__name" id={controlId + '-label'}>
                  {choice.label}
                </span>
                <span
                  className="workplace-module-card__description"
                  id={controlId + '-description'}
                >
                  {choice.description}
                </span>
              </span>
              <span className="tasks-toggle workplace-module-card__toggle">
                <input
                  type="checkbox"
                  role="switch"
                  name={field.name}
                  id={controlId}
                  value={choice.value}
                  defaultChecked={selected.has(choice.value)}
                  disabled={field.disabled}
                  aria-labelledby={controlId + '-label'}
                  aria-describedby={controlId + '-description'}
                  aria-invalid={field.errors.length > 0}
                />
                <span aria-hidden="true" />
              </span>
            </label>
          );
        })}
      </div>
    </div>
  );
}
export function ErrorList({ schema, message = '' }: { schema?: Schema | null; message?: string }) {
  const errors = [
    ...(message ? [message] : []),
    ...(schema?.errors || []),
    ...(schema?.fields.flatMap((field) =>
      field.errors.map((error) => field.label + ': ' + error),
    ) || []),
  ];
  return errors.length ? (
    <div className="tasks-modal__errors" role="alert">
      {errors.map((text, index) => (
        <p key={index}>{text}</p>
      ))}
    </div>
  ) : null;
}
export function CrumbHeader({
  title,
  close,
  create = false,
}: {
  title: string;
  close: () => void;
  create?: boolean;
}) {
  return (
    <header
      className={
        'tasks-modal__header tasks-issue-modal__header ' +
        (create
          ? 'tasks-project-create-modal__header workplace-create-modal__header'
          : 'tasks-project-edit-modal__header workplace-edit-modal__header')
      }
    >
      <div className="tasks-issue-modal__crumbs">
        <button
          type="button"
          className="tasks-issue-close"
          aria-label="Zamknij"
          title="Zamknij"
          onClick={close}
        >
          <Icon name="arrow-left" />
        </button>
        <span className="tasks-issue-divider" />
        <strong>{title}</strong>
      </div>
    </header>
  );
}
export function SettingsFields({
  schema,
  id,
  name,
  description,
  setName,
  setDescription,
  code = '',
  readonly = false,
  create = false,
}: {
  schema: Schema | null;
  id: string;
  name: string;
  description: string;
  setName: (v: string) => void;
  setDescription: (v: string) => void;
  code?: string;
  readonly?: boolean;
  create?: boolean;
}) {
  const modules = schema?.fields.find((field) => field.name === 'enabled_modules');
  return (
    <div className="workplace-modal__content app-form-avatar-layout" data-profile-photo-layout>
      {schema && !readonly ? <AvatarControl schema={schema} formId={id} create={create} /> : null}
      <div className="workplace-modal__details app-form-layout">
        <div className="app-form-heading">
          <div className="tasks-form-field app-form-field">
            <label htmlFor={id + '-name'}>Nazwa miejsca pracy</label>
            <input
              id={id + '-name'}
              aria-invalid={!!schema?.fields.find((field) => field.name === 'name')?.errors.length}
              name="name"
              className="tasks-inline-input workplace-create-modal__name-input workplace-create-modal__text-input"
              placeholder="Nazwa miejsca pracy"
              autoComplete="off"
              maxLength={140}
              value={name}
              onChange={(e) => setName(e.target.value)}
              readOnly={readonly}
              required
            />
          </div>
        </div>
        {create ? (
          <span className="u-sr-only" aria-live="polite">
            {name.length}/140
          </span>
        ) : null}
        <div className="tasks-form-field app-form-field app-form-description">
          <label htmlFor={id + '-description'}>Opis</label>
          <textarea
            id={id + '-description'}
            name="description"
            className="tasks-inline-input tasks-modal-textarea workplace-create-modal__text-input workplace-create-modal__textarea"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Dodaj krótki opis miejsca pracy…"
            readOnly={readonly}
          />
        </div>
        <div className="tasks-form-field workplace-edit-modal__code-field app-form-field">
          <FieldLabel
            htmlFor={id + '-code'}
            label="Kod miejsca pracy"
            helpText="Stały, unikatowy identyfikator Workspace. Zmiana nazwy nie zmienia kodu ani adresu."
            helpId={id + '-code-hint'}
            helpLabel="Kod miejsca pracy"
          />
          <input
            id={id + '-code'}
            aria-label="Kod miejsca pracy"
            className="tasks-inline-input"
            value={code || 'Generowany automatycznie'}
            readOnly
            aria-describedby={id + '-code-hint'}
          />
        </div>
        {modules && !readonly ? <ModuleFields field={modules} id={id} /> : null}
      </div>
    </div>
  );
}
export function fieldValue(schema: Schema, name: string) {
  const v = schema.fields.find((field) => field.name === name)?.value;
  return Array.isArray(v) ? v[0] || '' : v || '';
}
export default function CreateDialog({
  schema: initial,
  api,
  token,
  action,
  onClose,
  onSaved,
}: {
  schema: Schema;
  api: string;
  token: string;
  action: string;
  onClose: () => void;
  onSaved: (url: string) => unknown;
}) {
  const [schema, setSchema] = useState(initial),
    [name, setName] = useState(fieldValue(initial, 'name')),
    [description, setDescription] = useState(fieldValue(initial, 'description')),
    [dirty, setDirty] = useState(initial.bound),
    [pending, setPending] = useState(false),
    [error, setError] = useState('');
  const [life] = useState(() => new AbortController());
  const sending = useRef(false);
  useEffect(() => () => life.abort(), [life]);
  return (
    <Modal
      title="Nowe miejsce pracy"
      className="tasks-project-modal tasks-project-create-modal tasks-issue-modal workplace-create-modal"
      dialogClassName="tasks-project-modal__dialog tasks-project-create-modal__dialog tasks-issue-modal__dialog workplace-create-modal__dialog"
      header={(close) => <CrumbHeader title="Nowe miejsce pracy" create close={close} />}
      dirty={dirty}
      pending={pending}
      onClose={() => {
        life.abort();
        onClose();
      }}
    >
      <form
        id="workspace-create-form"
        className="tasks-modal__form tasks-project-modal__form tasks-project-create-modal__form tasks-issue-modal__form workplace-create-modal__form"
        onInput={() => setDirty(true)}
        onChange={() => setDirty(true)}
        onSubmit={async (e) => {
          e.preventDefault();
          if (sending.current) return;
          sending.current = true;
          const body = new FormData(e.currentTarget);
          setPending(true);
          setError('');
          try {
            const result = await pageRequest<{ redirect: string }>(
              api,
              action,
              token,
              life.signal,
              body,
            );
            if (life.signal.aborted) return;
            flushSync(() => {
              setPending(false);
              setDirty(false);
            });
            await onSaved(result.redirect);
          } catch (error) {
            if (life.signal.aborted) return;
            if (error instanceof PageError) {
              const corrected = ((error.data as unknown as Page).data as DirectoryData)
                ?.create_form;
              if (corrected) setSchema(corrected);
            }
            setError(errorMessage(error));
          } finally {
            sending.current = false;
            setPending(false);
          }
        }}
      >
        <div className="tasks-modal__body tasks-project-modal__body tasks-project-create-modal__body tasks-issue-modal__body workplace-create-modal__body">
          <ErrorList schema={schema} message={error} />
          <fieldset className="resources-react-fieldset" disabled={pending}>
            <SettingsFields
              schema={schema}
              id="workspace-create-form"
              name={name}
              description={description}
              setName={setName}
              setDescription={setDescription}
              create
            />
          </fieldset>
        </div>
        <footer className="tasks-modal__footer tasks-project-create-modal__footer tasks-issue-modal__footer workplace-create-modal__footer">
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
          <button type="submit" className="tasks-modal__submit" disabled={pending || !name.trim()}>
            {pending ? 'Tworzenie…' : 'Utwórz miejsce pracy'}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
