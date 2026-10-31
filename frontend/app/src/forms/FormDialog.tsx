import {
  lazy,
  Suspense,
  useCallback,
  type FormEvent,
  type ReactNode,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from 'react';
import { flushSync } from 'react-dom';
import { Avatar, type AvatarData } from '../shared/Avatar';
import { Icon } from '../shared/Icon';
import { FieldLabel } from '../shared/FieldLabel';
import EmojiPicker, { type EmojiPickerConfig } from '../shared/EmojiPicker';
import { Modal } from '../shared/Modal';
import { type PageProps, navigate, PageError, pageRequest } from '../shared/page';
import { errorMessage } from '../shared/api';
import AvatarControl, { type AvatarForm } from '../shared/AvatarControl';
import type { FilterTeam } from '../filters/types';

export interface Field {
  name: string;
  field_name?: string;
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
    description?: string;
    photo_url?: string;
    space_avatar?: AvatarData;
    status_category?: string;
    priority?: string;
    layout_preview?: string;
  }[];
  emoji_picker?: EmojiPickerConfig;
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
  inline_avatar?: boolean;
  automatic_avatar?: AvatarData;
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
const SpaceSettingsDialog = lazy(() => import('../spaces/SettingsDialog'));
const FilterSettingsDialog = lazy(() => import('../filters/SettingsDialog'));
const tagFieldOrder = [
  'name',
  'description',
  'category',
  'status',
  'color',
  'icon',
  'priority',
  'scope',
  'owner_label',
  'related_tags',
  'usage_notes',
  'automation_rules',
];

export interface FormSection {
  id: string;
  label: string;
  fields: string[];
}

export interface FormDialogData {
  filter_settings?: 'create' | 'edit';
  filter_team?: { url: string; data: FilterTeam } | null;
  space_settings?: { space_url: string; tab: 'main' | 'members' | 'avatar' };
  title: string;
  action: string;
  return_url: string;
  form: FormSchema;
  values?: Record<string, string>;
}

// Django prefixes belong to submitted names; layout uses the original field name.
const layoutFieldName = (field: Field) => field.field_name ?? field.name;

export function FieldControl({
  field,
  bare = false,
  inline = false,
  emojiVariant = 'field',
}: {
  field: Field;
  bare?: boolean;
  inline?: boolean;
  emojiVariant?: 'field' | 'avatar';
}) {
  const host = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const root = host.current!;
    if (field.type === 'emoji') return;
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
          const url = choice.photo_url || data?.photo_url;
          avatar.className = data
            ? `profile-avatar space-avatar ${url ? 'has-photo' : `space-avatar-art ${data.preset_class || ''}`}`
            : 'work-team-avatar';
          avatar.setAttribute('aria-hidden', 'true');
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
        element.value = Array.isArray(field.value)
          ? field.value[0] || ''
          : field.value || (field.type === 'checkbox' ? 'on' : '');
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
          : `documents-field tasks-form-field ${['name', 'title', 'description', 'notes', 'spaces'].includes(layoutFieldName(field)) ? 'resources-form-wide' : ''}`
      }
      hidden={field.hidden}
    >
      {!field.hidden && !bare ? (
        <FieldLabel
          htmlFor={field.type === 'checkboxes' ? undefined : field.id}
          label={field.label}
          required={field.label_required ?? field.required}
          helpText={field.help_text}
          helpId={`${field.id}_help`}
        />
      ) : null}
      {field.type === 'emoji' && field.emoji_picker ? (
        <div className="react-field-control">
          <EmojiPicker
            key={String(field.value)}
            id={field.id}
            name={field.name}
            label={field.label}
            value={String(field.value || '')}
            config={field.emoji_picker}
            variant={emojiVariant}
            disabled={field.disabled}
            invalid={!!field.errors.length}
            describedBy={[
              field.help_text ? `${field.id}_help` : '',
              field.errors.length ? `${field.id}_error` : '',
            ]
              .filter(Boolean)
              .join(' ')}
          />
        </div>
      ) : (
        <div ref={host} className="react-field-control" />
      )}
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
/** Keep reading and keyboard order aligned with the shared form layout. */
export function FormLayout({
  fields,
  renderField = (field) => <FieldControl key={field.name} field={field} />,
}: {
  fields: Field[];
  renderField?: (field: Field) => ReactNode;
}) {
  const primary = fields.find(
    (field) => !field.hidden && ['name', 'title'].includes(layoutFieldName(field)),
  );
  const visibility =
    primary && fields.find((field) => !field.hidden && layoutFieldName(field) === 'visibility');
  const description = fields.find(
    (field) => !field.hidden && ['description', 'goal', 'notes'].includes(layoutFieldName(field)),
  );
  if (fields.every((field) => field.hidden)) return <>{fields.map(renderField)}</>;
  return (
    <div className="app-form-layout">
      {primary ? (
        <div className="app-form-heading">
          {renderField(primary)}
          {visibility ? renderField(visibility) : null}
        </div>
      ) : null}
      {description ? <div className="app-form-description">{renderField(description)}</div> : null}
      {fields
        .filter((field) => field !== primary && field !== visibility && field !== description)
        .map(renderField)}
    </div>
  );
}

export function FormFields({
  schema,
  exclude = [],
  layout = false,
}: {
  schema: FormSchema;
  exclude?: string[];
  layout?: boolean;
}) {
  const fields = schema.fields.filter((field) => !exclude.includes(field.name));
  if (layout) return <FormLayout fields={fields} />;
  return (
    <>
      {fields.map((field) => (
        <FieldControl key={field.name} field={field} />
      ))}
    </>
  );
}

export function PulpitFields({
  schema,
  visibility,
  kind,
  dataScope,
}: {
  schema: FormSchema;
  visibility: string;
  kind?: string;
  dataScope?: string;
}) {
  const icon = schema.fields.find((field) => field.name === 'icon' && field.type === 'emoji');
  const fields = (
    <FormLayout
      fields={schema.fields.filter((field) => field !== icon)}
      renderField={(field) => (
        <div
          key={field.name}
          data-pulpit-field={field.name}
          hidden={
            field.hidden ||
            (field.name === 'shared_with' && visibility !== 'selected') ||
            (field.name === 'scope_spaces' && dataScope !== 'spaces') ||
            (field.name === 'scope_filter' && dataScope !== 'filter')
          }
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
      )}
    />
  );
  return icon ? (
    <>
      <div className="profile-photo-control" data-pulpit-field="icon">
        <FieldControl field={icon} bare emojiVariant="avatar" />
      </div>
      <div className="space-settings-fields">{fields}</div>
    </>
  ) : (
    fields
  );
}

export function EmbeddedForm({
  data,
  api,
  csrfToken,
  onSaved,
  onStateChange,
  openAvatar = false,
  sections,
  activeSection,
  onInvalidSection,
  revisionChange,
}: {
  openAvatar?: boolean;
  data: FormDialogData;
  api: string;
  csrfToken: string;
  onSaved: (url: string, result?: { filter_modal?: FormDialogData }) => void;
  onStateChange: (dirty: boolean, pending: boolean) => void;
  sections?: FormSection[];
  activeSection?: string;
  onInvalidSection?: (id: string) => void;
  revisionChange?: { previous: number; current: number };
}) {
  const [schema, setSchema] = useState(data.form),
    [pending, setPending] = useState(false),
    [dirty, setDirty] = useState(data.form.bound),
    [error, setError] = useState('');
  const pulpitAvatar =
    schema.layout === 'pulpit' &&
    schema.fields.some((field) => field.name === 'icon' && field.type === 'emoji');
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
  const [dataScope, setDataScope] = useState(() =>
    String(schema.fields.find((field) => field.name === 'data_scope')?.value || 'workspace'),
  );
  useLayoutEffect(() => {
    if (form.current) window.AncoreCustomSelect?.refresh(form.current);
  }, [visibility, dataScope, schema]);
  useLayoutEffect(() => {
    const input = form.current?.querySelector<HTMLInputElement>('input[name="revision"]');
    // Only advance the form we actually shared from; an older external edit must still conflict.
    if (input && revisionChange && input.value === String(revisionChange.previous))
      input.value = String(revisionChange.current);
  }, [revisionChange]);
  useEffect(() => {
    const element = form.current!,
      changed = (event: Event) => {
        setDirty(true);
        const target = event.target;
        if (target instanceof HTMLSelectElement && target.name === 'visibility')
          setVisibility(target.value);
        if (target instanceof HTMLSelectElement && target.name === 'kind') setKind(target.value);
        if (target instanceof HTMLSelectElement && target.name === 'data_scope')
          setDataScope(target.value);
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
  useEffect(() => onStateChange(dirty, pending), [dirty, pending, onStateChange]);
  useEffect(() => {
    if (openAvatar)
      form.current?.querySelector<HTMLButtonElement>('[data-workplace-avatar-open]')?.click();
  }, [openAvatar]);
  async function save(event: FormEvent) {
    event.preventDefault();
    if (sending.current) return;
    const values = new FormData(form.current!);
    sending.current = true;
    setPending(true);
    setError('');
    try {
      const result = await pageRequest<{
        redirect?: string;
        saved?: boolean;
        url?: string;
        form?: FormSchema;
        filter_modal?: FormDialogData;
      }>(api, data.action, csrfToken, controller.current.signal, values);
      flushSync(() => {
        if (result.form) setSchema(result.form);
        setDirty(false);
        setPending(false);
        onStateChange(false, false);
      });
      await onSaved(result.redirect || result.url || data.return_url, result);
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
          setDataScope(
            String(
              corrected.form.fields.find((field) => field.name === 'data_scope')?.value ||
                'workspace',
            ),
          );
          const invalid = corrected.form.fields.find((field) => field.errors.length);
          const section = sections?.find((item) => item.fields.includes(invalid?.name || ''));
          if (section) onInvalidSection?.(section.id);
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
    <form
      ref={form}
      id={
        schema.inline_avatar
          ? 'space-settings-form'
          : schema.layout === 'tag'
            ? 'tag-create-form'
            : undefined
      }
      className="tasks-modal__form"
      onSubmit={save}
      onInvalidCapture={(event) => {
        const section = sections?.find((item) =>
          item.fields.includes((event.target as HTMLInputElement).name),
        );
        if (section) flushSync(() => onInvalidSection?.(section.id));
      }}
      encType="multipart/form-data"
      aria-busy={pending}
    >
      {Object.entries(data.values || {}).map(([name, value]) => (
        <input type="hidden" key={name} name={name} value={value} />
      ))}
      <div
        className={`tasks-modal__body ${schema.inline_avatar || pulpitAvatar ? 'profile-edit-body space-settings-main app-form-avatar-layout' : schema.layout === 'tag' ? 'tasks-project-modal__body tasks-project-edit-modal__body tasks-issue-modal__body' : schema.layout === 'filter' ? 'documents-form task-filter-form' : schema.layout === 'pulpit' ? 'documents-form pulpit-form' : 'documents-form resources-form'}${pulpitAvatar ? ' pulpit-profile-form' : ''}`}
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
              {schema.planning_summary.total} zadań · {schema.planning_summary.finished} ukończonych
              · {schema.planning_summary.points} pkt
            </span>
            {schema.planning_summary.unestimated ? (
              <p>{schema.planning_summary.unestimated} zadań bez estymacji</p>
            ) : null}
          </div>
        ) : null}
        {schema.inline_avatar ? (
          <fieldset className="resources-react-fieldset" disabled={pending}>
            <AvatarControl schema={schema as AvatarForm} formId="space-settings-form" space />
            <div className="space-settings-fields documents-form resources-form">
              <FormFields
                layout
                schema={schema}
                exclude={['avatar', 'avatar_photo', 'avatar_photo_crop', 'avatar_photo_remove']}
              />
              {schema.fields
                .filter((field) => field.name.startsWith('avatar'))
                .flatMap((field) => field.errors)
                .map((message, index) => (
                  <p key={index} className="tasks-modal__errors resources-form-wide" role="alert">
                    {message}
                  </p>
                ))}
            </div>
          </fieldset>
        ) : schema.layout === 'tag' ? (
          <fieldset className="resources-react-fieldset" disabled={pending}>
            <FormLayout
              fields={[
                ...tagFieldOrder.flatMap((name) =>
                  schema.fields.filter((field) => field.name === name),
                ),
                ...schema.fields.filter((field) => !tagFieldOrder.includes(field.name)),
              ]}
            />
          </fieldset>
        ) : schema.layout === 'pulpit' ? (
          <fieldset className="resources-react-fieldset" disabled={pending}>
            <PulpitFields
              schema={schema}
              visibility={visibility}
              kind={kind}
              dataScope={dataScope}
            />
          </fieldset>
        ) : schema.layout === 'filter' ? (
          <fieldset className="resources-react-fieldset" disabled={pending}>
            {sections
              ? sections.map((section) => (
                  <section
                    key={section.id}
                    id={`${section.id}-panel`}
                    role="tabpanel"
                    aria-labelledby={`${section.id}-tab`}
                    hidden={activeSection !== section.id}
                    className="filter-settings-panel"
                  >
                    <FormLayout
                      fields={schema.fields.filter((field) => section.fields.includes(field.name))}
                      renderField={(field) => (
                        <div
                          key={field.name}
                          className="react-field-slot"
                          hidden={field.name === 'shared_with' && visibility !== 'selected'}
                        >
                          <FieldControl field={field} />
                        </div>
                      )}
                    />
                  </section>
                ))
              : null}
            <FormLayout
              fields={schema.fields.filter((field) => !sections || field.hidden)}
              renderField={(field) => (
                <div
                  key={field.name}
                  className="react-field-slot"
                  hidden={
                    field.hidden || (field.name === 'shared_with' && visibility !== 'selected')
                  }
                >
                  <FieldControl field={field} />
                </div>
              )}
            />
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
                <FormFields schema={schema} exclude={['template', 'kind']} layout />
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
            <FormFields schema={schema} layout />
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
  );
}

export function FormDialog(props: {
  data: FormDialogData;
  api: string;
  csrfToken: string;
  onClose: () => void;
  onSaved: (url: string) => void;
  hostId?: string;
}) {
  const [state, setState] = useState({ dirty: false, pending: false });
  const report = useCallback(
    (dirty: boolean, pending: boolean) => setState({ dirty, pending }),
    [],
  );
  if (props.data.space_settings)
    return (
      <Suspense fallback={<div role="status">Wczytywanie ustawień…</div>}>
        <SpaceSettingsDialog
          {...props}
          spaceUrl={props.data.space_settings.space_url}
          initialTab={props.data.space_settings.tab}
          initialForm={props.data}
        />
      </Suspense>
    );
  if (props.data.filter_settings)
    return (
      <Suspense fallback={<div role="status">Wczytywanie ustawień…</div>}>
        <FilterSettingsDialog {...props} />
      </Suspense>
    );
  const schema = props.data.form;
  return (
    <Modal
      title={props.data.title}
      hostId={props.hostId}
      className={`work-modal ${schema.compact ? 'app-modal-panel--compact' : ''} ${schema.layout === 'tag' ? 'tasks-project-modal tasks-project-edit-modal' : ''}`}
      dirty={state.dirty}
      pending={state.pending}
      onClose={props.onClose}
    >
      <EmbeddedForm {...props} onStateChange={report} />
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
        onClose={() =>
          navigate(
            data.space_settings ? data.return_url.replace('?view=settings', '') : data.return_url,
          )
        }
        onSaved={navigate}
      />
    </div>
  );
}
