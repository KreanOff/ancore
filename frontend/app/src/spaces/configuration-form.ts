import type { Field, FormSchema } from '../forms/FormDialog';
import type { ConfigurationData, ConfigurationEditor } from './ConfigurationPage';

export const configurationFieldName = (field: Field) =>
  field.field_name || field.name.split('-').pop()!;

export function configurationHasRow(schema: FormSchema) {
  return schema.fields.some((field) => configurationFieldName(field) === 'key' && !!field.value);
}

export function configurationEditorSchema(schema: FormSchema): FormSchema {
  return {
    ...schema,
    fields: schema.fields
      .filter((field) => configurationFieldName(field) !== 'DELETE')
      .map((field) => ({
        ...field,
        required: ['key', 'label', 'category', 'flow_stage', 'type'].includes(
          configurationFieldName(field),
        ),
      })),
  };
}

// The existing endpoint validates all three formsets and their common revision.
// Keep every saved value, including repeated transition values, and replace only
// the row edited in the dialog. Unchecked checkboxes are absent from FormData.
export function configurationSubmission(
  data: ConfigurationData,
  editor: ConfigurationEditor,
  draft: FormData,
) {
  const values = configurationDraftSubmission(data);
  values.set('configuration_section', editor.section);
  values.set('configuration_index', String(editor.index));
  if (editor.remove) values.set('configuration_remove', '1');
  const row = data.sets.find((group) => group.key === editor.section)?.forms[editor.index];
  if (!row) throw new Error('Pozycja konfiguracji jest niedostępna. Odśwież stronę.');
  if (editor.remove) {
    const deletion = row.fields.find((field) => configurationFieldName(field) === 'DELETE');
    if (!deletion) throw new Error('Nie można usunąć tej pozycji.');
    values.set(deletion.name, 'on');
  } else {
    for (const field of row.fields) {
      if (configurationFieldName(field) === 'DELETE') continue;
      values.delete(field.name);
      draft.getAll(field.name).forEach((value) => values.append(field.name, value));
    }
  }
  return values;
}

export function configurationDraftSubmission(data: ConfigurationData) {
  const values = new FormData();
  values.set('revision', data.revision);
  values.set('configuration_section', data.section || 'types');
  for (const group of data.sets) {
    for (const schema of [group.management, ...group.forms]) {
      for (const field of schema.fields) {
        if (field.type === 'checkbox') {
          if (field.checked) values.append(field.name, String(field.value || 'on'));
        } else if (Array.isArray(field.value)) {
          field.value.forEach((value) => values.append(field.name, value));
        } else values.append(field.name, field.value || '');
      }
    }
  }
  return values;
}

export function configurationDraftKey(data: ConfigurationData) {
  return JSON.stringify(
    data.sets.map((group) => [
      group.key,
      group.forms
        .filter(
          (schema) =>
            configurationHasRow(schema) &&
            !schema.fields.some(
              (field) => configurationFieldName(field) === 'DELETE' && field.checked,
            ),
        )
        .map((schema) =>
          schema.fields
            .filter((field) => configurationFieldName(field) !== 'DELETE')
            .map((field) => [
              configurationFieldName(field),
              field.type === 'checkbox'
                ? field.checked
                : field.multiple
                  ? Array.isArray(field.value)
                    ? field.value
                    : []
                  : Array.isArray(field.value)
                    ? field.value[0] || ''
                    : field.value || '',
            ]),
        ),
    ]),
  );
}

