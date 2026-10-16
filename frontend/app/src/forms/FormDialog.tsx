import { type FormEvent, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { Avatar, type AvatarData } from '../shared/Avatar';
import { Icon } from '../shared/Icon';
import { Modal } from '../shared/Modal';
import { type PageProps, navigate, PageError, pageRequest } from '../shared/page';
import { errorMessage } from '../shared/api';

export interface Field {
  name: string;
  id: string;
  label: string;
  type: string;
  value: string | string[] | null;
  required: boolean;
  label_required?: boolean;
  disabled: boolean;
  hidden: boolean;
  checked: boolean;
  multiple?: boolean;
  help_text: string;
  errors: string[];
  attrs: Record<string, string>;
  choices?: {
    value: string;
    label: string;
    avatar?: AvatarData;
    group?: string;
    icon?: string;
    photo_url?: string;
    space_avatar?: AvatarData;
    status_category?: string;
    priority?: string;
    layout_preview?: string;
  }[];
}
interface Template {
  key: string;
  kind: string;
  kind_label: string;
  label: string;
  description: string;
  image: string;
}
export interface FormSchema {
  layout?: 'filter' | 'tag' | 'pulpit';
  gadget_catalog?: {
    kind: string;
    name: string;
    icon: string;
    description: string;
    category: string;
    category_label: string;
  }[];
  illustration?: string;
  fields: Field[];
  errors: string[];
  bound: boolean;
  compact: boolean;
  submit_label: string;
  templates?: Template[];
  avatars?: { key: string; label: string; preset_class: string }[];
  current_avatar?: AvatarData;
  planning_summary?: { total: number; finished: number; points: number; unestimated: number };
  sprint_name?: string;
}
export interface FormDialogData {
  title: string;
  action: string;
  return_url: string;
  form: FormSchema;
  values?: Record<string, string>;
}

export function FieldControl({
  field,
  bare = false,
  inline = false,
}: {
  field: Field;
  bare?: boolean;
  inline?: boolean;
}) {
  const host = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const root = host.current!;
    if (!field.hidden && field.type === 'checkboxes') {
      const group = document.createElement('div');
      group.setAttribute('role', 'group');
      group.setAttribute('aria-label', field.label);
      const selected = new Set(Array.isArray(field.value) ? field.value : []);
      (field.choices || []).forEach((choice, index) => {
        const row = document.createElement('div'),
          label = document.createElement('label'),
          input = document.createElement('input');
        input.type = 'checkbox';
        input.name = field.name;
        input.value = choice.value;
        input.id = `${field.id}_${index}`;
        input.checked = selected.has(choice.value);
        input.disabled = field.disabled;
        input.className = 'tasks-row-checkbox';
        label.htmlFor = input.id;
        label.append(input, document.createTextNode(' ' + choice.label));
        row.append(label);
        group.append(row);
      });
      root.append(group);
      return () => root.replaceChildren();
    }
    const element = document.createElement(
      field.hidden
        ? 'input'
        : field.type === 'select'
          ? 'select'
          : field.type === 'textarea'
            ? 'textarea'
            : 'input',
    );
    element.id = field.id;
    element.name = field.name;
    element.disabled = field.disabled;
    element.required = field.required;
    if (element instanceof HTMLSelectElement) {
      element.className = 'form-select';
      element.multiple = !!field.multiple;
      const chosen = new Set(Array.isArray(field.value) ? field.value : [field.value || '']);
      for (const choice of field.choices || []) {
        const option = new Option(choice.label, choice.value, false, chosen.has(choice.value));
        if (choice.icon) option.dataset.ancoreOptionIcon = choice.icon;
        if (choice.layout_preview) {
          const template = document.createElement('template');
          template.id = `${field.id}_layout_${choice.value}`;
          const preview = document.createElement('span');
          preview.className = `pulpit-layout-preview pulpit-layout-preview--${choice.layout_preview}`;
          preview.setAttribute('aria-hidden', 'true');
          for (let index = 0; index < 3; index++) preview.append(document.createElement('span'));
          template.content.append(preview);
          root.append(template);
          option.dataset.ancoreOptionPreview = template.id;
        }
        if (choice.priority) {
          const template = document.createElement('template');
          template.id = `${field.id}_priority_${choice.value}`;
          const indicator = document.createElement('span');
          indicator.className = `tasks-row-priority priority-${choice.priority}`;
          const icon = window.AncoreIcons?.create(
            (
              {
                urgent: 'circle-alert',
                high: 'arrow-up',
                medium: 'equal',
                low: 'arrow-down',
              } as Record<string, string>
            )[choice.priority] || 'circle',
          );
          if (icon) indicator.append(icon);
          template.content.append(indicator);
          root.append(template);
          option.dataset.ancoreOptionPreview = template.id;
        }
        if (choice.status_category) {
          const template = document.createElement('template');
          template.id = `${field.id}_status_${choice.value}`;
          const indicator = document.createElement('span');
          indicator.className = `status-indicator status-${choice.status_category} tasks-filter-status-icon`;
          indicator.setAttribute('aria-hidden', 'true');
          template.content.append(indicator);
          root.append(template);
          option.dataset.ancoreOptionPreview = template.id;
        }
        if (choice.photo_url || choice.space_avatar) {
          const template = document.createElement('template');
          template.id = `${field.id}_visual_${choice.value}`;
          const avatar = document.createElement('span');
          const data = choice.space_avatar;
          avatar.className = data ? `space-avatar ${data.preset_class || ''}` : 'work-team-avatar';
          const url = choice.photo_url || data?.photo_url;
          if (url) {
            const image = document.createElement('img');
            image.src = url;
            image.alt = '';
            avatar.append(image);
          }
          template.content.append(avatar);
          root.append(template);
          option.dataset.ancoreOptionPreview = template.id;
        }
        if (choice.avatar) {
          const template = document.createElement('template');
          template.id = `${field.id}_avatar_${choice.value}`;
          const avatar = document.createElement('span');
          avatar.className = `profile-avatar profile-avatar--user ${choice.avatar.color_class || ''} ${choice.avatar.photo_url ? 'has-photo' : `user-avatar-art ${choice.avatar.preset_class || ''}`}`;
          avatar.style.setProperty('--profile-avatar-bg', choice.avatar.background_color || '');
          avatar.style.setProperty('--profile-avatar-fg', choice.avatar.foreground_color || '');
          avatar.setAttribute('aria-hidden', 'true');
          if (choice.avatar.photo_url) {
            const image = document.createElement('img');
            image.src = choice.avatar.photo_url;
            image.alt = '';
            avatar.append(image);
          } else if (!choice.avatar.preset_class) {
            const icon = window.AncoreIcons?.create('user-round');
            if (icon) avatar.append(icon);
          }
          template.content.append(avatar);
          root.append(template);
          option.dataset.ancoreOptionPreview = template.id;
        }
        element.add(option);
      }
    } else {
      element.className = field.type === 'checkbox' ? 'tasks-row-checkbox' : 'form-input';
      if (element instanceof HTMLInputElement) {
        element.type = field.hidden ? 'hidden' : field.type;
        element.checked = field.checked;
        if (field.type === 'file') element.multiple = !!field.multiple;
      }
      if (field.type !== 'file')
        element.value = Array.isArray(field.value) ? field.value[0] || '' : field.value || '';
    }
    Object.entries(field.attrs).forEach(([key, value]) => element.setAttribute(key, value));
    element.setAttribute('aria-invalid', String(!!field.errors.length));
    element.setAttribute('aria-label', field.label);
    element.setAttribute(
      'aria-describedby',
      [field.help_text ? `${field.id}_help` : '', field.errors.length ? `${field.id}_error` : '']
        .filter(Boolean)
        .join(' '),
    );
    root.append(element);
    window.AncoreCustomSelect?.refresh(root);
    window.AncoreIcons?.render(root);
    return () => root.replaceChildren();
  }, [field]);
  return (
    <div
      className={
        bare
          ? field.type === 'select' && !inline
            ? 'tasks-issue-select-wrap'
            : undefined
          : `documents-field tasks-form-field ${['name', 'title', 'description', 'notes', 'spaces'].includes(field.name) ? 'resources-form-wide' : ''}`
      }
      hidden={field.hidden}
    >
      {!field.hidden && !bare ? (
        <label htmlFor={field.type === 'checkboxes' ? undefined : field.id}>
          {field.label}
          {(field.label_required ?? field.required) ? <span aria-hidden="true"> *</span> : null}
        </label>
      ) : null}
      <div ref={host} className="react-field-control" />
      {field.help_text && !bare ? <small id={`${field.id}_help`}>{field.help_text}</small> : null}
      {field.errors.length ? (
        <div className="tasks-modal__errors" role="alert" id={`${field.id}_error`}>
          {field.errors.map((message, index) => (
            <p key={index}>{message}</p>
          ))}
        </div>
      ) : null}
    </div>
  );
}
export function FormFields({ schema, exclude = [] }: { schema: FormSchema; exclude?: string[] }) {
  return (
    <>
      {schema.fields
        .filter((field) => !exclude.includes(field.name))
        .map((field) => (
          <FieldControl key={field.name} field={field} />
        ))}
    </>
  );
}

