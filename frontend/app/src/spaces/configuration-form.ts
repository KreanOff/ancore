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
        required: ['key', 'label', 'category', 'type'].includes(configurationFieldName(field)),
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
  const values = new FormData();
  values.set('revision', data.revision);
  values.set('configuration_section', editor.section);
  values.set('configuration_index', String(editor.index));
  if (editor.remove) values.set('configuration_remove', '1');
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