export function configurationStage(
  data: ConfigurationData,
  editor: ConfigurationEditor,
  draft: FormData,
): ConfigurationData {
  if (!data.sets.find((group) => group.key === editor.section)?.forms[editor.index])
    throw new Error('Pozycja konfiguracji jest niedostępna. Odśwież stronę.');
  const row = data.sets.find((group) => group.key === editor.section)!.forms[editor.index];
  const keyField = row.fields.find((field) => configurationFieldName(field) === 'key');
  const key = keyField ? String(draft.get(keyField.name) || '') : '';
  const knownType = data.sets
    .find((group) => group.key === 'types')
    ?.forms.find((schema) =>
      schema.fields.some(
        (field) => configurationFieldName(field) === 'key' && String(field.value || '') === key,
      ),
    );
  const defaultIcon =
    data.type_icon_defaults?.[key] ||
    knownType?.fields
      .find((field) => configurationFieldName(field) === 'icon')
      ?.choices?.find((choice) => choice.value === '')?.icon ||
    'shapes';
  return withStatusChoices({
    ...data,
    editor: null,
    errors: [],
    sets: data.sets.map((group) =>
      group.key !== editor.section
        ? group
        : {
            ...group,
            errors: [],
            forms: group.forms.map((schema, index) =>
              index !== editor.index
                ? schema
                : {
                    ...schema,
                    bound: false,
                    errors: [],
                    fields: schema.fields.map((field) => {
                      if (configurationFieldName(field) === 'DELETE')
                        return { ...field, checked: false, errors: [] };
                      const values = draft.getAll(field.name).map(String);
                      return {
                        ...field,
                        errors: [],
                        checked: field.type === 'checkbox' && draft.has(field.name),
                        choices:
                          configurationFieldName(field) === 'icon'
                            ? field.choices?.map((choice) =>
                                choice.value === '' ? { ...choice, icon: defaultIcon } : choice,
                              )
                            : field.choices,
                        value:
                          field.type === 'checkbox'
                            ? field.value
                            : field.multiple
                              ? values
                              : values[0] || '',
                      };
                    }),
                  },
            ),
          },
    ),
  });
}

export function configurationRemove(
  data: ConfigurationData,
  section: ConfigurationEditor['section'],
  indices: number[],
): ConfigurationData {
  const group = data.sets.find((group) => group.key === section);
  if (
    !group ||
    indices.some(
      (index) =>
        !group.forms[index]?.fields.some((field) => configurationFieldName(field) === 'DELETE'),
    )
  )
    throw new Error('Nie można usunąć tej pozycji.');
  const removed = new Set(indices);
  return withStatusChoices({
    ...data,
    errors: [],
    editor: null,
    sets: data.sets.map((group) =>
      group.key !== section
        ? group
        : {
            ...group,
            errors: [],
            forms: group.forms.map((schema, index) =>
              !removed.has(index)
                ? schema
                : {
                    ...schema,
                    errors: [],
                    fields: schema.fields.map((field) => ({
                      ...field,
                      errors: [],
                      checked: configurationFieldName(field) === 'DELETE' ? true : field.checked,
                    })),
                  },
            ),
          },
    ),
  });
}