export function PulpitFields({
  schema,
  visibility,
  kind,
}: {
  schema: FormSchema;
  visibility: string;
  kind?: string;
}) {
  return (
    <>
      {schema.fields.map((field) => (
        <div
          key={field.name}
          data-pulpit-field={field.name}
          hidden={field.name === 'shared_with' && visibility !== 'selected'}
        >
          <FieldControl field={field} />
          {field.name === 'kind' && schema.gadget_catalog ? (
            <div className="pulpit-gadget-preview">
              {kind ? (
                schema.gadget_catalog
                  .filter((entry) => entry.kind === kind)
                  .map((entry) => (
                    <div key={entry.kind}>
                      <span className="pulpit-catalog-preview" aria-hidden="true">
                        <Icon name={entry.icon} />
                        <span className="pulpit-catalog-preview-lines">
                          <span />
                          <span />
                          <span />
                        </span>
                      </span>
                      <div>
                        <span>{entry.name}</span>
                        <p>{entry.description}</p>
                      </div>
                    </div>
                  ))
              ) : (
                <div>
                  <img src={schema.illustration} alt="" width={1448} height={1086} />
                  <div>
                    <span>Wybierz gadżet</span>
                    <p>Śledź postęp pracy swojego zespołu.</p>
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>
      ))}
    </>
  );
}

export function FormDialog({
  data,
  api,
  csrfToken,
  onClose,
  onSaved,
  hostId,
}: {
  data: FormDialogData;
  api: string;
  csrfToken: string;
  onClose: () => void;
  onSaved: (url: string) => void;
  hostId?: string;
}) {
  const [schema, setSchema] = useState(data.form),
    [pending, setPending] = useState(false),
    [dirty, setDirty] = useState(false),
    [error, setError] = useState('');
  const form = useRef<HTMLFormElement>(null),
    controller = useRef(new AbortController()),
    sending = useRef(false);
  const [template, setTemplate] = useState(() =>
    schema.templates?.find(
      (option) => option.key === schema.fields.find((field) => field.name === 'template')?.value,
    ),
  );
  const [avatar, setAvatar] = useState(() =>
    String(schema.fields.find((field) => field.name === 'avatar')?.value || 'auto'),
  );
  const [preview, setPreview] = useState(data.form.current_avatar?.photo_url || '');
  const [visibility, setVisibility] = useState(() =>
    String(schema.fields.find((field) => field.name === 'visibility')?.value || ''),
  );
  const [kind, setKind] = useState(() =>
    String(schema.fields.find((field) => field.name === 'kind')?.value || ''),
  );
  useLayoutEffect(() => {
    if (form.current) window.AncoreCustomSelect?.refresh(form.current);
  }, [visibility, schema]);
  useEffect(() => {
    const element = form.current!,
      changed = (event: Event) => {
        setDirty(true);
        const target = event.target;
        if (target instanceof HTMLSelectElement && target.name === 'visibility')
          setVisibility(target.value);
        if (target instanceof HTMLSelectElement && target.name === 'kind') setKind(target.value);
      };
    element.addEventListener('input', changed);
    element.addEventListener('change', changed);
    return () => {
      controller.current.abort();
      element.removeEventListener('input', changed);
      element.removeEventListener('change', changed);
    };
  }, []);
  useEffect(
    () => () => {
      if (preview.startsWith('blob:')) URL.revokeObjectURL(preview);
    },
    [preview],
  );
  async function save(event: FormEvent) {
    event.preventDefault();
    if (sending.current) return;
    const values = new FormData(form.current!);
    sending.current = true;
    setPending(true);
    setError('');
    try {
      const result = await pageRequest<{ redirect?: string; saved?: boolean; url?: string }>(
        api,
        data.action,
        csrfToken,
        controller.current.signal,
        values,
      );
      flushSync(() => {
        setDirty(false);
        setPending(false);
      });
      await onSaved(result.redirect || result.url || data.return_url);
    } catch (exception) {
      if (controller.current.signal.aborted) return;
      if (exception instanceof PageError) {
        const details = exception.data.data as
          | (FormDialogData & { modal?: FormDialogData })
          | undefined;
        const corrected = details?.modal || details;
        if (corrected?.form) {
          setSchema(corrected.form);
          setVisibility(
            String(corrected.form.fields.find((field) => field.name === 'visibility')?.value || ''),
          );
          setKind(
            String(corrected.form.fields.find((field) => field.name === 'kind')?.value || ''),
          );
        }
      }
      setError(errorMessage(exception));
      requestAnimationFrame(() => {
        const input = form.current?.querySelector<HTMLElement>('[aria-invalid="true"]');
        (
          input?.closest('.ancore-custom-select')?.querySelector<HTMLElement>('button') || input
        )?.focus();
      });
    } finally {
      sending.current = false;
      setPending(false);
    }
  }
  function close() {
    const modal = form.current?.closest<HTMLElement>('.tasks-modal');
    if (modal) window.AncoreTaskModals?.close(modal);
  }
  return (
    <Modal
      title={data.title}
      hostId={hostId}
      className={`work-modal ${schema.compact ? 'app-modal-panel--compact' : ''} ${schema.layout === 'tag' ? 'tasks-project-modal tasks-project-edit-modal' : ''}`}
      dirty={dirty}
      pending={pending}
      onClose={onClose}
    >
      <form
        ref={form}
        id={schema.layout === 'tag' ? 'tag-create-form' : undefined}
        className="tasks-modal__form"
        onSubmit={save}
        encType="multipart/form-data"
        aria-busy={pending}
      >
        {Object.entries(data.values || {}).map(([name, value]) => (
          <input type="hidden" key={name} name={name} value={value} />
        ))}
        <div
          className={`tasks-modal__body ${schema.layout === 'tag' ? 'tasks-project-modal__body tasks-project-edit-modal__body tasks-issue-modal__body' : schema.layout === 'filter' ? 'documents-form task-filter-form' : schema.layout === 'pulpit' ? 'documents-form pulpit-form' : 'documents-form resources-form'}`}
        >
          {error ? (
            <div className="tasks-modal__errors resources-form-wide" role="alert">
              {error}
            </div>
          ) : null}
          {schema.errors.length ? (
            <div className="tasks-modal__errors resources-form-wide" role="alert">
              {schema.errors.map((message, index) => (
                <p key={index}>{message}</p>
              ))}
            </div>
          ) : null}
          {schema.planning_summary ? (
            <div className="work-sprint-preview resources-form-wide">
              <p>{schema.sprint_name}</p>
              <span>
                {schema.planning_summary.total} zadań · {schema.planning_summary.finished}{' '}
                ukończonych · {schema.planning_summary.points} pkt
              </span>
              {schema.planning_summary.unestimated ? (
                <p>{schema.planning_summary.unestimated} zadań bez estymacji</p>
              ) : null}
            </div>
          ) : null}
          {schema.layout === 'tag' ? (
            <fieldset className="resources-react-fieldset" disabled={pending}>
              {schema.fields
                .filter((field) => ['name', 'description'].includes(field.name))
                .map((field) => (
                  <FieldControl key={field.name} field={field} />
                ))}
              <section className="tasks-tag-parameters" aria-label="Parametry tagu">
                <div className="tasks-tag-fields">
                  {[
                    ['category', 'status', 'color', 'icon', 'priority', 'scope'],
                    ['owner_label', 'related_tags'],
                    ['usage_notes', 'automation_rules'],
                  ].map((names, index) => (
                    <div className="tasks-tag-field-group" key={index}>
                      <div className="tasks-tag-field-grid">
                        {names
                          .map((name) => schema.fields.find((field) => field.name === name))
                          .map((field) =>
                            field ? <FieldControl key={field.name} field={field} /> : null,
                          )}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            </fieldset>
          ) : schema.layout === 'pulpit' ? (
            <fieldset className="resources-react-fieldset" disabled={pending}>
              <PulpitFields schema={schema} visibility={visibility} kind={kind} />
            </fieldset>
          ) : schema.layout === 'filter' ? (
            <fieldset className="resources-react-fieldset task-filter-form" disabled={pending}>
              {schema.fields.map((field) => (
                <div
                  key={field.name}
                  className="react-field-slot"
                  hidden={field.name === 'shared_with' && visibility !== 'selected'}
                >
                  <FieldControl field={field} />
                </div>
              ))}
            </fieldset>
          ) : schema.templates ? (
            <>
              <input type="hidden" name="kind" value={template?.kind || ''} />
              <input type="hidden" name="template" value={template?.key || ''} />
              <section className="work-template-picker resources-form-wide" hidden={!!template}>
                <p className="work-caption">Krok 1 z 2 · Szablon przestrzeni</p>
                <h3>Wybierz sposób pracy swojego zespołu</h3>
                <p className="work-template-intro">
                  Zacznij od szablonu. W następnym kroku uzupełnisz nazwę i pozostałe dane
                  przestrzeni.
                </p>
                <div className="work-template-grid">
                  {schema.templates.map((option) => (
                    <button
                      key={option.key}
                      type="button"
                      className="work-space-card work-template-card"
                      aria-label={`Wybierz szablon: ${option.label}`}
                      onClick={() => {
                        setTemplate(option);
                        setDirty(true);
                        requestAnimationFrame(() =>
                          form.current?.querySelector<HTMLInputElement>('[name="name"]')?.focus(),
                        );
                      }}
                    >
                      <img
                        className="work-template-art"
                        src={option.image}
                        width={360}
                        height={200}
                        alt=""
                      />
                      <span className="work-template-copy">
                        <span className="work-caption">{option.kind_label}</span>
                        <span className="work-card-title">{option.label}</span>
                        <span className="work-template-description">{option.description}</span>
                        <span className="work-template-link">
                          Wybierz szablon
                          <Icon name="arrow-right" />
                        </span>
                      </span>
                    </button>
                  ))}
                </div>
              </section>
              <section className="work-space-details resources-form-wide" hidden={!template}>
                <p className="work-caption">Krok 2 z 2 · Dane przestrzeni</p>
                <h3>Skonfiguruj swoją przestrzeń</h3>
                <div className="work-template-summary">
                  {template ? <img src={template.image} width={108} height={60} alt="" /> : null}
                  <div>
                    <span className="work-caption">Wybrany szablon</span>
                    <span className="work-card-title">{template?.label}</span>
                    <span className="work-caption">{template?.kind_label}</span>
                  </div>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setTemplate(undefined)}
                  >
                    Zmień szablon
                  </button>
                </div>
                <fieldset
                  className="documents-form resources-form tasks-project-heading-fields work-space-fields"
                  disabled={!template || pending}
                >
                  <legend className="u-sr-only">Dane nowej przestrzeni</legend>
                  <FormFields schema={schema} exclude={['template', 'kind']} />
                </fieldset>
              </section>
            </>
          ) : schema.avatars ? (
            <div className="space-avatar-picker resources-form-wide">
              <fieldset className="space-avatar-presets" disabled={pending}>
                <legend>Wybierz gotowy awatar</legend>
                <div className="space-avatar-grid">
                  {schema.avatars.map((option) => (
                    <label key={option.key} className="space-avatar-option" title={option.label}>
                      <input
                        type="radio"
                        name="avatar"
                        value={option.key}
                        checked={avatar === option.key}
                        onChange={() => {
                          setAvatar(option.key);
                          setDirty(true);
                        }}
                        className="u-sr-only"
                      />
                      <span
                        className={`profile-avatar space-avatar space-avatar--picker space-avatar-art ${option.preset_class}`}
                        aria-hidden="true"
                      />
                      <span className="u-sr-only">{option.label}</span>
                    </label>
                  ))}
                </div>
                <label className="space-avatar-auto">
                  <input
                    type="radio"
                    name="avatar"
                    value="auto"
                    checked={avatar === 'auto'}
                    onChange={() => {
                      setAvatar('auto');
                      setDirty(true);
                    }}
                  />
                  Automatyczny awatar
                </label>
              </fieldset>
              <div
                className="space-avatar-upload"
                onDragOver={(event) => {
                  event.preventDefault();
                }}
                onDrop={(event) => {
                  event.preventDefault();
                  if (pending) return;
                  const file = event.dataTransfer.files[0];
                  const input = form.current?.querySelector<HTMLInputElement>(
                    'input[name="avatar_photo"]',
                  );
                  if (!file || !input) return;
                  const transfer = new DataTransfer();
                  transfer.items.add(file);
                  input.files = transfer.files;
                  setAvatar('upload');
                  setPreview(URL.createObjectURL(file));
                  setDirty(true);
                }}
              >
                <label className="space-avatar-auto">
                  <input
                    type="radio"
                    name="avatar"
                    value="upload"
                    checked={avatar === 'upload'}
                    onChange={() => {
                      setAvatar('upload');
                      setDirty(true);
                    }}
                  />
                  Własny obraz
                </label>
                <div className="space-avatar-upload__content">
                  {preview ? (
                    <Avatar space data={{ photo_url: preview }} className="space-avatar--picker" />
                  ) : null}
                  <label className="btn btn-secondary">
                    Wybierz obraz
                    <input
                      type="file"
                      className="u-sr-only"
                      name="avatar_photo"
                      accept="image/png,image/jpeg,image/webp"
                      disabled={pending}
                      onChange={(event) => {
                        const file = event.target.files?.[0];
                        if (file) {
                          setAvatar('upload');
                          setPreview(URL.createObjectURL(file));
                          setDirty(true);
                        }
                      }}
                    />
                  </label>
                  <small>PNG, JPG, WebP · do 5 MB</small>
                </div>
                {schema.fields
                  .flatMap((field) => field.errors)
                  .map((message, index) => (
                    <p className="tasks-modal__errors" role="alert" key={index}>
                      {message}
                    </p>
                  ))}
              </div>
            </div>
          ) : (
            <fieldset className="resources-react-fieldset" disabled={pending}>
              <FormFields schema={schema} />
            </fieldset>
          )}
        </div>
        <footer className="tasks-modal__footer">
          <button type="button" className="btn btn-secondary" disabled={pending} onClick={close}>
            Anuluj
          </button>
          {!schema.templates || template ? (
            <button type="submit" className="tasks-modal__submit" disabled={pending}>
              {pending
                ? 'Zapisywanie…'
                : schema.templates
                  ? 'Utwórz przestrzeń'
                  : schema.submit_label}
            </button>
          ) : null}
        </footer>
      </form>
    </Modal>
  );
}
export default function FormPage({ initial, csrfToken }: PageProps) {
  const data = initial.data as FormDialogData;
  return (
    <div className="tasks-page work-page">
      <FormDialog
        data={data}
        api={initial.api_url}
        csrfToken={csrfToken}
        onClose={() => navigate(data.return_url)}
        onSaved={navigate}
      />
    </div>
  );
}