export function configurationAdd(data: ConfigurationData, section: ConfigurationEditor['section']) {
  const group = data.sets.find((group) => group.key === section);
  if (!group) throw new Error('Sekcja konfiguracji jest niedostępna.');
  const active = group.forms.filter(
    (schema) =>
      configurationHasRow(schema) &&
      !schema.fields.some((field) => configurationFieldName(field) === 'DELETE' && field.checked),
  );
  const maximum = Number(
    group.management.fields.find((field) => configurationFieldName(field) === 'MAX_NUM_FORMS')
      ?.value || 30,
  );
  if (active.length >= maximum)
    throw new Error(`Możesz dodać maksymalnie ${maximum} pozycji w tej sekcji.`);
  const empty = group.forms.findIndex((schema) => !configurationHasRow(schema));
  if (empty >= 0) return { data, index: empty };
  const initialCount = Number(
    group.management.fields.find((field) => configurationFieldName(field) === 'INITIAL_FORMS')
      ?.value || 0,
  );
  const reusable = group.forms.findIndex(
    (schema, index) =>
      index >= initialCount &&
      schema.fields.some((field) => configurationFieldName(field) === 'DELETE' && field.checked),
  );
  const template = group.forms[group.forms.length - 1];
  if (!template) throw new Error('Brak formularza dodawania. Odśwież stronę.');
  const index = reusable >= 0 ? reusable : group.forms.length;
  const prefix = `${section}-${index}-`;
  const blank: FormSchema = {
    ...template,
    bound: false,
    errors: [],
    fields: template.fields.map((field) => ({
      ...field,
      name: prefix + configurationFieldName(field),
      id: 'id_' + prefix + configurationFieldName(field),
      value: field.multiple
        ? []
        : { category: 'new', flow_stage: 'queue', type: 'text' }[configurationFieldName(field)] ||
          '',
      checked: false,
      errors: [],
      attrs: { ...field.attrs, id: 'id_' + prefix + configurationFieldName(field) },
      choices: field.choices?.map((choice) =>
        choice.value === '' && configurationFieldName(field) === 'icon'
          ? { ...choice, icon: 'shapes' }
          : choice,
      ),
    })),
  };
  return {
    index,
    data: {
      ...data,
      sets: data.sets.map((current) =>
        current.key !== section
          ? current
          : {
              ...current,
              forms:
                reusable >= 0
                  ? current.forms.map((schema, position) => (position === index ? blank : schema))
                  : [...current.forms, blank],
              management: {
                ...current.management,
                fields: current.management.fields.map((field) =>
                  configurationFieldName(field) === 'TOTAL_FORMS'
                    ? { ...field, value: String(Math.max(index + 1, current.forms.length)) }
                    : field,
                ),
              },
            },
      ),
    },
  };
}

function withStatusChoices(data: ConfigurationData): ConfigurationData {
  const statuses = data.sets.find((group) => group.key === 'statuses');
  const choices = (statuses?.forms || []).flatMap((schema) => {
    const fields = Object.fromEntries(
      schema.fields.map((field) => [configurationFieldName(field), field]),
    );
    return fields.key?.value && !fields.DELETE?.checked
      ? [
          {
            value: String(fields.key.value),
            label: String(fields.label?.value || fields.key.value),
          },
        ]
      : [];
  });
  return {
    ...data,
    sets: data.sets.map((group) =>
      group.key !== 'statuses'
        ? group
        : {
            ...group,
            forms: group.forms.map((schema) => ({
              ...schema,
              fields: schema.fields.map((field) =>
                configurationFieldName(field) !== 'transitions'
                  ? field
                  : {
                      ...field,
                      choices,
                      value: (Array.isArray(field.value) ? field.value : []).filter((value) =>
                        choices.some((choice) => choice.value === value),
                      ),
                    },
              ),
            })),
          },
    ),
  };
}

export function configurationMove(
  data: ConfigurationData,
  section: ConfigurationEditor['section'],
  index: number,
  direction: -1 | 1,
): ConfigurationData {
  const group = data.sets.find((group) => group.key === section);
  if (!group) return data;
  const visible = group.forms.flatMap((schema, position) =>
    configurationHasRow(schema) &&
    !schema.fields.some((field) => configurationFieldName(field) === 'DELETE' && field.checked)
      ? [position]
      : [],
  );
  const destination = visible[visible.indexOf(index) + direction];
  if (destination === undefined) return data;
  const forms = [...group.forms];
  [forms[index], forms[destination]] = [forms[destination], forms[index]];
  return {
    ...data,
    sets: data.sets.map((current) =>
      current !== group
        ? current
        : {
            ...current,
            forms: forms.map((schema, position) => ({
              ...schema,
              fields: schema.fields.map((field) => {
                const name = `${section}-${position}-${configurationFieldName(field)}`;
                return {
                  ...field,
                  name,
                  id: `id_${name}`,
                  attrs: { ...field.attrs, id: `id_${name}` },
                };
              }),
            })),
          },
    ),
  };
}
